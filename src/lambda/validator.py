"""
validator.py - Lambda function triggered by S3 ObjectCreated events.

Responsibilities:
  1. Verify the uploaded .zip file has a valid organization-id tag.
  2. Verify the file meets metadata requirements.
  3. Write audit records to DynamoDB at every state transition.
  4. Trigger an ECS Fargate task to process validated files.

Environment variables (injected by Terraform via lambda.tf):
  AUDIT_TABLE     - DynamoDB table name
  ECS_CLUSTER     - ECS cluster ARN
  TASK_DEFINITION - ECS task definition ARN
  SUBNETS         - comma-separated private subnet IDs
  SECURITY_GROUP  - ECS task security group ID
  AWS_ACCOUNT_ID  - AWS account ID
  VALID_ORGS      - comma-separated list of permitted organization IDs
"""
import os
import time
import uuid

import boto3

# ---------------------------------------------------------------------------
# Storage / compute adapters
# AWS SDK calls isolated here swap these functions to point at an
# on-premises backend without touching validation logic.
# ---------------------------------------------------------------------------

def _get_object_tags(bucket: str, key: str) -> dict:
    """Return {tag_key: tag_value} for the given S3 object."""
    s3 = boto3.client('s3')
    resp = s3.get_object_tagging(Bucket=bucket, Key=key)
    return {t['Key']: t['Value'] for t in resp.get('TagSet', [])}


def _get_object_head(bucket: str, key: str) -> dict:
    """Return the HeadObject response dict for the given S3 object."""
    s3 = boto3.client('s3')
    return s3.head_object(Bucket=bucket, Key=key)


def _launch_ecs_task(cluster: str, task_def: str, subnets: list,
                     security_group: str, overrides: list) -> str:
    """Launch a Fargate task and return its ARN."""
    ecs = boto3.client('ecs')
    resp = ecs.run_task(
        cluster=cluster,
        taskDefinition=task_def,
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets':        subnets,
                'securityGroups': [security_group],
                'assignPublicIp': 'DISABLED',
            }
        },
        overrides={'containerOverrides': [{'name': 'processor', 'environment': overrides}]},
    )
    failures = resp.get('failures', [])
    if failures:
        raise RuntimeError(f"ECS launch failures: {failures}")
    return resp['tasks'][0]['taskArn']


def _write_audit(table, trace_id: str, org_id: str, bucket: str,
                 key: str, status: str, reason: str = None):
    """Write a single audit record to DynamoDB."""
    item = {
        'trace_id':   trace_id,
        'timestamp':  int(time.time() * 1000),
        'org_id':     org_id or 'UNKNOWN',
        'bucket':     bucket,
        'key':        key,
        'status':     status,
        'expires_at': int(time.time()) + (90 * 24 * 60 * 60),
    }
    if reason:
        item['reason'] = reason
    table.put_item(Item=item)


# ---------------------------------------------------------------------------
# Config resolved once at Lambda cold-start from environment variables.
# All values are injected by Terraform (lambda.tf); no runtime lookups needed.
# ---------------------------------------------------------------------------

AUDIT_TABLE    = os.environ['AUDIT_TABLE']
ECS_CLUSTER    = os.environ['ECS_CLUSTER']
TASK_DEF       = os.environ['TASK_DEFINITION']
SUBNETS        = os.environ['SUBNETS'].split(',')
SECURITY_GROUP = os.environ['SECURITY_GROUP']

# VALID_ORGS is now a plain environment variable set in lambda.tf (var.valid_orgs).
# Previously this was fetched at runtime from SSM SecureString that dependency
# has been removed. Update terraform.tfvars and redeploy to change the list.
VALID_ORGS = set(os.environ['VALID_ORGS'].split(','))

_dynamodb = boto3.resource('dynamodb')
_table    = _dynamodb.Table(AUDIT_TABLE)


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------

def _process_record(record: dict) -> dict:
    """Validate one S3 event record and trigger ECS if it passes."""
    bucket   = record['s3']['bucket']['name']
    key      = record['s3']['object']['key']
    trace_id = str(uuid.uuid4())
    org_id   = None

    print(f"[{trace_id}] Validating s3://{bucket}/{key}")

    # --- Check 1: file must be a .zip ---
    if not key.endswith('.zip'):
        reason = f"invalid_file_type:key={key}"
        print(f"[{trace_id}] REJECTED — {reason}")
        _write_audit(_table, trace_id, org_id, bucket, key, 'REJECTED', reason)
        return {"trace_id": trace_id, "status": "failed", "reason": reason}

    # --- Check 2: organisation-id tag ---
    try:
        tags = _get_object_tags(bucket, key)
    except Exception as e:
        reason = f"tagging_error:{e}"
        _write_audit(_table, trace_id, org_id, bucket, key, 'ERROR', reason)
        raise

    org_id = tags.get('organization-id')
    if not org_id or org_id not in VALID_ORGS:
        reason = f"invalid_org_id:{org_id}"
        print(f"[{trace_id}] REJECTED — {reason}")
        _write_audit(_table, trace_id, org_id, bucket, key, 'REJECTED', reason)
        return {"trace_id": trace_id, "status": "failed", "reason": reason}

    # --- Check 3: metadata / content-type ---
    try:
        head = _get_object_head(bucket, key)
    except Exception as e:
        reason = f"head_object_error:{e}"
        print(f"[{trace_id}] ERROR — {reason}")
        _write_audit(_table, trace_id, org_id, bucket, key, 'ERROR', reason)
        raise

    metadata     = head.get('Metadata', {})
    content_type = head.get('ContentType', '')
    valid_zip_types = ('application/zip', 'application/octet-stream', 'application/x-zip-compressed')
    if metadata.get('data-type') != 'research-log' or not any(ct in content_type for ct in valid_zip_types):
        reason = f"metadata_mismatch:data-type={metadata.get('data-type')},content-type={content_type}"
        print(f"[{trace_id}] REJECTED — {reason}")
        _write_audit(_table, trace_id, org_id, bucket, key, 'REJECTED', reason)
        return {"trace_id": trace_id, "status": "failed", "reason": reason}

    # --- All checks passed: write PENDING then launch ECS ---
    _write_audit(_table, trace_id, org_id, bucket, key, 'PENDING')
    print(f"[{trace_id}] Validation passed. Launching ECS task...")

    try:
        task_arn = _launch_ecs_task(
            cluster=ECS_CLUSTER,
            task_def=TASK_DEF,
            subnets=SUBNETS,
            security_group=SECURITY_GROUP,
            overrides=[
                {'name': 'S3_BUCKET', 'value': bucket},
                {'name': 'S3_KEY',    'value': key},
                {'name': 'TRACE_ID',  'value': trace_id},
                {'name': 'ORG_ID',    'value': org_id},
            ],
        )
    except RuntimeError as e:
        reason = str(e)
        print(f"[{trace_id}] ECS launch failed — {reason}")
        _write_audit(_table, trace_id, org_id, bucket, key, 'ECS_FAILED', reason)
        raise

    print(f"[{trace_id}] ECS task launched: {task_arn}")

    _table.update_item(
        Key={'trace_id': trace_id, 'timestamp': int(time.time() * 1000)},
        UpdateExpression='SET #s = :s, task_arn = :t',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':s': 'TRIGGERED', ':t': task_arn},
    )

    return {"trace_id": trace_id, "status": "success", "organization": org_id, "task_arn": task_arn}


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handler(event, context):
    records = event.get('Records', [])
    if not records:
        print("No records in event — nothing to do.")
        return {"status": "noop"}

    results = [_process_record(r) for r in records]
    return {"processed": len(results), "results": results}
