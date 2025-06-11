#!/usr/bin/env python3
"""
Test the integration flow to find where risk scores get lost
"""
import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from test_harness import MockComprehend, MockDynamoDB, MockBedrock

def trace_analyze_sentiment_advanced():
    """Trace through analyze_sentiment_advanced to find the issue"""
    print("\n=== Tracing analyze_sentiment_advanced ===")
    
    # Set up mocks
    import utils
    import ai_analyzer
    
    # Create mocked services
    mock_comprehend = MockComprehend()
    mock_table = MockDynamoDB.Table('your6-users')
    
    # Create analyzer with mocks
    analyzer = ai_analyzer.AdvancedSentimentAnalyzer(mock_comprehend, mock_table)
    
    crisis_text = "I have my gun and I'm thinking about ending it all"
    
    try:
        # Call analyze_with_context directly
        print("\n1. Testing analyze_with_context directly:")
        result = analyzer.analyze_with_context(crisis_text, "test_user")
        print(f"   Risk score from analyzer: {result.get('risk_score', 'MISSING')}")
        print(f"   Full result keys: {list(result.keys())}")
        
    except Exception as e:
        print(f"   ERROR in analyze_with_context: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Test _calculate_risk_score directly
        print("\n2. Testing _calculate_risk_score directly:")
        risk_score, risk_factors = analyzer._calculate_risk_score(crisis_text)
        print(f"   Risk score: {risk_score}")
        print(f"   Risk factors: {risk_factors}")

def trace_utils_integration():
    """Trace through utils.py integration"""
    print("\n=== Tracing utils.py integration ===")
    
    import utils
    
    # Mock the services
    utils.comprehend = MockComprehend()
    utils.dynamodb = MockDynamoDB()
    utils.bedrock = MockBedrock()
    utils.sns = type('obj', (object,), {'publish': lambda **k: {'MessageId': '123'}})
    utils.events = type('obj', (object,), {'put_events': lambda **k: {'Entries': []}})
    utils.cloudwatch = type('obj', (object,), {'put_metric_data': lambda **k: None})
    
    # Check if advanced analyzer is initialized
    print(f"\n1. Checking utils initialization:")
    print(f"   Has advanced_analyzer: {hasattr(utils, 'advanced_analyzer')}")
    
    if hasattr(utils, 'advanced_analyzer'):
        print(f"   Type: {type(utils.advanced_analyzer)}")
    
    # Test analyze_sentiment_advanced
    print(f"\n2. Testing analyze_sentiment_advanced:")
    
    crisis_text = "I have my gun and I'm thinking about ending it all"
    
    try:
        result = utils.analyze_sentiment_advanced(crisis_text, "test_user")
        print(f"   Risk score: {result.get('risk_score', 'MISSING')}")
        print(f"   Sentiment: {result.get('sentiment', 'MISSING')}")
        print(f"   Fallback: {result.get('fallback_analysis', False)}")
        print(f"   All keys: {list(result.keys())}")
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

def trace_enhanced_processing():
    """Trace through utils_enhanced.py"""
    print("\n=== Tracing utils_enhanced.py ===")
    
    try:
        import utils_enhanced
        
        print("\n1. Testing process_check_in_enhanced:")
        
        # This should call analyze_sentiment_advanced
        result = utils_enhanced.process_check_in_enhanced(
            "test_user",
            "I have my gun and I'm thinking about ending it all"
        )
        
        print(f"   Risk score: {result.get('risk_score', 'MISSING')}")
        print(f"   Alert triggered: {result.get('alertTriggered', 'MISSING')}")
        print(f"   All keys: {list(result.keys())}")
        
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

def check_permissions_issue():
    """Check if the issue is permissions-related"""
    print("\n=== Checking Permissions Issue ===")
    
    import ai_analyzer
    
    class ComprehendWithoutSyntax:
        """Mock that simulates missing DetectSyntax permission"""
        def detect_sentiment(self, **kwargs):
            return MockComprehend().detect_sentiment(**kwargs)
        
        def detect_entities(self, **kwargs):
            return MockComprehend().detect_entities(**kwargs)
        
        def detect_syntax(self, **kwargs):
            raise Exception("AccessDeniedException: not authorized to perform: comprehend:DetectSyntax")
    
    analyzer = ai_analyzer.AdvancedSentimentAnalyzer(ComprehendWithoutSyntax(), None)
    
    try:
        result = analyzer.analyze_with_context("Crisis text with gun", "test_user")
        print(f"Result when DetectSyntax fails: {result}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("This simulates what happens in production!")

if __name__ == "__main__":
    trace_analyze_sentiment_advanced()
    trace_utils_integration()
    trace_enhanced_processing()
    check_permissions_issue()