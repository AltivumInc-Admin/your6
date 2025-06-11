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
    Modified to work with both API Gateway and Step Functions.
    """
    try:
        # Determine if called from API Gateway or Step Functions
        if 'body' in event and isinstance(event.get('body'), str):
            # API Gateway call
            body = json.loads(event['body'])
            from_api_gateway = True
        else:
            # Step Functions or direct invocation
            body = event
            from_api_gateway = False
        
        # Extract and validate input
        user_id = body.get('userId')
        if not user_id:
            error_response = {'error': 'userId is required'}
            if from_api_gateway:
                return {
                    'statusCode': 400,
                    'body': json.dumps(error_response)
                }
            raise ValueError('userId is required')
        
        # Get user data (including trusted contact info)
        user_data = get_user_data(user_id)
        if not user_data:
            logger.warning(f"User {user_id} not found, creating new user")
        
        # Process input based on type
        text = body.get('text')
        voice_s3_uri = body.get('voiceS3Uri')
        
        if not text and not voice_s3_uri:
            error_response = {'error': 'Either text or voiceS3Uri is required'}
            if from_api_gateway:
                return {
                    'statusCode': 400,
                    'body': json.dumps(error_response)
                }
            raise ValueError('Either text or voiceS3Uri is required')
        
        # Convert voice to text if needed
        if voice_s3_uri:
            logger.info(f"Processing voice input for user {user_id}")
            text = transcribe_audio(voice_s3_uri, user_id)
            if not text:
                error_response = {'error': 'Failed to transcribe audio'}
                if from_api_gateway:
                    return {
                        'statusCode': 500,
                        'body': json.dumps(error_response)
                    }
                raise Exception('Failed to transcribe audio')
        
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
        alert_triggered = False
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
        response_data = {
            'response': ai_response,
            'sentiment': sentiment,
            'score': sentiment_score,
            'entities': key_phrases[:5],  # Limit to top 5 phrases
            'userId': user_id,
            'text': text[:200],  # Include preview for Step Functions
            'alertTriggered': alert_triggered
        }
        
        # Return appropriate format
        if from_api_gateway:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response_data)
            }
        else:
            # For Step Functions, return the data directly
            return response_data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        error_response = {'error': 'Invalid JSON in request body'}
        if from_api_gateway:
            return {
                'statusCode': 400,
                'body': json.dumps(error_response)
            }
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        error_response = {
            'error': 'Internal server error',
            'message': str(e)
        }
        if from_api_gateway:
            return {
                'statusCode': 500,
                'body': json.dumps(error_response)
            }
        raise