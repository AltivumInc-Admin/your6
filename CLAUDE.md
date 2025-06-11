# Your6 Project Context for Claude

## Project Overview
Your6 is an AI-powered veteran support mobilization system built for AWS Lambda Hackathon 2025. It transforms passive mental health monitoring into active support network mobilization.

## Current Status (June 11, 2025 - Post Phase 3 Debug)
- ✅ Fully deployed to AWS us-east-1
- ✅ API endpoint: https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in
- ✅ Step Functions workflow deployed with Phase 3 multi-level routing
- ✅ Crisis failsafe implemented and deployed (your6-lambda-phase3-failsafe.zip)
- ✅ Dual notification system (SMS + Email) implemented
- ✅ Operations SNS topic created for crisis alerts
- ⚠️ SMS requires origination identity (toll-free number ordered but not activated)
- ✅ Email notifications working (christian.perez0321@gmail.com)

## Key Components

### AWS Services Deployed
1. **Lambda Functions**:
   - `Your6-CheckinProcessor` - Main handler with Phase 3 enhancements
   - `Your6-AlertDispatcher` - Sends notifications
2. **Step Functions**: `Your6-CheckinWorkflow` (updated with 4-level routing)
3. **DynamoDB**: `your6-users` table
4. **S3**: `your6-checkins-205930636302`
5. **EventBridge**: 4 rules (crisis, high-risk, standard, proactive)
6. **SNS**: 
   - `Your6-TrustedContactAlerts` - Main alerts
   - `Your6-OperationsAlerts` - Crisis alerts
7. **API Gateway**: REST endpoint
8. **SQS**: Dead letter queues
9. **CloudWatch**: Dashboard and logging

### Phase 3 Alert Levels
1. **Crisis Protocol** (risk > 95): Parallel alerts, ops notification
2. **Immediate Intervention** (risk > 85): High-priority escalation
3. **Standard Alert** (risk > 50 OR sentiment < -0.6): Regular notification
4. **Proactive Outreach** (declining trajectory): Preventive intervention

### Test User
```json
{
  "userId": "veteran123",
  "trustedContact": {
    "name": "John Smith",
    "phone": "+16176868438",
    "email": "christian.perez0321@gmail.com",
    "preferredMethod": "SMS"
  },
  "alertThreshold": -0.6
}
```

### Critical Fixes Applied (June 11)
1. **Risk Score Bug**: Advanced analyzer was failing, returning risk_score: 0
   - Added null checks for user profiles
   - Added DetectSyntax permission
   - Implemented crisis failsafe patterns
2. **Step Functions**: Fixed to handle variable response structures
3. **IAM Permissions**: Added Comprehend DetectEntities/DetectSyntax, CloudWatch PutMetricData
4. **Failsafe Implementation**: Pattern matching for crisis keywords (gun, suicide, etc.)

### Testing Commands
```bash
# Test via API
curl -X POST https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in \
  -H "Content-Type: application/json" \
  -d '{"userId": "veteran123", "text": "Feeling very isolated today"}'

# Test crisis scenario (should trigger high risk)
curl -X POST https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in \
  -H "Content-Type: application/json" \
  -d '{"userId": "veteran123", "text": "I have my gun and thinking about ending it all"}'

# Check logs
aws logs tail /aws/lambda/Your6-CheckinProcessor --since 5m --region us-east-1
aws logs tail /aws/lambda/Your6-AlertDispatcher --since 5m --region us-east-1

# Check Step Functions execution
aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-east-1:205930636302:stateMachine:Your6-CheckinWorkflow --region us-east-1 --max-items 5
```

### Current Lambda Package
- **File**: `your6-lambda-phase3-failsafe.zip`
- **Key Features**: Crisis failsafe, enhanced logging, Phase 3 AI features
- **Last Updated**: June 11, 2025

### Infrastructure as Code
- **Terraform**: Fully updated in `/terraform/main.tf`
- **CloudFormation**: Multiple templates available
- **Step Functions Definition**: `stepfunctions-phase3-definition.json`

### Test Results
- Normal text: risk_score = 0 → CheckinComplete ✓
- Crisis text: risk_score = 95 → ImmediateIntervention ✓
- Extreme crisis: Inconsistent (sometimes 0, sometimes 95)

### Known Issues
1. **Inconsistent Failsafe**: Crisis detection works ~70% of time
2. **SMS Not Configured**: Toll-free number pending activation
3. **Bedrock Throttling**: Causes fallback responses

### Demo Video Script
`/Users/christianperez/Desktop/your6/demo-video-script.md`

### GitHub
Repository: https://github.com/AltivumInc-Admin/your6

### Next Steps
1. Monitor crisis failsafe consistency
2. Activate SMS toll-free number
3. Record demo video (<3 minutes)
4. Submit to hackathon with working crisis detection
5. Consider implementing continuous Lambda deployment to avoid caching issues

### Key Learning
The system was silently failing on crisis detection due to:
- Missing IAM permissions causing advanced analysis to fail
- Fallback path returning risk_score: 0
- No visibility into the failure

Solution: Added comprehensive failsafes and logging throughout the pipeline.