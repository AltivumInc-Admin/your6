# Your6 System Architecture Analysis & Debugging Plan

## 1. System Overview

Your6 is a multi-layered AI-powered veteran support system with the following core components:

### 1.1 Entry Points
- **API Gateway** → REST endpoint for check-ins
- **Step Functions** → Orchestrates the workflow
- **EventBridge** → Triggers alert processing

### 1.2 Core Processing Pipeline
```
User Input → Lambda Handler → Enhanced Processing → Risk Assessment → Response Generation → Alert Decision → Notification
```

## 2. Component Architecture & Expected Behavior

### 2.1 Lambda Handler (`handler.py`)
**Purpose**: Entry point for all check-ins
**Expected Behavior**:
- Receive user input (text or voice)
- Call `process_check_in_enhanced()` from `utils_enhanced.py`
- Return structured response with risk data
- Handle both API Gateway and Step Functions invocations

**Key Output Fields**:
```json
{
  "response": "AI-generated support message",
  "sentiment": "POSITIVE|NEUTRAL|NEGATIVE",
  "score": -1.0 to 1.0,
  "risk_score": 0 to 100,
  "entities": ["array of detected entities"],
  "alertTriggered": boolean,
  "trajectory": "improving|stable|declining",
  "aiMetadata": {
    "phase3_enhanced": true,
    "ensemble_used": boolean,
    "risk_factors": ["array"],
    "patterns_detected": ["array"]
  }
}
```

### 2.2 Enhanced Processing (`utils_enhanced.py`)
**Purpose**: Orchestrate Phase 3 features
**Expected Flow**:
1. Call `analyze_sentiment_advanced()` → Should return risk scores
2. Call `generate_ai_response_enhanced()` → Should use ensemble for high risk
3. Call `store_enhanced_checkin()` → Should save all metadata
4. Call `trigger_enhanced_alert()` → Should handle multi-level alerts

### 2.3 Advanced Sentiment Analyzer (`ai_analyzer.py`)
**Purpose**: Calculate risk scores and detect entities
**Expected Behavior**:
1. **Risk Calculation** (`_calculate_risk_score()`):
   - Match text against RISK_INDICATORS patterns
   - Sum weights (gun=8, ending it=10, etc.)
   - Apply temporal multipliers (1.0-1.5x)
   - Return score 0-100+

2. **Entity Detection**:
   - Use Comprehend DetectEntities
   - Extract persons, locations, dates
   - Contextualize entities

3. **Output Structure**:
```python
{
    'sentiment': 'NEGATIVE',
    'sentiment_score': -0.96,
    'risk_score': 18-27,  # For crisis text
    'risk_factors': ['gun', 'ending it'],
    'entities': [...],
    'requires_immediate_attention': True
}
```

### 2.4 Response Personalizer (`ai_personalizer.py`)
**Purpose**: Adapt responses to user profile
**Expected Behavior**:
- Select communication style (military_brief, peer_casual, etc.)
- Adjust tone based on risk level
- Track response effectiveness

### 2.5 Multi-Model Ensemble (`ai_ensemble.py`)
**Purpose**: Use multiple AI models for critical situations
**Expected Behavior**:
- Activate when risk_score > 30
- Query multiple Claude variants
- Blend responses with weights
- Provide consensus response

### 2.6 Predictive Risk Analytics (`ai_predictor.py`)
**Purpose**: Analyze patterns over time
**Expected Behavior**:
- Calculate trajectory from history
- Detect declining patterns
- Return risk predictions

### 2.7 Step Functions State Machine
**Purpose**: Orchestrate workflow and decisions
**Expected Decision Tree**:
```
EvaluateRisk:
├─ risk_score > 95 → CrisisProtocol (Parallel alerts)
├─ risk_score > 85 → ImmediateIntervention
├─ risk_score > 50 OR sentiment < -0.6 → StandardAlert
├─ trajectory = "declining" AND risk_score > 30 → ProactiveOutreach
└─ Default → CheckinComplete
```

## 3. Current System Failures

### 3.1 Risk Score Always 0
**Symptom**: Crisis text with gun/suicide returns risk_score: 0
**Expected**: risk_score: 18-27 minimum

### 3.2 Advanced Analysis Falling Back
**Symptom**: Falls back to basic sentiment analysis
**Expected**: Full risk assessment with entities

### 3.3 Permission Errors
**Symptom**: Comprehend operations denied
**Status**: Partially fixed, needs verification

## 4. Debugging Strategy

### Phase 1: Component Isolation Testing
1. **Unit Tests for Each Module**
   - Test risk calculation in isolation
   - Test entity detection separately
   - Test response generation independently

2. **Integration Tests**
   - Test utils → analyzer flow
   - Test analyzer → personalizer flow
   - Test complete pipeline

### Phase 2: Logging Enhancement
1. Add detailed logging at each step
2. Log all risk calculations
3. Log all fallback decisions
4. Add correlation IDs

### Phase 3: Local Testing Framework
1. Mock AWS services
2. Test with known inputs/outputs
3. Validate each component

### Phase 4: Threshold Calibration
1. Test various text inputs
2. Map risk scores
3. Adjust thresholds
4. Validate escalation paths

## 5. Testing Framework Requirements

### 5.1 Unit Test Structure
```
tests/
├── unit/
│   ├── test_risk_calculator.py
│   ├── test_entity_detector.py
│   ├── test_response_generator.py
│   ├── test_personalizer.py
│   └── test_ensemble.py
├── integration/
│   ├── test_full_pipeline.py
│   ├── test_alert_flow.py
│   └── test_step_functions.py
└── fixtures/
    ├── sample_texts.json
    ├── expected_outputs.json
    └── user_profiles.json
```

### 5.2 Test Scenarios
1. **Crisis Scenarios** (Expected: risk > 95)
   - Explicit suicide mention with method
   - Imminent threat language
   
2. **High Risk** (Expected: risk > 85)
   - Severe depression with self-harm
   - Substance abuse with hopelessness
   
3. **Moderate Risk** (Expected: risk > 50)
   - Persistent negative thoughts
   - Isolation and worthlessness
   
4. **Declining Trajectory** (Expected: proactive outreach)
   - Gradual decline over time
   - Pattern detection

## 6. Implementation Plan

### Step 1: Create Testing Infrastructure (2 hours)
- Set up unit test framework
- Create mock services
- Build test fixtures

### Step 2: Debug Risk Calculation (1 hour)
- Isolate risk calculation
- Test with known inputs
- Fix calculation logic

### Step 3: Fix Integration Flow (2 hours)
- Trace data flow
- Fix connection points
- Ensure proper data passing

### Step 4: Calibrate Thresholds (1 hour)
- Test various scenarios
- Adjust weights/thresholds
- Validate escalation

### Step 5: End-to-End Testing (1 hour)
- Full pipeline tests
- Step Functions validation
- Alert verification

## 7. Success Criteria

1. Crisis text generates risk_score > 95
2. All components pass unit tests
3. Integration tests show proper data flow
4. Step Functions routes correctly based on risk
5. Appropriate alerts trigger for each level
6. No false negatives for crisis situations

## 8. Monitoring & Validation

### 8.1 Key Metrics
- Risk score distribution
- Alert accuracy rate
- Component failure rate
- Response time per component

### 8.2 Validation Checklist
- [ ] Risk calculation returns non-zero for crisis
- [ ] Entity detection completes without fallback
- [ ] Ensemble activates for high risk
- [ ] Step Functions routes match risk levels
- [ ] Alerts fire at appropriate thresholds
- [ ] All permissions verified