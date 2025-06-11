# Step Functions Phase 3 Implementation Plan

## Overview
Update the existing Step Functions state machine to fully leverage Phase 3 AI enhancements including risk scoring, multi-level alerts, and predictive interventions.

## Pre-Implementation Checklist

### Current State Assessment
- [x] State Machine ARN: `arn:aws:states:us-east-1:205930636302:stateMachine:Your6-CheckinWorkflow`
- [x] Lambda Functions: Already updated with Phase 3 features
- [x] DynamoDB Table: `your6-users` (existing)
- [x] SNS Topic: `Your6-TrustedContactAlerts` (existing)
- [ ] Operations SNS Topic: Not created yet
- [ ] IAM Permissions: Need updates

## Implementation Steps

### Phase 1: Infrastructure Setup (10 minutes)

#### 1.1 Create Operations SNS Topic
```bash
aws sns create-topic --name Your6-OperationsAlerts --region us-east-1
```
- Purpose: High-priority alerts for crisis situations
- Subscribers: Operations team emails/phones

#### 1.2 Create SNS Subscription
```bash
aws sns subscribe --topic-arn <OPS_TOPIC_ARN> \
  --protocol email \
  --notification-endpoint christian.perez@altivum.io
```

#### 1.3 Update Lambda Environment Variables
```bash
aws lambda update-function-configuration \
  --function-name Your6-CheckinProcessor \
  --environment Variables={OPS_SNS_TOPIC_ARN=<OPS_TOPIC_ARN>}
```

### Phase 2: IAM Permission Updates (15 minutes)

#### 2.1 Step Functions Execution Role Updates
Add permissions for:
- `dynamodb:UpdateItem` on `your6-users` table
- `events:PutEvents` for new event patterns
- `sns:Publish` to Operations topic

#### 2.2 Create IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:205930636302:table/your6-users"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:PutEvents"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "events:source": "your6.checkin*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": [
        "arn:aws:sns:us-east-1:205930636302:Your6-TrustedContactAlerts",
        "arn:aws:sns:us-east-1:205930636302:Your6-OperationsAlerts"
      ]
    }
  ]
}
```

### Phase 3: State Machine Update (20 minutes)

#### 3.1 Backup Current Definition
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --query 'definition' \
  --output text > stepfunctions-backup-$(date +%Y%m%d).json
```

#### 3.2 Prepare New Definition
- Replace placeholders in `stepfunctions-phase3-definition.json`:
  - `${CheckinProcessorArn}`
  - `${OpsAlertTopicArn}`
  - `${DynamoTableName}`
  - `${AlertTopicArn}`

#### 3.3 Update State Machine
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --definition file://stepfunctions-phase3-definition.json \
  --role-arn <EXISTING_ROLE_ARN>
```

### Phase 4: EventBridge Rule Updates (10 minutes)

#### 4.1 Create New Event Rules
Create rules for new event patterns:
- Crisis Protocol Events (`your6.checkin.crisis`)
- High Risk Events (`your6.checkin.highrisk`)
- Proactive Outreach (`your6.checkin.proactive`)

#### 4.2 Update Alert Dispatcher Target
Ensure Alert Dispatcher Lambda handles new event types

### Phase 5: Testing & Validation (30 minutes)

#### 5.1 Test Scenarios
1. **Normal Check-in** (risk < 30, positive sentiment)
   - Should complete without alerts
   
2. **Standard Alert** (sentiment < -0.6)
   - Should trigger standard alert path
   
3. **Moderate Risk** (risk_score = 60)
   - Should trigger standard alert
   
4. **High Risk** (risk_score = 90)
   - Should trigger immediate intervention
   
5. **Crisis Scenario** (risk_score = 98)
   - Should trigger parallel crisis protocol
   - Check both SNS topics received alerts
   
6. **Declining Trajectory** (risk = 40, trajectory = "declining")
   - Should trigger proactive outreach

#### 5.2 Validation Checklist
- [ ] All paths execute correctly
- [ ] Crisis alerts reach operations team
- [ ] DynamoDB updates for crisis interventions
- [ ] EventBridge events published correctly
- [ ] Error handling works as expected

### Phase 6: Documentation Updates (10 minutes)

#### 6.1 Update CLAUDE.md
- Add new event types
- Document crisis thresholds
- Update testing commands

#### 6.2 Update README.md
- Add Phase 3 Step Functions features
- Update architecture diagram
- Document new alert levels

## Risk Mitigation

### Rollback Plan
1. Keep backup of current state machine
2. Test in stages (deploy but don't update triggers first)
3. Monitor CloudWatch logs during testing
4. Have rollback command ready:
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn <ARN> \
  --definition file://stepfunctions-backup.json
```

### Potential Issues & Solutions

1. **IAM Permission Errors**
   - Solution: Incrementally add permissions
   - Test each permission before proceeding

2. **State Machine Syntax Errors**
   - Solution: Validate JSON before deployment
   - Use AWS Console visual editor to verify

3. **Lambda Timeout on Crisis Path**
   - Solution: Ensure parallel execution
   - Set appropriate timeouts

4. **SNS Delivery Failures**
   - Solution: Configure DLQ for SNS
   - Add CloudWatch alarms

## Success Criteria

1. ✅ All test scenarios pass
2. ✅ Crisis alerts delivered < 30 seconds
3. ✅ No disruption to existing workflows
4. ✅ CloudWatch shows successful executions
5. ✅ New metrics visible in dashboard

## Estimated Timeline

- Infrastructure Setup: 10 minutes
- IAM Updates: 15 minutes
- State Machine Update: 20 minutes
- EventBridge Setup: 10 minutes
- Testing: 30 minutes
- Documentation: 10 minutes

**Total: ~95 minutes**

## Post-Implementation

1. Monitor CloudWatch for 24 hours
2. Review execution history
3. Gather metrics on new paths usage
4. Fine-tune thresholds based on data

## Commands Summary

```bash
# 1. Create Ops Topic
aws sns create-topic --name Your6-OperationsAlerts

# 2. Backup current state machine
aws stepfunctions describe-state-machine --state-machine-arn <ARN> > backup.json

# 3. Update state machine
aws stepfunctions update-state-machine --state-machine-arn <ARN> --definition file://new-definition.json

# 4. Test execution
aws stepfunctions start-execution --state-machine-arn <ARN> --input file://test-crisis.json
```