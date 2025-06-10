import json
import logging
import boto3
import os
from typing import Dict
from utils import (
    get_user_data,
    format_alert_message,
    sns,
    VA_CRISIS_LINE,
    VA_CRISIS_URL
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict, context) -> Dict:
    """
    Alert Dispatcher Lambda - Triggered by EventBridge when low sentiment is detected.
    Sends notifications to trusted contacts via SNS (SMS/Email).
    """
    try:
        # EventBridge events come wrapped in a specific format
        if 'detail' in event:
            detail = event['detail']
        else:
            detail = event
        
        user_id = detail.get('userId')
        sentiment_score = detail.get('sentimentScore')
        text_preview = detail.get('textPreview', '')
        timestamp = detail.get('timestamp')
        
        if not user_id:
            logger.error("No userId provided in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'userId is required'})
            }
        
        logger.info(f"Processing alert for user {user_id} with sentiment score {sentiment_score}")
        
        # Get user data including trusted contact
        user_data = get_user_data(user_id)
        if not user_data:
            logger.error(f"User {user_id} not found")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'User not found'})
            }
        
        trusted_contact = user_data.get('trustedContact')
        if not trusted_contact:
            logger.warning(f"No trusted contact configured for user {user_id}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No trusted contact configured',
                    'userId': user_id
                })
            }
        
        # Format the alert message
        alert_data = format_alert_message(
            user_id=user_id,
            sentiment_score=sentiment_score,
            text_preview=text_preview,
            trusted_contact=trusted_contact
        )
        
        # Determine delivery method and send
        contact_method = trusted_contact.get('preferredMethod', 'SMS')
        contact_phone = trusted_contact.get('phone')
        contact_email = trusted_contact.get('email')
        
        notification_sent = False
        
        if contact_method == 'SMS' and contact_phone:
            # Send SMS via SNS
            try:
                response = sns.publish(
                    PhoneNumber=contact_phone,
                    Message=alert_data['message'],
                    MessageAttributes={
                        'AWS.SNS.SMS.SMSType': {
                            'DataType': 'String',
                            'StringValue': 'Transactional'
                        }
                    }
                )
                logger.info(f"SMS sent to trusted contact for user {user_id}")
                notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send SMS: {str(e)}")
        
        elif contact_method == 'EMAIL' and contact_email:
            # Send Email via SNS
            try:
                response = sns.publish(
                    TopicArn=os.environ.get('SNS_TOPIC_ARN'),  # Or direct email
                    Subject=alert_data['subject'],
                    Message=alert_data['message'],
                    MessageAttributes={
                        'email': {
                            'DataType': 'String',
                            'StringValue': contact_email
                        }
                    }
                )
                logger.info(f"Email sent to trusted contact for user {user_id}")
                notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
        
        # Log the alert for audit purposes
        audit_entry = {
            'userId': user_id,
            'timestamp': timestamp,
            'sentimentScore': sentiment_score,
            'trustedContactName': trusted_contact.get('name'),
            'contactMethod': contact_method,
            'notificationSent': notification_sent,
            'alertType': 'LOW_SENTIMENT'
        }
        
        logger.info(f"Alert audit: {json.dumps(audit_entry)}")
        
        # Store audit trail in DynamoDB or CloudWatch
        # This could be expanded to track alert history
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Alert processed successfully',
                'userId': user_id,
                'notificationSent': notification_sent,
                'contactMethod': contact_method
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in alert dispatcher: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': 'Failed to process alert'
            })
        }

def send_escalation_alert(user_id: str, user_data: Dict) -> bool:
    """
    Send escalation alert if multiple low sentiment check-ins detected.
    This could notify additional contacts or crisis services.
    """
    try:
        # Check recent check-in history
        # If multiple low sentiment scores in past 24-48 hours, escalate
        
        escalation_message = f"""🚨 URGENT: Your6 Escalation Alert

User {user_id} has had multiple concerning check-ins.

Immediate action recommended:
- Contact veteran directly
- Consider wellness check
- VA Crisis Line: {VA_CRISIS_LINE}
- Online support: {VA_CRISIS_URL}

This is an automated escalation based on pattern detection."""
        
        # Send to primary contact and potentially others
        # Implementation would depend on escalation policies
        
        return True
    except Exception as e:
        logger.error(f"Failed to send escalation alert: {str(e)}")
        return False