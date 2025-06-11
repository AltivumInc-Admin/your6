# Your6 System Review - Complete Analysis

## Critical Thresholds and Triggers

### Sentiment Analysis Thresholds
- **ALERT THRESHOLD: -0.6** (defined in utils.py line 21)
- Alert triggers when sentiment_score < -0.6
- Sentiment scores from Amazon Comprehend are converted:
  - NEGATIVE sentiment → negative score (e.g., -0.85)
  - POSITIVE sentiment → positive score (e.g., 0.85)
  - NEUTRAL sentiment → score around 0

### Alert Logic Flow
1. User submits check-in (text or voice)
2. Sentiment analysis via Amazon Comprehend
3. If sentiment_score < -0.6 AND user has trustedContact:
   - EventBridge event triggered
   - alert_dispatcher Lambda invoked
   - SMS attempted first (if phone available)
   - Email also sent (if email available)

## Data Models

### DynamoDB Table: your6-users
```json
{
  "userId": "veteran123",
  "alertThreshold": -0.6,
  "trustedContact": {
    "name": "John Smith",
    "phone": "+16176868438",
    "email": "christian.perez@altivum.io",
    "preferredMethod": "SMS"
  },
  "lastCheckIn": "2024-06-10T15:30:00Z",
  "lastSentiment": "NEGATIVE",
  "lastSentimentScore": -0.85
}
```

### S3 Archive Structure
- Bucket: your6-checkins-205930636302
- Path: `{userId}/{year}/{month}/{day}/{timestamp}.json`
- Contains full check-in data including AI response

## Security Analysis

### IAM Permissions
- Lambda has access to:
  - DynamoDB (read/write to your6-users table only)
  - S3 (read/write to checkins bucket)
  - Comprehend (sentiment analysis)
  - Bedrock (AI response generation)
  - SNS (publish for alerts)
  - EventBridge (put events)

### SNS Topic Policy (FIXED)
- Now allows email subscriptions with proper permissions
- Allows Lambda to publish
- Allows public email subscriptions (restricted to email protocol)

### Data Protection
- S3 bucket has public access blocked
- DynamoDB uses AWS managed encryption
- No PII in CloudWatch logs (text truncated to 200 chars)

## API Endpoints

### POST /check-in
**Request:**
```json
{
  "userId": "veteran123",
  "text": "Feeling very isolated and hopeless today"
}
```

**Response:**
```json
{
  "response": "AI-generated supportive message",
  "sentiment": "NEGATIVE",
  "score": -0.85,
  "entities": ["isolated", "hopeless"],
  "alertTriggered": true
}
```

## Test Scenarios

### Trigger Alert Test
To trigger an alert, sentiment score must be < -0.6. Example texts:
- "I feel completely hopeless and isolated"
- "The nightmares won't stop, I can't take this anymore"
- "Everything feels pointless, I'm struggling badly"

### Non-Alert Test
These should NOT trigger alerts (score > -0.6):
- "Had a rough day but pushing through"
- "Feeling okay, just tired"
- "Not great but managing"

## Current System Status

### Working
- ✅ API Gateway endpoint active
- ✅ Step Functions workflow deployed
- ✅ DynamoDB table configured with test user
- ✅ Email notifications via SNS
- ✅ Sentiment analysis and AI responses

### Pending
- ⏳ SMS notifications (toll-free number +18666216560 pending activation)
- ⏳ DynamoDB Decimal conversion (float error exists but non-blocking)

## How to Test

1. **Via API Gateway:**
```bash
curl -X POST https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in \
  -H "Content-Type: application/json" \
  -d '{"userId": "veteran123", "text": "I feel completely hopeless and alone"}'
```

2. **Via Step Functions:**
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:205930636302:stateMachine:Your6-CheckinWorkflow \
  --input '{"userId": "veteran123", "text": "The darkness is overwhelming today"}' \
  --region us-east-1
```

## Key Insights
- System designed for proactive support mobilization
- Dual notification system ensures redundancy
- Sentiment threshold (-0.6) calibrated for serious concerns
- Privacy-focused: minimal data exposure, truncated previews
- Serverless architecture for scalability