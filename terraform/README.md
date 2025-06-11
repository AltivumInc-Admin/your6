# Terraform Deployment for Your6

This directory contains Terraform configuration files as an **alternative** to the CloudFormation deployment. Both achieve the same infrastructure setup.

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- Lambda deployment package built (`lambda-package-v2.zip`)

## File Structure

```
terraform/
├── main.tf         # Main infrastructure configuration
├── variables.tf    # Variable definitions
├── terraform.tfvars # Variable values (create this)
└── README.md       # This file
```

## Deployment Steps

1. **Initialize Terraform**
   ```bash
   cd terraform
   terraform init
   ```

2. **Create terraform.tfvars** (optional - for custom values)
   ```hcl
   aws_region = "us-east-1"
   environment = "prod"
   sentiment_threshold = -0.6
   ```

3. **Plan the deployment**
   ```bash
   terraform plan
   ```

4. **Apply the configuration**
   ```bash
   terraform apply
   ```

5. **Save the outputs**
   ```bash
   terraform output > outputs.txt
   ```

## Key Resources Created

- **2 SQS Dead Letter Queues** - For failed Lambda invocations
- **1 DynamoDB Table** - User data and trusted contacts
- **1 S3 Bucket** - Check-in archival with lifecycle rules
- **1 SNS Topic** - Alert notifications
- **2 Lambda Functions** - Check-in processor and alert dispatcher
- **1 Step Functions State Machine** - Orchestration workflow
- **1 API Gateway** - REST API endpoint
- **EventBridge Rules** - Event-driven alerting
- **IAM Roles and Policies** - Least privilege access

## Comparison with CloudFormation

| Feature | CloudFormation | Terraform |
|---------|---------------|-----------|
| Provider | AWS Native | Multi-cloud |
| State Management | CloudFormation Stack | terraform.tfstate |
| Syntax | YAML/JSON | HCL |
| Community | AWS-focused | Broader ecosystem |

## Managing State

Terraform maintains state in `terraform.tfstate`. For production:

```hcl
terraform {
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "your6/terraform.tfstate"
    region = "us-east-1"
  }
}
```

## Destroy Resources

To remove all resources:
```bash
terraform destroy
```

## Why Both CloudFormation and Terraform?

- **CloudFormation** - Native AWS, zero dependencies, what most AWS teams expect
- **Terraform** - Popular in startups, multi-cloud capable, great for hybrid environments

Both are provided to give deployment flexibility and demonstrate IaC best practices.