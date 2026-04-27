"""
processor.py - runs inside the ECS Fargate container.

Reads a .zip data package from S3, processes it, and writes audit records
to DynamoDB at each stage of the workflow.

Environment variables:
  AUDIT_TABLE  - DynamoDB table name        (from ecs.tf task definition)
  S3_BUCKET    - source bucket              (from Lambda container override)
  S3_KEY       - object key of the .zip     (from Lambda container override)
  TRACE_ID     - correlation ID             (from Lambda container override)
  ORG_ID       - validated organisation ID  (from Lambda container override)
"""
import io
import os
import time
import zipfile

import boto3

# ---------------------------------------------------------------------------
# Storage adapter
#  hybrid backbone: all storage I/O is isolated in these two functions.
# To run on-premises S3-compatible store, only
# _download_object() needs to change the processing logic is untouched.
# ---------------------------------------------------------------------------

def _download_object(bucket: str, key: str) -> bytes:
    """Download and return the raw bytes of an S3 object."""
    s3 = boto3.client('s3')
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp['Body'].read()


def _write_audit(table, trace_id: str, org_id: str, bucket: str,
                 key: str, status: str, detail: str = None):
    """Append an audit record to DynamoDB."""
    item = {
        'trace_id':   trace_id,
        'timestamp':  int(time.time() * 1000),
        'org_id':     org_id,
        'bucket':     bucket,
        'key':        key,
        'status':     status,
        'expires_at': int(time.time()) + (90 * 24 * 60 * 60),
    }
    if detail:
        item['detail'] = detail
    table.put_item(Item=item)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

AUDIT_TABLE = os.environ['AUDIT_TABLE']
S3_BUCKET   = os.environ['S3_BUCKET']
S3_KEY      = os.environ['S3_KEY']
TRACE_ID    = os.environ.get('TRACE_ID', 'NO-TRACE')
ORG_ID      = os.environ.get('ORG_ID',   'UNKNOWN')

_dynamodb = boto3.resource('dynamodb')
_table    = _dynamodb.Table(AUDIT_TABLE)


# ---------------------------------------------------------------------------
# Processing logic
# ---------------------------------------------------------------------------

def _inspect_zip(raw: bytes) -> dict:
    """
    Open the .zip archive and return a summary of its contents.

    The original code used time.sleep(10) as a processing stub.
    This now actually reads the zip, listing each member file with its
    name and uncompressed size — satisfying the requirement that the
    processing step 'logs the file name and size'.

    Replace or extend this function with domain-specific logic:
    e.g. extract CSVs, validate schemas, push to downstream storage.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        members = [
            {"name": info.filename, "size_bytes": info.file_size}
            for info in zf.infolist()
        ]
    return {"member_count": len(members), "members": members}


def main():
    print(f"[{TRACE_ID}] --- Starting Data Processing ---")
    print(f"[{TRACE_ID}] File  : s3://{S3_BUCKET}/{S3_KEY}")
    print(f"[{TRACE_ID}] Org   : {ORG_ID}")

    _write_audit(_table, TRACE_ID, ORG_ID, S3_BUCKET, S3_KEY, 'PROCESSING_STARTED')

    try:
        print(f"[{TRACE_ID}] Downloading {S3_KEY} ...")
        raw       = _download_object(S3_BUCKET, S3_KEY)
        file_size = len(raw)
        print(f"[{TRACE_ID}] Downloaded {file_size:,} bytes.")

        print(f"[{TRACE_ID}] Inspecting zip archive ...")
        summary = _inspect_zip(raw)

        for m in summary['members']:
            print(f"[{TRACE_ID}]   {m['name']}  ({m['size_bytes']:,} bytes)")

        detail = (
            f"zip_bytes:{file_size},"
            f"members:{summary['member_count']}"
        )
        _write_audit(_table, TRACE_ID, ORG_ID, S3_BUCKET, S3_KEY,
                     'PROCESSING_COMPLETE', detail=detail)
        print(f"[{TRACE_ID}] --- Processing Complete ---")

    except Exception as e:
        _write_audit(_table, TRACE_ID, ORG_ID, S3_BUCKET, S3_KEY,
                     'FAILED', detail=str(e))
        print(f"[{TRACE_ID}] ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
