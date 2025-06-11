terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

# Data sources
data "aws_caller_identity" "current" {}

# Dead Letter Queues
resource "aws_sqs_queue" "checkin_dlq" {
  name                      = "Your6-CheckinDLQ"
  message_retention_seconds = 1209600 # 14 days
  
  tags = {
    Name        = "Your6-CheckinDLQ"
    Environment = var.environment
    Purpose     = "Failed check-in processing"
  }
}

resource "aws_sqs_queue" "alert_dlq" {
  name                      = "Your6-AlertDLQ"
  message_retention_seconds = 1209600 # 14 days
  
  tags = {
    Name        = "Your6-AlertDLQ"
    Environment = var.environment
    Purpose     = "Failed alert dispatching"
  }
}

# DynamoDB Table
resource "aws_dynamodb_table" "users" {
  name         = "your6-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = {
    Name        = "your6-users"
    Environment = var.environment
    Phase       = "3"
  }
}

# S3 Bucket
resource "aws_s3_bucket" "checkins" {
  bucket = "your6-checkins-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "Your6 Check-ins"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "checkins" {
  bucket = aws_s3_bucket.checkins.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "checkins" {
  bucket = aws_s3_bucket.checkins.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "checkins" {
  bucket = aws_s3_bucket.checkins.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# SNS Topics
resource "aws_sns_topic" "alerts" {
  name         = "Your6-TrustedContactAlerts"
  display_name = "Your6 Alerts"

  tags = {
    Name        = "Your6-TrustedContactAlerts"
    Environment = var.environment
  }
}

resource "aws_sns_topic" "operations_alerts" {
  name         = "Your6-OperationsAlerts"
  display_name = "Your6 Operations Alerts"

  tags = {
    Name        = "Your6-OperationsAlerts"
    Environment = var.environment
    Purpose     = "Crisis and high-risk alerts"
  }
}

# SNS Subscriptions
resource "aws_sns_topic_subscription" "operations_email" {
  topic_arn = aws_sns_topic.operations_alerts.arn
  protocol  = "email"
  endpoint  = "christian.perez0321@gmail.com"
}

# IAM Roles
resource "aws_iam_role" "lambda_execution" {
  name = "Your6-LambdaExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution.name
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "Your6LambdaPolicy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.users.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.checkins.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "comprehend:DetectSentiment",
          "comprehend:DetectKeyPhrases",
          "comprehend:DetectEntities",
          "comprehend:DetectSyntax"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.alerts.arn,
          aws_sns_topic.operations_alerts.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.checkin_dlq.arn,
          aws_sqs_queue.alert_dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.your6_workflow.arn
      }
    ]
  })
}

# Step Functions Role
resource "aws_iam_role" "stepfunctions" {
  name = "Your6-StepFunctionsRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "stepfunctions_policy" {
  name = "Your6StepFunctionsPolicy"
  role = aws_iam_role.stepfunctions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.checkin.arn,
          aws_lambda_function.alert_dispatcher.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.alerts.arn,
          aws_sns_topic.operations_alerts.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.users.arn
      }
    ]
  })
}

# Lambda Functions
resource "aws_lambda_function" "checkin" {
  filename         = "${path.module}/../your6-lambda-phase3-failsafe.zip"
  function_name    = "Your6-CheckinProcessor"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 512
  reserved_concurrent_executions = 100

  dead_letter_config {
    target_arn = aws_sqs_queue.checkin_dlq.arn
  }

  environment {
    variables = {
      DYNAMODB_TABLE    = aws_dynamodb_table.users.name
      S3_BUCKET        = aws_s3_bucket.checkins.id
      SNS_TOPIC_ARN    = aws_sns_topic.alerts.arn
      OPS_SNS_TOPIC_ARN = aws_sns_topic.operations_alerts.arn
      STATE_MACHINE_ARN = aws_sfn_state_machine.your6_workflow.arn
    }
  }

  tags = {
    Name        = "Your6-CheckinProcessor"
    Environment = var.environment
    Phase       = "3"
  }
}

resource "aws_lambda_function" "alert_dispatcher" {
  filename         = "${path.module}/../your6-lambda-phase3-failsafe.zip"
  function_name    = "Your6-AlertDispatcher"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "alert_dispatcher.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 128
  reserved_concurrent_executions = 50

  dead_letter_config {
    target_arn = aws_sqs_queue.alert_dlq.arn
  }

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.users.name
      S3_BUCKET     = aws_s3_bucket.checkins.id
      SNS_TOPIC_ARN = aws_sns_topic.alerts.arn
    }
  }

  tags = {
    Name        = "Your6-AlertDispatcher"
    Environment = var.environment
  }
}

