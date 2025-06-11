# Your6 Project Context for Claude

## Project Overview
Your6 is an AI-powered veteran support mobilization system built for AWS Lambda Hackathon 2025. It transforms passive mental health monitoring into active support network mobilization.

## Current Status (June 11, 2025 - Critical Issues Identified)
- ✅ Fully deployed to AWS us-east-1
- ✅ API endpoint: https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in
- ✅ Step Functions workflow deployed with Phase 3 multi-level routing
- ✅ Crisis failsafe implemented and deployed (your6-lambda-phase3-failsafe.zip)
- ✅ Dual notification system (SMS + Email) implemented
- ✅ Operations SNS topic created for crisis alerts
- ⚠️ SMS requires origination identity (toll-free number +18666216560 still PENDING)
- ✅ Email notifications working (christian.perez0321@gmail.com)
- ✅ Amazon Comprehend working perfectly (sentiment analysis confirmed)
- ❌ Bedrock throttling due to 1 req/min limit on Claude 3.5 Sonnet
- ❌ Risk score calculation failing (returns 0 for crisis scenarios)
- ❌ Multi-model ensemble removed (unnecessary complexity)

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

### Current Critical Issues (June 11, 2025 Update)

#### 1. **Bedrock Throttling (Root Cause Identified)**
- **Issue**: Getting ThrottlingException on every request
- **Root Cause**: Multi-model ensemble was calling 3 Claude models simultaneously
- **Math**: 3 models × 3 retries = 9 requests vs 1 request/minute limit
- **Status**: Ensemble disabled, but still hitting 1 req/min limit with single model
- **Solution**: Need to request limit increase OR switch to Claude Haiku (20 req/min)

#### 2. **Risk Score Always Returns 0**
- **Issue**: Crisis text like "gun + suicide" returns risk_score: 0
- **Evidence**: Logs show risk calculated as 90, but API returns 0
- **Impact**: Crisis scenarios route through CheckinComplete instead of CrisisProtocol
- **Theory**: Value lost between calculation and response serialization

#### 3. **SMS Still Pending**
- **Number**: +18666216560
- **Status**: PENDING (checked at 00:21 UTC)
- **Type**: TRANSACTIONAL
- **Expected**: 15 min to 72 hours for activation

#### 4. **Step Functions Not Triggering**
- **Last Run**: June 10, 23:41 UTC
- **Issue**: Lambda completes but doesn't invoke Step Functions
- **Impact**: No alert routing despite successful sentiment analysis

### Demo Video Script
`/Users/christianperez/Desktop/your6/demo-video-script.md`

### GitHub
Repository: https://github.com/AltivumInc-Admin/your6

### What's Working Well
1. **Amazon Comprehend**: Sentiment analysis working perfectly
   - Example: "gun + suicide" → NEGATIVE sentiment, -0.78 score
   - Confirms NLP pipeline is solid
2. **Fallback System**: When Bedrock throttles, system continues with pre-written responses
3. **Alert Triggering**: alertTriggered: true for negative sentiment
4. **Infrastructure**: All AWS services deployed and configured correctly

### Immediate Next Steps
1. **Fix Risk Score Pipeline**
   - Debug why risk_score calculated as 90 becomes 0 in response
   - Check utils_enhanced.py response assembly
   - Verify Step Functions integration

2. **Address Bedrock Throttling**
   - Option A: Request limit increase via AWS Support (24-48 hours)
   - Option B: Switch to Claude Haiku (20 req/min) or Instant (1000 req/min)
   - Option C: Implement caching for common responses

3. **Verify Step Functions**
   - Check why Lambda isn't triggering Step Functions
   - Verify IAM permissions for states:StartExecution
   - Test direct Step Functions invocation

4. **Complete SMS Setup**
   - Check toll-free number status: `aws pinpoint-sms-voice-v2 describe-phone-numbers`
   - Once active, SMS alerts will work automatically

### Architecture Simplification
- **Removed**: Multi-model ensemble (unnecessary complexity)
- **Focus**: Robust failsafes over fancy AI features
- **Principle**: One model, strong safety nets, clear alerts

### Key Learnings

#### From Phase 3 Debugging:
1. **Silent Failures are Dangerous**: Risk calculation failed without alerts
2. **Overengineering Hurts**: Multi-model ensemble created more problems than solutions
3. **Simple is Reliable**: Comprehend + failsafes > complex AI orchestration

#### From Today's Session:
1. **Throttling Root Cause**: Ensemble multiplied requests by 3x
2. **Risk Score Bug**: Calculated correctly (90) but lost in response pipeline
3. **Step Functions Disconnect**: Lambda completes but doesn't trigger workflow

### Testing Evidence
```bash
# Crisis text test
Input: "I have my gun loaded and thinking about ending it all"
Comprehend: ✅ NEGATIVE, -0.78 score
Risk Calculation: ✅ 90 (in logs)
API Response: ❌ risk_score: 0
Step Functions: ❌ Not triggered
Alert: ✅ alertTriggered: true
```

### Critical Path to Demo
1. Fix risk_score pipeline (data flow issue)
2. Ensure Step Functions triggers on high risk
3. Use Claude Haiku to avoid throttling
4. Record demo showing crisis → alert flow