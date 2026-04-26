# Networking
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs where Fargate tasks run"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs containing the NAT Gateway"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_ip" {
  description = "Elastic IP of the NAT Gateway — whitelist this on downstream systems"
  value       = aws_eip.nat.public_ip
}

# Storage & database
output "s3_bucket_name" {
  description = "Name of the S3 ingress bucket"
  value       = aws_s3_bucket.ingress.id
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB audit table"
  value       = aws_dynamodb_table.audit.name
}

# Compute
output "lambda_function_arn" {
  description = "ARN of the Lambda validator function"
  value       = aws_lambda_function.validator.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS Fargate cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_task_definition_arn" {
  description = "ARN of the processor task definition"
  value       = aws_ecs_task_definition.processor.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL — docker push target for CI/CD"
  value       = aws_ecr_repository.processor.repository_url
}

# IAM
output "ecs_task_role_arn" {
  description = "IAM role ARN used by the ECS task"
  value       = aws_iam_role.ecs_task_role.arn
}

output "ecs_tasks_security_group_id" {
  description = "Security group ID assigned to Fargate tasks"
  value       = aws_security_group.ecs_tasks.id
}
