terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project = "uni-heidelberg-dataworks"
    }
  }
}

# ECR repository — container registry managed in IaC
resource "aws_ecr_repository" "processor" {
  name                 = "${var.prefix}-processor"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "${var.prefix}-processor-ecr" }
}
