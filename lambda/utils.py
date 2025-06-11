import boto3
import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
import logging
from decimal import Decimal
import time
from ai_logger import AIServiceLogger, MetricsCollector, AIServiceTimer
from ai_retry import retry_with_backoff, CIRCUIT_BREAKERS
from ai_validator import ResponseValidator, ValidationResult
from ai_fallback import FallbackOrchestrator, FallbackType
from ai_analyzer import AdvancedSentimentAnalyzer, EntityContextualizer
from ai_personalizer import ResponsePersonalizer
from ai_ensemble import MultiModelEnsemble
from ai_predictor import PredictiveRiskAnalytics

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
comprehend = boto3.client('comprehend')
bedrock = boto3.client('bedrock-runtime')
transcribe = boto3.client('transcribe')
sns = boto3.client('sns')
events = boto3.client('events')
cloudwatch = boto3.client('cloudwatch')

# Constants
SENTIMENT_THRESHOLD = -0.6
VA_CRISIS_LINE = "1-800-273-8255 (press 1)"
VA_CRISIS_URL = "https://www.veteranscrisisline.net"
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'your6-users')
BUCKET_NAME = os.environ.get('S3_BUCKET', 'your6-checkins')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')

# Initialize metrics collector and validators
metrics = MetricsCollector(cloudwatch)
validator = ResponseValidator()
fallback_orchestrator = FallbackOrchestrator(sns, cloudwatch)

# Initialize Phase 3 components
table = dynamodb.Table(TABLE_NAME)
advanced_analyzer = AdvancedSentimentAnalyzer(comprehend, table)
personalizer = ResponsePersonalizer(table)
ensemble = MultiModelEnsemble(bedrock, validator, metrics)
risk_predictor = PredictiveRiskAnalytics(table, sns, events)

