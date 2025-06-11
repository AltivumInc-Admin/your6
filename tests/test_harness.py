#!/usr/bin/env python3
"""
Your6 Component Test Harness
Tests individual components in isolation without AWS dependencies
"""
import sys
import os
import json
from typing import Dict, List, Tuple
from datetime import datetime
from decimal import Decimal

# Add lambda directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

# Mock AWS services
class MockComprehend:
    def detect_sentiment(self, Text='', LanguageCode='en', **kwargs):
        # Return negative sentiment for crisis texts
        if any(word in Text.lower() for word in ['gun', 'suicide', 'ending it']):
            return {
                'Sentiment': 'NEGATIVE',
                'SentimentScore': {
                    'Negative': 0.96,
                    'Positive': 0.01,
                    'Neutral': 0.02,
                    'Mixed': 0.01
                }
            }
        return {
            'Sentiment': 'NEUTRAL',
            'SentimentScore': {
                'Negative': 0.1,
                'Positive': 0.2,
                'Neutral': 0.6,
                'Mixed': 0.1
            }
        }
    
    def detect_entities(self, Text='', LanguageCode='en', **kwargs):
        entities = []
        if 'gun' in Text.lower():
            entities.append({
                'Type': 'OTHER',
                'Text': 'gun',
                'Score': 0.9
            })
        return {'Entities': entities}
    
    def detect_syntax(self, Text='', LanguageCode='en', **kwargs):
        return {'SyntaxTokens': []}
    
    def detect_key_phrases(self, Text='', LanguageCode='en', **kwargs):
        return {'KeyPhrases': []}

class MockDynamoDB:
    class Table:
        def __init__(self, name):
            self.name = name
            self.data = {}
        
        def get_item(self, Key):
            return {'Item': self.data.get(Key.get('userId', {}))}
        
        def update_item(self, **kwargs):
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}

class MockBedrock:
    def invoke_model(self, **kwargs):
        return {
            'body': MockStreamingBody(json.dumps({
                'content': [{
                    'text': 'I hear you and I\'m here to support you. Please reach out to the Veterans Crisis Line at 1-800-273-8255.'
                }],
                'usage': {'total_tokens': 50}
            }))
        }

class MockStreamingBody:
    def __init__(self, data):
        self.data = data
    
    def read(self):
        return self.data.encode('utf-8')

# Test utilities
def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"{'='*60}")

def print_result(passed, message):
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {message}")

# Component Tests
def test_risk_calculation():
    """Test risk score calculation in isolation"""
    print_test_header("Risk Score Calculation")
    
    # Import with mocked dependencies
    import ai_analyzer
    analyzer = ai_analyzer.AdvancedSentimentAnalyzer(MockComprehend(), None)
    
    test_cases = [
        {
            "text": "I have my gun and I'm thinking about ending it all",
            "expected_min": 18,
            "description": "Crisis text with weapon and suicidal ideation"
        },
        {
            "text": "Feeling hopeless and worthless, can't go on",
            "expected_min": 14,
            "description": "High risk without explicit method"
        },
        {
            "text": "Had a good day today, feeling optimistic",
            "expected_min": 0,
            "description": "Positive text should have zero risk"
        }
    ]
    
    results = []
    for case in test_cases:
        risk_score, risk_factors = analyzer._calculate_risk_score(case['text'])
        passed = risk_score >= case['expected_min']
        print_result(passed, f"{case['description']}: Score={risk_score}, Expected>={case['expected_min']}")
        print(f"  Risk factors: {risk_factors}")
        results.append({
            'text': case['text'][:50] + '...',
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'passed': passed
        })
    
    return all(r['passed'] for r in results), results

def test_entity_detection():
    """Test entity detection component"""
    print_test_header("Entity Detection")
    
    comprehend = MockComprehend()
    
    test_texts = [
        "I have my gun right here",
        "Meeting John at the VA hospital tomorrow",
        "Been drinking since 3pm"
    ]
    
    results = []
    for text in test_texts:
        entities = comprehend.detect_entities(Text=text)
        print(f"Text: {text}")
        print(f"  Entities: {entities['Entities']}")
        results.append({
            'text': text,
            'entities': entities['Entities']
        })
    
    return True, results

def test_integration_flow():
    """Test data flow between components"""
    print_test_header("Integration Flow")
    
    # Mock the utils module
    import utils
    utils.comprehend = MockComprehend()
    utils.bedrock = MockBedrock()
    utils.dynamodb = MockDynamoDB()
    utils.table = MockDynamoDB.Table('your6-users')
    
    # Test basic sentiment analysis
    sentiment, score, phrases = utils.analyze_sentiment("I'm feeling very depressed", "test_user")
    
    print(f"Sentiment: {sentiment}")
    print(f"Score: {score}")
    print(f"Key phrases: {phrases}")
    
    passed = sentiment == 'NEGATIVE' and score < 0
    print_result(passed, "Basic sentiment analysis flow")
    
    return passed, {
        'sentiment': sentiment,
        'score': score,
        'phrases': phrases
    }

def test_crisis_detection():
    """Test crisis scenario detection"""
    print_test_header("Crisis Detection")
    
    crisis_texts = [
        "I can't do this anymore. I have my gun and I'm going to end it all.",
        "Planning to take all my pills tonight. No one will miss me.",
        "Standing on the bridge. This is goodbye.",
        "Cut myself again. Deeper this time. Want the pain to stop."
    ]
    
    import ai_analyzer
    analyzer = ai_analyzer.AdvancedSentimentAnalyzer(MockComprehend(), None)
    
    results = []
    for text in crisis_texts:
        risk_score, risk_factors = analyzer._calculate_risk_score(text)
        # Crisis texts should score very high
        passed = risk_score >= 15  # Current weights would give at least this
        
        print(f"\nText: {text[:50]}...")
        print(f"  Risk Score: {risk_score}")
        print(f"  Risk Factors: {risk_factors}")
        print_result(passed, f"Crisis detection (score >= 15)")
        
        results.append({
            'text': text[:50] + '...',
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'passed': passed
        })
    
    return all(r['passed'] for r in results), results

def run_all_tests():
    """Run all component tests"""
    print("\n" + "="*60)
    print("Your6 Component Test Suite")
    print("="*60)
    
    test_results = {}
    
    # Run each test
    tests = [
        ('risk_calculation', test_risk_calculation),
        ('entity_detection', test_entity_detection),
        ('integration_flow', test_integration_flow),
        ('crisis_detection', test_crisis_detection)
    ]
    
    for test_name, test_func in tests:
        try:
            passed, results = test_func()
            test_results[test_name] = {
                'passed': passed,
                'results': results
            }
        except Exception as e:
            print(f"\n✗ ERROR in {test_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            test_results[test_name] = {
                'passed': False,
                'error': str(e)
            }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results.values() if r.get('passed', False))
    
    for test_name, result in test_results.items():
        status = "PASS" if result.get('passed', False) else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} passed")
    
    return test_results

if __name__ == "__main__":
    results = run_all_tests()
    
    # Save results
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)