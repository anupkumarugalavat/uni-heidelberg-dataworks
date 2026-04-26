data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda"
  output_path = "${path.module}/lambda_payload.zip"
}

resource "aws_lambda_function" "validator" {
  function_name    = "${var.prefix}-validator"
  role             = aws_iam_role.lambda_role.arn
  handler          = "validator.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      AUDIT_TABLE     = aws_dynamodb_table.audit.name
      ECS_CLUSTER     = aws_ecs_cluster.main.arn
      TASK_DEFINITION = aws_ecs_task_definition.processor.arn
      SUBNETS         = join(",", aws_subnet.private[*].id)
      SECURITY_GROUP  = aws_security_group.ecs_tasks.id
      AWS_ACCOUNT_ID  = data.aws_caller_identity.current.account_id
      VALID_ORGS      = var.valid_orgs
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.validator.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.ingress.arn
}
