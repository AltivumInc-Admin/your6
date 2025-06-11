# Your6 Project Context for Claude

## Project Overview
Your6 is an AI-powered veteran support mobilization system built for AWS Lambda Hackathon 2025. It transforms passive mental health monitoring into active support network mobilization.

## Current Status (June 10, 2025)
- ✅ Fully deployed to AWS us-east-1
- ✅ API endpoint: https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in
- ✅ Step Functions workflow deployed
- ✅ Dual notification system (SMS + Email) implemented
- ⚠️ SMS requires origination identity (not configured)
- ✅ Email notifications working via SNS topic

## Key Components

### AWS Services Deployed
1. **Lambda Functions**:
   - `Your6-CheckinProcessor` - Main handler
   - `Your6-AlertDispatcher` - Sends notifications
2. **Step Functions**: `Your6-CheckinWorkflow`
3. **DynamoDB**: `your6-users` table
4. **S3**: `your6-checkins-205930636302`
5. **EventBridge**: Low sentiment rule
6. **SNS**: Topic for alerts
7. **API Gateway**: REST endpoint
8. **SQS**: Dead letter queues

### Test User
```json
{
  "userId": "veteran123",
  "trustedContact": {
    "name": "John Smith",
    "phone": "+16176868438",
    "email": "christian.perez@altivum.io",
    "preferredMethod": "SMS"
  },
  "alertThreshold": -0.6
}
```

### Recent Issues Resolved
1. Lambda import errors - Fixed by creating proper zip structure
2. DynamoDB float error - Need to convert to Decimal
3. Bedrock throttling - Using Claude 3.5 Sonnet
4. SMS sandbox mode - No origination identity

### Testing Commands
```bash
# Test via API
curl -X POST https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in \
  -H "Content-Type: application/json" \
  -d '{"userId": "veteran123", "text": "Feeling very isolated today"}'

# Check logs
aws logs tail /aws/lambda/Your6-CheckinProcessor --since 5m
aws logs tail /aws/lambda/Your6-AlertDispatcher --since 5m
```

### Demo Video Script Location
`/Users/christianperez/Desktop/your6/demo-video-script.md`

### GitHub
Repository: https://github.com/AltivumInc-Admin/your6

### What's Left
1. Record demo video (<3 minutes)
2. Fix DynamoDB float issue if time
3. Show working system in hackathon submission