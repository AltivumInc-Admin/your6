variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
  
  validation {
    condition     = var.lambda_timeout >= 3 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 3 and 900 seconds."
  }
}

variable "sentiment_threshold" {
  description = "Sentiment score threshold for triggering alerts"
  type        = number
  default     = -0.6
  
  validation {
    condition     = var.sentiment_threshold >= -1 && var.sentiment_threshold <= 0
    error_message = "Sentiment threshold must be between -1 and 0."
  }
}

variable "dlq_retention_days" {
  description = "Number of days to retain messages in DLQ"
  type        = number
  default     = 14
  
  validation {
    condition     = var.dlq_retention_days >= 1 && var.dlq_retention_days <= 14
    error_message = "DLQ retention must be between 1 and 14 days."
  }
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Your6"
    ManagedBy   = "Terraform"
    Purpose     = "Veteran Support System"
    Repository  = "https://github.com/AltivumInc-Admin/your6"
  }
}