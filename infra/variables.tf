variable "aws_region" {
  description = "Target AWS region for deployment"
  default     = "us-east-1"
}

variable "prefix" {
  description = "Unique identifier for resource naming"
  default     = "hybrid-relay"
}

variable "container_image" {
  description = "ECR image URI for the data processor container"
  default     = ""
}

# valid_orgs is injected directly as an environment variable on
# the Lambda function. No SSM parameter or SecureString involved.
variable "valid_orgs" {
  description = "Comma-separated list of permitted organization IDs"
  default     = "ORG-123,ORG-456,UHD-DATA-01"
}

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }
