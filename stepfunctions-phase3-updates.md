# Step Functions Phase 3 Updates

## Key Enhancements to State Machine

### 1. **Enhanced Risk Evaluation** (EvaluateRisk State)
The state machine now evaluates multiple risk factors:

- **Crisis Protocol** (risk_score > 95)
  - Parallel execution of alerts
  - Immediate notification to operations team
  - Logs crisis intervention in DynamoDB
  
- **Immediate Intervention** (risk_score > 85)
  - High-priority EventBridge event
  - Includes risk factors and ensemble usage
  
- **Standard Alert** (sentiment < -0.6 OR risk_score > 50)
  - Maintains backward compatibility
  - Includes both sentiment and risk scores
  
- **Proactive Outreach** (trajectory = "declining" AND risk_score > 30)
  - New predictive intervention path
  - Based on risk trajectory analysis

### 2. **Crisis Protocol Branch**
New parallel state for crisis situations:
- Simultaneously alerts trusted contact and operations team
- Ensures no single point of failure
- Logs interventions for pattern analysis

### 3. **Enhanced Output Data**
The workflow now captures:
- `risk_score` - Phase 3 risk assessment
- `trajectory` - Predictive risk direction
- `ensembleUsed` - Whether multi-model was used
- `phase3Enhanced` - Confirmation of Phase 3 features

### 4. **Improved Error Handling**
- Maintains existing retry logic
- Enhanced failure notifications
- Better context in error messages

## Integration Requirements

To deploy these updates:

1. **Update CloudFormation/Terraform** with new definition
2. **Create Operations SNS Topic** (OpsAlertTopicArn)
3. **Grant Additional Permissions**:
   - DynamoDB UpdateItem for crisis logging
   - EventBridge PutEvents for new event types
   
## New Event Types

The enhanced workflow publishes these event types:
- `your6.checkin` - Standard alerts (existing)
- `your6.checkin.crisis` - Crisis protocol events
- `your6.checkin.highrisk` - Immediate intervention
- `your6.checkin.proactive` - Predictive outreach

## Benefits

1. **Multi-Level Response** - Different interventions based on severity
2. **Predictive Actions** - Proactive support before crisis
3. **Better Visibility** - Enhanced tracking of all interventions
4. **Fail-Safe Design** - Parallel execution for critical alerts
5. **AI Integration** - Leverages all Phase 3 AI capabilities

This update ensures the Step Functions workflow fully utilizes the Phase 3 AI enhancements while maintaining backward compatibility.