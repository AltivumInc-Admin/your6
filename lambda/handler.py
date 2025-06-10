import json
import logging
from typing import Dict
from utils import (
    get_user_data,
    transcribe_audio,
    analyze_sentiment,
    generate_ai_response,
    store_checkin,
    trigger_alert,
    SENTIMENT_THRESHOLD
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict, context) -> Dict:
    """
    Main Lambda handler for Your6 check-in processing.
    Accepts text or voice input, analyzes sentiment, generates AI response,
    and triggers alerts if needed.
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        # Extract and validate input
        user_id = body.get('userId')
        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'userId is required'
                })
            }
        
        # Get user data (including trusted contact info)
        user_data = get_user_data(user_id)
        if not user_data:
            logger.warning(f"User {user_id} not found, creating new user")
            # In production, you might want to handle new user registration differently
        
        # Process input based on type
        text = body.get('text')
        voice_s3_uri = body.get('voiceS3Uri')
        
        if not text and not voice_s3_uri:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Either text or voiceS3Uri is required'
                })
            }
        
        # Convert voice to text if needed
        if voice_s3_uri:
            logger.info(f"Processing voice input for user {user_id}")
            text = transcribe_audio(voice_s3_uri, user_id)
            if not text:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Failed to transcribe audio'
                    })
                }
        
        logger.info(f"Processing check-in for user {user_id}: {text[:50]}...")
        
        # Analyze sentiment
        sentiment, sentiment_score, key_phrases = analyze_sentiment(text)
        logger.info(f"Sentiment analysis: {sentiment} ({sentiment_score})")
        
        # Generate AI response
        ai_response = generate_ai_response(text, sentiment, user_id)
        
        # Store check-in data
        stored = store_checkin(
            user_id=user_id,
            text=text,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            ai_response=ai_response,
            key_phrases=key_phrases
        )
        
        if not stored:
            logger.error("Failed to store check-in data")
        
        # Check if we need to trigger an alert
        if sentiment_score < SENTIMENT_THRESHOLD:
            logger.warning(f"Low sentiment detected for user {user_id}: {sentiment_score}")
            
            # Only trigger alert if user has a trusted contact configured
            if user_data and user_data.get('trustedContact'):
                alert_triggered = trigger_alert(user_id, sentiment_score, text)
                if alert_triggered:
                    logger.info(f"Alert triggered for user {user_id}")
                else:
                    logger.error(f"Failed to trigger alert for user {user_id}")
            else:
                logger.info(f"No trusted contact configured for user {user_id}, skipping alert")
        
        # Prepare response
        response_body = {
            'response': ai_response,
            'sentiment': sentiment,
            'score': sentiment_score,
            'entities': key_phrases[:5]  # Limit to top 5 phrases
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # Configure appropriately for production
            },
            'body': json.dumps(response_body)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred processing your check-in'
            })
        }