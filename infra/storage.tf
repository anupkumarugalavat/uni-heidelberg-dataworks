# S3 ingress bucket — receives .zip data packages from member orgs
resource "aws_s3_bucket" "ingress" {
  bucket = "${var.prefix}-ingress-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "ingress" {
  bucket                  = aws_s3_bucket.ingress.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# AWS-managed AES-256 encryption (SSE-S3).
resource "aws_s3_bucket_server_side_encryption_configuration" "encrypt" {
  bucket = aws_s3_bucket.ingress.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 event notification — triggers Lambda only on .zip uploads
resource "aws_s3_bucket_notification" "trigger" {
  bucket = aws_s3_bucket.ingress.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.validator.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".zip"
  }
  depends_on = [aws_lambda_permission.allow_s3]
}