# Step Functions State Machine with Phase 3 Definition
resource "aws_sfn_state_machine" "your6_workflow" {
  name     = "Your6-CheckinWorkflow"
  role_arn = aws_iam_role.stepfunctions.arn

  definition = file("${path.module}/../stepfunctions-phase3-definition.json")

  tags = {
    Name        = "Your6-CheckinWorkflow"
    Environment = var.environment
    Phase       = "3"
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "your6" {
  name        = "Your6-API"
  description = "API for Your6 veteran check-ins"
}

resource "aws_api_gateway_resource" "checkin" {
  rest_api_id = aws_api_gateway_rest_api.your6.id
  parent_id   = aws_api_gateway_rest_api.your6.root_resource_id
  path_part   = "check-in"
}

resource "aws_api_gateway_method" "checkin_post" {
  rest_api_id   = aws_api_gateway_rest_api.your6.id
  resource_id   = aws_api_gateway_resource.checkin.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "checkin" {
  rest_api_id = aws_api_gateway_rest_api.your6.id
  resource_id = aws_api_gateway_resource.checkin.id
  http_method = aws_api_gateway_method.checkin_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.checkin.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.checkin.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.your6.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "your6" {
  depends_on = [
    aws_api_gateway_integration.checkin,
  ]

  rest_api_id = aws_api_gateway_rest_api.your6.id
  stage_name  = var.environment
}

# EventBridge Rules
resource "aws_cloudwatch_event_rule" "low_sentiment" {
  name        = "Your6-LowSentimentRule"
  description = "Triggers alert when sentiment is below threshold"

  event_pattern = jsonencode({
    source      = ["your6.checkin"]
    detail-type = ["Low Sentiment Alert"]
  })
}

resource "aws_cloudwatch_event_rule" "crisis_protocol" {
  name        = "Your6-CrisisProtocolRule"
  description = "Triggers immediate response for crisis situations"

  event_pattern = jsonencode({
    source      = ["your6.checkin.crisis"]
    detail-type = ["Crisis Protocol Alert"]
  })
}

resource "aws_cloudwatch_event_rule" "high_risk" {
  name        = "Your6-HighRiskRule"
  description = "Triggers intervention for high-risk situations"

  event_pattern = jsonencode({
    source      = ["your6.checkin.highrisk"]
    detail-type = ["Immediate Intervention Required"]
  })
}

resource "aws_cloudwatch_event_rule" "proactive" {
  name        = "Your6-ProactiveRule"
  description = "Triggers proactive outreach"

  event_pattern = jsonencode({
    source      = ["your6.checkin.proactive"]
    detail-type = ["Proactive Outreach Recommended"]
  })
}

# Event Targets
resource "aws_cloudwatch_event_target" "alert_dispatcher" {
  rule      = aws_cloudwatch_event_rule.low_sentiment.name
  target_id = "AlertDispatcherTarget"
  arn       = aws_lambda_function.alert_dispatcher.arn
}

resource "aws_cloudwatch_event_target" "crisis_alert" {
  rule      = aws_cloudwatch_event_rule.crisis_protocol.name
  target_id = "CrisisAlertTarget"
  arn       = aws_lambda_function.alert_dispatcher.arn
}

resource "aws_cloudwatch_event_target" "high_risk_alert" {
  rule      = aws_cloudwatch_event_rule.high_risk.name
  target_id = "HighRiskAlertTarget"
  arn       = aws_lambda_function.alert_dispatcher.arn
}

resource "aws_cloudwatch_event_target" "proactive_alert" {
  rule      = aws_cloudwatch_event_rule.proactive.name
  target_id = "ProactiveAlertTarget"
  arn       = aws_lambda_function.alert_dispatcher.arn
}

# Lambda Permissions for EventBridge
resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert_dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.low_sentiment.arn
}

resource "aws_lambda_permission" "eventbridge_crisis" {
  statement_id  = "AllowEventBridgeCrisisInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert_dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.crisis_protocol.arn
}

resource "aws_lambda_permission" "eventbridge_highrisk" {
  statement_id  = "AllowEventBridgeHighRiskInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert_dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.high_risk.arn
}

resource "aws_lambda_permission" "eventbridge_proactive" {
  statement_id  = "AllowEventBridgeProactiveInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert_dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.proactive.arn
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "your6_monitoring" {
  dashboard_name = "Your6-AI-Monitoring"
  
  dashboard_body = file("${path.module}/../cloudwatch-dashboard.json")
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "checkin_processor" {
  name              = "/aws/lambda/Your6-CheckinProcessor"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "alert_dispatcher" {
  name              = "/aws/lambda/Your6-AlertDispatcher"
  retention_in_days = 30
}

# Outputs
output "api_url" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_deployment.your6.invoke_url}/check-in"
}

output "state_machine_arn" {
  description = "Step Functions State Machine ARN"
  value       = aws_sfn_state_machine.your6_workflow.arn
}

output "checkin_dlq_url" {
  description = "Dead Letter Queue URL for failed check-ins"
  value       = aws_sqs_queue.checkin_dlq.url
}

output "alert_dlq_url" {
  description = "Dead Letter Queue URL for failed alerts"
  value       = aws_sqs_queue.alert_dlq.url
}

output "operations_topic_arn" {
  description = "Operations SNS Topic ARN for crisis alerts"
  value       = aws_sns_topic.operations_alerts.arn
}