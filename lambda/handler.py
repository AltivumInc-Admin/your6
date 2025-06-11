import json
import logging
from typing import Dict
from datetime import datetime
from utils import (
    get_user_data,
    transcribe_audio,
    SENTIMENT_THRESHOLD
)
from utils_enhanced import (
    process_check_in_enhanced
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
        
        # Use enhanced processing with Phase 3 features
        response_data = process_check_in_enhanced(user_id, text)
        
        # Add additional fields for compatibility
        response_data['userId'] = user_id
        response_data['text'] = text[:200]  # Include preview for Step Functions
        
        # Log Phase 3 features
        if response_data.get('risk_score', 0) > 0:
            logger.info(f"Risk analysis: score={response_data['risk_score']}, trajectory={response_data.get('trajectory', 'unknown')}")
        if 'aiMetadata' in response_data:
            if response_data['aiMetadata'].get('phase3_enhanced'):
                logger.info("Phase 3 enhanced features active")
            if response_data['aiMetadata'].get('ensemble_used'):
                logger.info(f"Ensemble response generated with {len(response_data['aiMetadata'].get('models_used', []))} models")
        
        # Trigger Step Functions workflow for risk assessment and alert routing
        try:
            import boto3
            import os
            
            events_client = boto3.client('events', region_name='us-east-1')
            
            if response_data.get('risk_score', 0) > 0:
                # Publish event to EventBridge to trigger Step Functions
                event_detail = {
                    'userId': user_id,
                    'riskScore': response_data.get('risk_score', 0),
                    'sentimentScore': response_data.get('score', 0),
                    'sentiment': response_data.get('sentiment', 'NEUTRAL'),
                    'alertTriggered': response_data.get('alertTriggered', False),
                    'trajectory': response_data.get('trajectory', 'unknown'),
                    'textPreview': text[:200],
                    'timestamp': datetime.now().isoformat(),
                    'checkinResult': response_data
                }
                
                events_client.put_events(
                    Entries=[{
                        'Source': 'your6.checkin.processed',
                        'DetailType': 'Check-in Processed',
                        'Detail': json.dumps(event_detail)
                    }]
                )
                logger.info(f"EventBridge event published for risk assessment")
            else:
                logger.info("No risk detected - no event published")
                
        except Exception as e:
            logger.error(f"Failed to publish EventBridge event: {str(e)}")
            # Don't fail the request if EventBridge fails
        
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