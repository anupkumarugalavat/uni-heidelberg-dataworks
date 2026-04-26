aws_region = "us-east-1"
prefix     = "member-org-001"
valid_orgs = "ORG-123,ORG-456,UHD-DATA-01"

# create an ECR repository and push your Docker image there first.
# Format: <account_id>.dkr.ecr.<region>.amazonaws.com/<repo_name>:<tag>
container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/processor-app:latest"
