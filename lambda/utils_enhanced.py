# Enhanced utility functions for Phase 3
from typing import Dict, Any, Optional

def generate_ai_response_enhanced(text: str, 
                                sentiment_data: Dict,
                                user_id: str,
                                use_ensemble: bool = True) -> Dict[str, Any]:
    """
    Enhanced AI response generation with ensemble and personalization
    """
    try:
        # Prepare context from advanced analysis
        context = {
            'entities': sentiment_data.get('entities', []),
            'entity_context': sentiment_data.get('entity_context', {}),
            'risk_factors': sentiment_data.get('risk_factors', []),
            'temporal_context': sentiment_data.get('temporal_context', {})
        }
        
        # Generate base response
        if use_ensemble and sentiment_data.get('risk_score', 0) > 30:
            # Use ensemble for higher-risk situations
            response_data = ensemble.generate_ensemble_response(
                text,
                sentiment_data,
                user_id,
                context
            )
        else:
            # Use standard generation with enhancements
            response_data = generate_ai_response(
                text,
                sentiment_data.get('sentiment', 'NEUTRAL'),
                user_id,
                sentiment_data.get('sentiment_score', 0)
            )
        
        # Personalize response
        personalized_data = personalizer.personalize_response(
            response_data['response'],
            user_id,
            sentiment_data,
            context
        )
        
        # Merge metadata
        final_metadata = {
            **response_data.get('metadata', {}),
            **personalized_data.get('personalization_metadata', {}),
            'phase3_enhanced': True,
            'risk_aware': sentiment_data.get('risk_score', 0) > 30
        }
        
        return {
            'response': personalized_data['response'],
            'metadata': final_metadata
        }
        
    except Exception as e:
        logger.error(f"Enhanced generation failed: {str(e)}")
        # Fall back to standard generation
        return generate_ai_response(
            text,
            sentiment_data.get('sentiment', 'NEUTRAL'),
            user_id,
            sentiment_data.get('sentiment_score', 0)
        )

def process_check_in_enhanced(user_id: str, text: str) -> Dict:
    """
    Complete enhanced check-in processing with all Phase 3 features
    """
    # Advanced sentiment analysis
    sentiment_data = analyze_sentiment_advanced(text, user_id)
    
    # Generate enhanced response
    ai_response_data = generate_ai_response_enhanced(
        text,
        sentiment_data,
        user_id,
        use_ensemble=True
    )
    
    # Store enhanced check-in
    store_enhanced_checkin(
        user_id=user_id,
        text=text,
        sentiment_data=sentiment_data,
        ai_response_data=ai_response_data
    )
    
    # Check if alert needed
    alert_triggered = False
    if sentiment_data.get('sentiment_score', 0) < SENTIMENT_THRESHOLD or \
       sentiment_data.get('risk_score', 0) > 50:
        alert_triggered = trigger_enhanced_alert(user_id, sentiment_data, text)
    
    # Build response
    return {
        'response': ai_response_data['response'],
        'sentiment': sentiment_data.get('sentiment', 'NEUTRAL'),
        'score': sentiment_data.get('sentiment_score', 0),
        'risk_score': sentiment_data.get('risk_score', 0),
        'entities': sentiment_data.get('entities', [])[:5],
        'alertTriggered': alert_triggered,
        'trajectory': sentiment_data.get('predictive_risk', {}).get('trajectory', 'unknown'),
        'aiMetadata': ai_response_data.get('metadata', {})
    }

def store_enhanced_checkin(user_id: str, 
                          text: str,
                          sentiment_data: Dict,
                          ai_response_data: Dict) -> bool:
    """Store enhanced check-in with all analytics data"""
    try:
        timestamp = datetime.now().isoformat()
        
        # Prepare enhanced check-in record
        checkin_record = {
            'timestamp': timestamp,
            'text': text,
            'sentiment': sentiment_data.get('sentiment'),
            'sentiment_score': Decimal(str(sentiment_data.get('sentiment_score', 0))),
            'risk_score': Decimal(str(sentiment_data.get('risk_score', 0))),
            'risk_factors': sentiment_data.get('risk_factors', []),
            'entities': sentiment_data.get('entities', []),
            'ai_response': ai_response_data.get('response'),
            'model_metadata': ai_response_data.get('metadata', {}),
            'requires_immediate_attention': sentiment_data.get('requires_immediate_attention', False)
        }
        
        # Update user profile
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression="""
                SET lastCheckIn = :timestamp,
                    lastSentiment = :sentiment,
                    lastSentimentScore = :score,
                    #rsk.current_risk_score = :risk_score,
                    #rsk.risk_level = :risk_level,
                    analysis_history = list_append(if_not_exists(analysis_history, :empty), :new_analysis)
            """,
            ExpressionAttributeNames={
                '#rsk': 'risk_analysis'
            },
            ExpressionAttributeValues={
                ':timestamp': timestamp,
                ':sentiment': sentiment_data.get('sentiment'),
                ':score': Decimal(str(sentiment_data.get('sentiment_score', 0))),
                ':risk_score': Decimal(str(sentiment_data.get('risk_score', 0))),
                ':risk_level': sentiment_data.get('predictive_risk', {}).get('risk_level', 'unknown'),
                ':empty': [],
                ':new_analysis': [checkin_record]
            }
        )
        
        # Archive to S3
        archive_to_s3(user_id, checkin_record)
        
        return True
        
    except Exception as e:
        logger.error(f"Error storing enhanced check-in: {str(e)}")
        return False

def trigger_enhanced_alert(user_id: str, sentiment_data: Dict, text: str) -> bool:
    """Trigger enhanced alert with risk-aware routing"""
    try:
        # Determine alert urgency
        risk_score = sentiment_data.get('risk_score', 0)
        requires_immediate = sentiment_data.get('requires_immediate_attention', False)
        
        # Create enhanced alert event
        event_detail = {
            'userId': user_id,
            'sentimentScore': sentiment_data.get('sentiment_score', 0),
            'riskScore': risk_score,
            'riskLevel': sentiment_data.get('predictive_risk', {}).get('risk_level', 'unknown'),
            'textPreview': text[:200],
            'timestamp': datetime.now().isoformat(),
            'alertType': 'ENHANCED_RISK_ALERT' if risk_score > 70 else 'LOW_SENTIMENT',
            'requiresImmediate': requires_immediate,
            'riskFactors': sentiment_data.get('risk_factors', []),
            'patterns': sentiment_data.get('predictive_risk', {}).get('patterns_detected', [])
        }
        
        # Send event
        response = events.put_events(
            Entries=[{
                'Source': 'your6.checkin.enhanced',
                'DetailType': 'Enhanced Risk Alert',
                'Detail': json.dumps(event_detail)
            }]
        )
        
        # For critical risks, also send immediate SNS
        if requires_immediate or risk_score > 85:
            logger.critical(f"IMMEDIATE INTERVENTION REQUIRED for {user_id}")
            # Direct SNS notification to ops team
            if os.environ.get('OPS_SNS_TOPIC_ARN'):
                sns.publish(
                    TopicArn=os.environ['OPS_SNS_TOPIC_ARN'],
                    Subject=f"URGENT: Your6 Critical Risk - {user_id}",
                    Message=json.dumps(event_detail, indent=2)
                )
        
        return True
        
    except Exception as e:
        logger.error(f"Error triggering enhanced alert: {str(e)}")
        return False