def get_user_data(user_id: str) -> Optional[Dict]:
    """Fetch user data including trusted contact info from DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'userId': user_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        return None

def transcribe_audio(s3_uri: str, user_id: str) -> Optional[str]:
    """Convert voice audio to text using Amazon Transcribe."""
    try:
        job_name = f"your6-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        response = transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat='wav',
            LanguageCode='en-US'
        )
        
        # Wait for transcription to complete (simplified for demo)
        # In production, use Step Functions or async processing
        import time
        while True:
            status = transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            time.sleep(2)
        
        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            # Fetch transcript (simplified - would need to download from S3)
            return "Transcribed text placeholder"
        
        return None
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return None

def analyze_sentiment_advanced(text: str, user_id: str = "unknown") -> Dict[str, Any]:
    """Advanced sentiment analysis with entity detection and risk scoring"""
    try:
        # Use advanced analyzer
        analysis = advanced_analyzer.analyze_with_context(text, user_id)
        
        # Add entity context
        entity_context = EntityContextualizer.contextualize(
            analysis.get('entities', []),
            text
        )
        analysis['entity_context'] = entity_context
        
        # Run predictive risk analysis
        risk_analysis = risk_predictor.analyze_user_risk(user_id)
        analysis['predictive_risk'] = risk_analysis
        
        return analysis
        
    except Exception as e:
        logger.error(f"Advanced analysis failed, falling back: {str(e)}")
        # Fall back to standard analysis
        sentiment, score, phrases = analyze_sentiment(text, user_id)
        
        # Apply basic risk detection for fallback
        risk_score = 0
        if sentiment == 'NEGATIVE' and score < -0.8:
            # Check for crisis keywords
            crisis_words = ['gun', 'suicide', 'kill myself', 'end it', 'pills', 'jump']
            text_lower = text.lower()
            for word in crisis_words:
                if word in text_lower:
                    risk_score = 95
                    logger.critical(f"FALLBACK CRISIS DETECTION: Found '{word}' in text with negative sentiment")
                    break
            
            if risk_score == 0 and score < -0.9:
                risk_score = 60  # High risk for extreme negative sentiment
        
        return {
            'sentiment': sentiment,
            'sentiment_score': score,
            'key_phrases': phrases,
            'risk_score': risk_score,
            'fallback_analysis': True,
            'fallback_crisis_check': risk_score > 0
        }

def analyze_sentiment(text: str, user_id: str = "unknown") -> Tuple[str, float, list]:
    """Analyze sentiment and extract key phrases using Amazon Comprehend with retry logic."""
    # Start logging
    request_id = AIServiceLogger.log_request(
        service="comprehend",
        operation="detect_sentiment",
        user_id=user_id,
        input_data={"text": text}
    )
    
    with AIServiceTimer() as timer:
        try:
            # Use circuit breaker
            circuit_breaker = CIRCUIT_BREAKERS.get("comprehend")
            
            def comprehend_analysis():
                # Sentiment analysis with retry
                sentiment_result, retry_meta = retry_with_backoff(
                    comprehend.detect_sentiment,
                    "comprehend",
                    Text=text,
                    LanguageCode='en'
                )
                
                # Key phrase extraction with retry
                phrases_result, _ = retry_with_backoff(
                    comprehend.detect_key_phrases,
                    "comprehend",
                    Text=text,
                    LanguageCode='en'
                )
                
                return sentiment_result, phrases_result, retry_meta
            
            # Execute with circuit breaker
            sentiment_response, key_phrases_response, retry_metadata = circuit_breaker.call(comprehend_analysis)
            
            sentiment = sentiment_response['Sentiment']
            all_scores = sentiment_response['SentimentScore']
            sentiment_score = all_scores[sentiment.capitalize()]
            
            # LOG COMPREHEND SUCCESS
            logger.info(f"✅ COMPREHEND WORKS: Sentiment={sentiment}, Score={sentiment_score:.3f}, Confidence={max(all_scores.values()):.3f}")
            
            # Convert positive sentiment to positive score, negative to negative
            if sentiment == 'NEGATIVE':
                sentiment_score = -sentiment_score
            elif sentiment == 'POSITIVE':
                sentiment_score = abs(sentiment_score)
            
            # Calculate confidence
            confidence = max(all_scores.values())
            
            key_phrases = [phrase['Text'] for phrase in key_phrases_response['KeyPhrases']]
            
            # Log successful response
            AIServiceLogger.log_response(
                service="comprehend",
                request_id=request_id,
                success=True,
                output_data={
                    "sentiment_score": sentiment_score,
                    "confidence": confidence,
                    "key_phrases_count": len(key_phrases),
                    "retry_attempts": retry_metadata.get("attempts", 1)
                },
                latency_ms=timer.elapsed_ms
            )
            
            # Record metrics
            metrics.record_latency("comprehend", "detect_sentiment", timer.elapsed_ms)
            metrics.record_sentiment_distribution(sentiment, sentiment_score)
            
            logger.info(f"Comprehend analysis complete: {sentiment} ({sentiment_score:.3f}) with {confidence:.2f} confidence")
            
            return sentiment, sentiment_score, key_phrases
            
        except Exception as e:
            error_type = type(e).__name__
            
            AIServiceLogger.log_response(
                service="comprehend",
                request_id=request_id,
                success=False,
                error_data={
                    "type": error_type,
                    "message": str(e),
                    "will_retry": False
                },
                latency_ms=timer.elapsed_ms
            )
            
            metrics.record_error("comprehend", error_type)
            logger.error(f"Error analyzing sentiment after retries: {str(e)}")
            
            # Return neutral fallback
            metrics.record_fallback("sentiment_analysis", "comprehend_error")
            return 'NEUTRAL', 0.0, []

def generate_ai_response(text: str, sentiment: str, user_id: str, sentiment_score: float = 0.0) -> Dict[str, Any]:
    """Generate supportive response using Amazon Bedrock with retry logic and validation."""
    # Start logging
    request_id = AIServiceLogger.log_request(
        service="bedrock",
        operation="invoke_model",
        user_id=user_id,
        input_data={"text": text, "model": "amazon.nova-pro-v1:0"}
    )
    
    # Prepare sentiment data for validation
    sentiment_data = {
        "dominant": sentiment,
        "sentiment_score": sentiment_score,
        "key_phrases": []  # Will be populated if needed
    }
    
    with AIServiceTimer() as timer:
        try:
            # Load system prompt
            system_prompt = """You are a supportive AI assistant specifically designed to help veterans. 
            Your responses should be:
            - Empathetic and understanding
            - Non-clinical and conversational
            - Action-oriented when appropriate
            - Respectful of military culture
            - Brief but meaningful (2-3 sentences)
            
            Never provide medical advice or diagnose conditions.
            For negative sentiment, always include the Veterans Crisis Line: 1-800-273-8255 (press 1)."""
            
            # Use circuit breaker
            circuit_breaker = CIRCUIT_BREAKERS.get("bedrock")
            
            def invoke_bedrock_with_retry():
                # Construct the prompt
                prompt = f"""System: {system_prompt}

