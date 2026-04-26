# ECS cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.prefix}-cluster"
}

# ECS task definition for the processor container
resource "aws_ecs_task_definition" "processor" {
  family                   = "${var.prefix}-processor"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_exec_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name      = "processor"
    image     = var.container_image != "" ? var.container_image : "${aws_ecr_repository.processor.repository_url}:latest"
    essential = true

    # processor.py needs no hardcoded values or SSM lookups.
    environment = [
      { name = "AUDIT_TABLE", value = aws_dynamodb_table.audit.name },
      { name = "AWS_REGION", value = var.aws_region }
    ]
  }])
}
