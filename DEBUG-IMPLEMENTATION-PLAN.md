# Your6 Debug Implementation Plan

## Executive Summary

The Your6 system has a critical bug where risk assessment returns 0 for obvious crisis situations. This plan provides a systematic approach to debug and fix the issue.

## Root Cause Analysis

### Primary Issue
The risk scoring pipeline is broken at multiple points:
1. Advanced analyzer fails due to permissions → falls back to basic analysis
2. Basic analysis returns risk_score: 0 by design
3. Even with permissions fixed, risk calculation may not be executing

### Secondary Issues
1. No visibility into component failures
2. No unit tests to isolate problems
3. Complex integration makes debugging difficult

## Debugging Approach

### Phase 1: Build Testing Infrastructure (Immediate)

#### 1.1 Create Local Test Harness
```python
# test_harness.py
import sys
sys.path.append('./lambda')

# Mock AWS services
class MockComprehend:
    def detect_sentiment(self, **kwargs):
        return {
            'Sentiment': 'NEGATIVE',
            'SentimentScore': {
                'Negative': 0.96,
                'Positive': 0.01,
                'Neutral': 0.02,
                'Mixed': 0.01
            }
        }
    
    def detect_entities(self, **kwargs):
        return {'Entities': []}
    
    def detect_syntax(self, **kwargs):
        return {'SyntaxTokens': []}

# Test individual components
def test_risk_calculation():
    from ai_analyzer import AdvancedSentimentAnalyzer
    analyzer = AdvancedSentimentAnalyzer(MockComprehend(), None)
    
    crisis_text = "I have my gun and I'm thinking about ending it all"
    risk_score, factors = analyzer._calculate_risk_score(crisis_text)
    
    print(f"Risk Score: {risk_score}")
    print(f"Risk Factors: {factors}")
    assert risk_score > 15, f"Risk score too low: {risk_score}"
```

#### 1.2 Component Test Suite
- Test risk calculator in isolation
- Test entity detector separately  
- Test response generator independently
- Test integration points

### Phase 2: Fix Risk Calculation (Priority 1)

#### 2.1 Debug Current Implementation
1. Add logging to every step of risk calculation
2. Test with known crisis texts
3. Verify pattern matching works
4. Check score accumulation

#### 2.2 Implement Fixes
```python
# Enhanced risk calculation with logging
def _calculate_risk_score(self, text: str) -> Tuple[float, List[str]]:
    logger.info(f"Calculating risk score for text: {text[:100]}...")
    risk_score = 0.0
    risk_factors = []
    text_lower = text.lower()
    
    for pattern, weight in self.RISK_INDICATORS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            risk_score += weight
            risk_factors.append(pattern)
            logger.info(f"Matched pattern: {pattern} (weight: {weight})")
    
    logger.info(f"Final risk score: {risk_score}, factors: {risk_factors}")
    return risk_score, risk_factors
```

### Phase 3: Fix Integration Flow

#### 3.1 Trace Data Flow
1. Log at every handoff point
2. Verify data structure at each step
3. Ensure no data loss between components

#### 3.2 Fix Connection Points
```python
# Add verification at each step
def analyze_sentiment_advanced(text: str, user_id: str) -> Dict:
    logger.info("Starting advanced sentiment analysis")
    try:
        analysis = advanced_analyzer.analyze_with_context(text, user_id)
        logger.info(f"Advanced analysis result: risk_score={analysis.get('risk_score', 'MISSING')}")
        
        if analysis.get('risk_score', 0) == 0:
            logger.warning("Risk score is 0 - this may indicate a calculation failure")
            
        return analysis
    except Exception as e:
        logger.error(f"Advanced analysis failed: {str(e)}")
        logger.error(f"Falling back to basic analysis")
        # Return with explicit risk calculation
        return fallback_with_risk_calculation(text, user_id)
```

### Phase 4: Threshold Calibration

#### 4.1 Test Scenarios
```python
test_cases = [
    {
        "text": "I have a gun and I'm going to end it all",
        "expected_risk": 95,
        "expected_path": "CrisisProtocol"
    },
    {
        "text": "Feeling hopeless and drinking heavily",
        "expected_risk": 60,
        "expected_path": "StandardAlert"
    }
]
```

#### 4.2 Adjust Thresholds
- Option A: Increase risk weights
- Option B: Lower Step Functions thresholds
- Option C: Both

### Phase 5: End-to-End Validation

#### 5.1 Lambda Testing
1. Deploy with enhanced logging
2. Test via API with known inputs
3. Verify risk scores in CloudWatch

#### 5.2 Step Functions Testing
1. Test each path with specific inputs
2. Verify routing decisions
3. Confirm alerts trigger correctly

## Implementation Timeline

### Day 1 (Today)
1. **Hour 1**: Build local test harness
2. **Hour 2**: Debug risk calculation
3. **Hour 3**: Fix and test locally
4. **Hour 4**: Deploy and test in AWS

### Day 2
1. **Morning**: Integration testing
2. **Afternoon**: Threshold calibration
3. **Evening**: Full system validation

## Quick Wins (Do First)

### 1. Add Failsafe for Extreme Sentiment
```python
# In utils_enhanced.py
if sentiment_data.get('sentiment_score', 0) < -0.9:
    sentiment_data['risk_score'] = max(
        sentiment_data.get('risk_score', 0), 
        80  # Minimum risk for extreme negative sentiment
    )
    logger.warning(f"Extreme negative sentiment detected, minimum risk set to 80")
```

### 2. Add Debug Endpoint
```python
# In handler.py
if event.get('debug_mode'):
    return {
        'raw_sentiment_data': sentiment_data,
        'risk_calculation_log': risk_log,
        'component_status': component_health
    }
```

### 3. Emergency Fix for Crisis Detection
```python
# Pattern-based override for obvious crisis
crisis_patterns = ['gun', 'suicide', 'kill myself', 'end it all']
if any(pattern in text.lower() for pattern in crisis_patterns):
    risk_score = max(risk_score, 95)
    logger.critical(f"Crisis pattern detected - override risk to 95")
```

## Monitoring Plan

### Real-time Monitoring
1. CloudWatch dashboard for risk score distribution
2. Alarms for risk_score = 0 with negative sentiment
3. Log analysis for fallback frequency

### Validation Metrics
- Crisis detection rate (should be 100%)
- False negative rate (should be 0%)
- Component success rate (should be >95%)

## Next Steps

1. **Immediate**: Implement failsafe for extreme sentiment
2. **Today**: Build test harness and debug risk calculation
3. **Tomorrow**: Full integration testing and calibration
4. **This Week**: Deploy fixes and monitor

This plan ensures we systematically identify and fix the risk assessment failure while building proper testing infrastructure for long-term reliability.