User (Veteran {user_id}) shared: "{text}"
Detected sentiment: {sentiment} (score: {sentiment_score:.2f})

Provide a brief, supportive response that acknowledges their feelings and offers encouragement."""
                
                # Call Bedrock with retry - Nova Pro format
                response, retry_metadata = retry_with_backoff(
                    bedrock.invoke_model,
                    "bedrock",
                    modelId='amazon.nova-pro-v1:0',
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps({
                        "inferenceConfig": {
                            "max_new_tokens": 300,
                            "temperature": 0.7
                        },
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "text": prompt
                                    }
                                ]
                            }
                        ]
                    })
                )
                
                return response, retry_metadata
            
            # Execute with circuit breaker
            response, retry_metadata = circuit_breaker.call(invoke_bedrock_with_retry)
            
            response_body = json.loads(response['body'].read())
            # Nova Pro response format
            ai_text = response_body['output']['message']['content'][0]['text']
            usage = response_body.get('usage', {})
            tokens_used = usage.get('totalTokens', 0)
            
            # Validate response
            validation_result = validator.validate_response(ai_text, sentiment_data)
            
            if not validation_result.is_valid:
                logger.warning(f"Response validation failed: {validation_result.failed_checks}")
                
                # Attempt regeneration once
                if "has_resources" in validation_result.failed_checks and sentiment == "NEGATIVE":
                    # Add crisis line if missing
                    ai_text += f"\n\nRemember, support is available 24/7: Veterans Crisis Line 1-800-273-8255 (press 1)."
                    validation_result = validator.validate_response(ai_text, sentiment_data)
                
                # If still invalid, use fallback
                if not validation_result.is_valid:
                    context = {
                        "user_id": user_id,
                        "sentiment_score": sentiment_score,
                        "error_type": "validation_failed",
                        "validation_errors": validation_result.failed_checks
                    }
                    return fallback_orchestrator.handle_fallback("validation_failed", context)
            
            # Log successful response
            AIServiceLogger.log_response(
                service="bedrock",
                request_id=request_id,
                success=True,
                output_data={
                    "response": ai_text,
                    "response_length": len(ai_text),
                    "tokens_used": tokens_used,
                    "sentiment_score": sentiment_score,
                    "validation_score": validation_result.score,
                    "retry_attempts": retry_metadata.get("attempts", 1)
                },
                latency_ms=timer.elapsed_ms
            )
            
            # Record metrics
            metrics.record_latency("bedrock", "invoke_model", timer.elapsed_ms)
            if tokens_used > 0:
                metrics.record_token_usage("claude-3.5-sonnet", tokens_used)
            
            logger.info(f"Bedrock response validated: score={validation_result.score:.2f}, {len(ai_text)} chars")
            
            return {
                "response": ai_text,
                "metadata": {
                    "model": "claude-3.5-sonnet",
                    "request_id": request_id,
                    "tokens_used": tokens_used,
                    "latency_ms": timer.elapsed_ms,
                    "validation_score": validation_result.score,
                    "retry_attempts": retry_metadata.get("attempts", 1),
                    "fallback": False
                }
            }
            
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            
            AIServiceLogger.log_response(
                service="bedrock",
                request_id=request_id,
                success=False,
                error_data={
                    "type": error_type,
                    "message": error_message,
                    "will_retry": False
                },
                latency_ms=timer.elapsed_ms
            )
            
            metrics.record_error("bedrock", error_type)
            logger.error(f"Bedrock error after retries: {error_type} - {error_message}")
            
            # Determine fallback type
            if "Circuit breaker is open" in str(e):
                fallback_type = "circuit_open"
            elif "retry" in error_message.lower():
                fallback_type = "retry_exhausted"
            else:
                fallback_type = "bedrock_error"
            
            # Use orchestrated fallback
            context = {
                "user_id": user_id,
                "sentiment_score": sentiment_score,
                "error_type": error_type,
                "request_id": request_id
            }
            
            return fallback_orchestrator.handle_fallback(fallback_type, context)

def store_checkin(user_id: str, text: str, sentiment: str, sentiment_score: float, 
                  ai_response: str, key_phrases: list) -> bool:
    """Store check-in data in DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_NAME)
        timestamp = datetime.now().isoformat()
        
        # Convert float to Decimal for DynamoDB
        sentiment_score_decimal = Decimal(str(sentiment_score))
        
        # Update user record with latest check-in
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET lastCheckIn = :timestamp, lastSentiment = :sentiment, lastSentimentScore = :score',
            ExpressionAttributeValues={
                ':timestamp': timestamp,
                ':sentiment': sentiment,
                ':score': sentiment_score_decimal
            }
        )
        
        # Store detailed check-in history (could be separate table)
        checkin_data = {
            'userId': user_id,
            'timestamp': timestamp,
            'text': text,
            'sentiment': sentiment,
            'sentimentScore': sentiment_score,
            'keyPhrases': key_phrases,
            'aiResponse': ai_response
        }
        
        # Archive to S3
        archive_to_s3(user_id, checkin_data)
        
        return True
    except Exception as e:
        logger.error(f"Error storing check-in: {str(e)}")
        return False

