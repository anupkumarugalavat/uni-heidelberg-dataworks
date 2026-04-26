# DynamoDB audit log table
resource "aws_dynamodb_table" "audit" {
  name         = "${var.prefix}-audit-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "trace_id"
  range_key    = "timestamp"

  attribute {
    name = "trace_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }
}
