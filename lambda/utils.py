import boto3
import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

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

# Constants
SENTIMENT_THRESHOLD = -0.6
VA_CRISIS_LINE = "1-800-273-8255 (press 1)"
VA_CRISIS_URL = "https://www.veteranscrisisline.net"
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'your6-users')
BUCKET_NAME = os.environ.get('S3_BUCKET', 'your6-checkins')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')

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

def analyze_sentiment(text: str) -> Tuple[str, float, list]:
    """Analyze sentiment and extract key phrases using Amazon Comprehend."""
    try:
        # Sentiment analysis
        sentiment_response = comprehend.detect_sentiment(
            Text=text,
            LanguageCode='en'
        )
        
        sentiment = sentiment_response['Sentiment']
        sentiment_score = sentiment_response['SentimentScore'][sentiment.capitalize()]
        
        # Convert positive sentiment to positive score, negative to negative
        if sentiment == 'NEGATIVE':
            sentiment_score = -sentiment_score
        elif sentiment == 'POSITIVE':
            sentiment_score = abs(sentiment_score)
        
        # Key phrase extraction
        key_phrases_response = comprehend.detect_key_phrases(
            Text=text,
            LanguageCode='en'
        )
        
        key_phrases = [phrase['Text'] for phrase in key_phrases_response['KeyPhrases']]
        
        return sentiment, sentiment_score, key_phrases
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        return 'NEUTRAL', 0.0, []

def generate_ai_response(text: str, sentiment: str, user_id: str) -> str:
    """Generate supportive response using Amazon Bedrock."""
    try:
        # Load system prompt from file or use default
        try:
            with open('/opt/bedrock_system_prompt.txt', 'r') as f:
                system_prompt = f.read()
        except:
            system_prompt = """You are a supportive AI assistant specifically designed to help veterans. 
            Your responses should be:
            - Empathetic and understanding
            - Non-clinical and conversational
            - Action-oriented when appropriate
            - Respectful of military culture
            - Brief but meaningful (2-3 sentences)
            
            Never provide medical advice or diagnose conditions."""
        
        # Construct the prompt
        prompt = f"""System: {system_prompt}

User (Veteran {user_id}) shared: "{text}"
Detected sentiment: {sentiment}

Provide a brief, supportive response that acknowledges their feelings and offers encouragement."""

        # Call Bedrock (Claude 3.5 Sonnet)
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 200,
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }]
            })
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return "Thank you for checking in. Your willingness to share is a sign of strength. Remember, you're not alone in this."

def store_checkin(user_id: str, text: str, sentiment: str, sentiment_score: float, 
                  ai_response: str, key_phrases: list) -> bool:
    """Store check-in data in DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_NAME)
        timestamp = datetime.now().isoformat()
        
        # Update user record with latest check-in
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET lastCheckIn = :timestamp, lastSentiment = :sentiment, lastSentimentScore = :score',
            ExpressionAttributeValues={
                ':timestamp': timestamp,
                ':sentiment': sentiment,
                ':score': sentiment_score
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