def archive_to_s3(user_id: str, checkin_data: Dict) -> bool:
    """Archive check-in data to S3 for long-term storage."""
    try:
        key = f"{user_id}/{datetime.now().strftime('%Y/%m/%d')}/{checkin_data['timestamp']}.json"
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(checkin_data),
            ContentType='application/json'
        )
        
        return True
    except Exception as e:
        logger.error(f"Error archiving to S3: {str(e)}")
        return False

def format_alert_message(user_id: str, sentiment_score: float, text_preview: str, 
                        trusted_contact: Dict) -> Dict:
    """Format alert message for trusted contact."""
    
    # Truncate text preview for privacy
    text_preview = text_preview[:100] + "..." if len(text_preview) > 100 else text_preview
    
    current_time = datetime.now().strftime("%-I:%M %p")
    
    message = f"""📡 Your6 Check-In Alert

[{user_id}] checked in at {current_time}.
The AI detected signs of emotional distress.

✅ You are their trusted contact.

Please consider reaching out today.

Resources:
☎️ Veterans Crisis Line: {VA_CRISIS_LINE}
💬 Suggested: "Hey, saw you weren't doing great. Let's talk."
🔗 {VA_CRISIS_URL}"""

    return {
        'subject': f'Your6 Alert: {user_id} needs support',
        'message': message,
        'contact_name': trusted_contact.get('name', 'Trusted Contact'),
        'contact_method': trusted_contact.get('preferredMethod', 'SMS')
    }

def trigger_alert(user_id: str, sentiment_score: float, text: str) -> bool:
    """Trigger EventBridge event for low sentiment alerts."""
    try:
        event_detail = {
            'userId': user_id,
            'sentimentScore': sentiment_score,
            'textPreview': text[:200],
            'timestamp': datetime.now().isoformat(),
            'alertType': 'LOW_SENTIMENT'
        }
        
        response = events.put_events(
            Entries=[{
                'Source': 'your6.checkin',
                'DetailType': 'Low Sentiment Alert',
                'Detail': json.dumps(event_detail)
            }]
        )
        
        return True
    except Exception as e:
        logger.error(f"Error triggering alert: {str(e)}")
        return False