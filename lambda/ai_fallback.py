import logging
import json
from typing import Dict, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger()

class FallbackType(Enum):
    """Types of fallback responses"""
    BEDROCK_ERROR = "SYSTEM_FALLBACK_BEDROCK_ERROR"
    VALIDATION_FAILED = "SYSTEM_FALLBACK_VALIDATION_FAILED"
    TIMEOUT = "SYSTEM_FALLBACK_TIMEOUT"
    CIRCUIT_OPEN = "SYSTEM_FALLBACK_CIRCUIT_OPEN"
    RETRY_EXHAUSTED = "SYSTEM_FALLBACK_RETRY_EXHAUSTED"
    UNKNOWN = "SYSTEM_FALLBACK_UNKNOWN"

class FallbackResponse:
    """Tiered fallback response system"""
    
    # Base fallback messages by type
    FALLBACK_TEMPLATES = {
        FallbackType.BEDROCK_ERROR: {
            "response": (
                "I hear you and want to provide the support you deserve. "
                "While I'm experiencing technical difficulties, please know that "
                "your check-in has been received and your trusted contact will be "
                "notified if needed. You're not alone. "
                "Veterans Crisis Line: 1-800-273-8255 (press 1). "
                "[{indicator}]"
            ),
            "priority": "high"
        },
        FallbackType.VALIDATION_FAILED: {
            "response": (
                "Thank you for checking in with Your6. Your message has been received "
                "and I want you to know that reaching out shows real strength. "
                "Your trusted contacts are here to support you. "
                "If you need immediate help: Veterans Crisis Line 1-800-273-8255, press 1. "
                "[{indicator}]"
            ),
            "priority": "medium"
        },
        FallbackType.TIMEOUT: {
            "response": (
                "Your check-in is being processed. While our system catches up, "
                "please remember that help is always available. Your trusted contact "
                "has been notified based on your sentiment score. "
                "For immediate support: Veterans Crisis Line 1-800-273-8255, press 1. "
                "[{indicator}]"
            ),
            "priority": "high"
        },
        FallbackType.CIRCUIT_OPEN: {
            "response": (
                "We're experiencing high demand but your check-in has been logged. "
                "Your support network has been activated if needed. Remember, you have "
                "people who care about you. "
                "Crisis support available 24/7: 1-800-273-8255, press 1. "
                "[{indicator}]"
            ),
            "priority": "medium"
        },
        FallbackType.RETRY_EXHAUSTED: {
            "response": (
                "I'm having trouble generating a personalized response right now, "
                "but I want you to know your check-in was received. Based on your "
                "sentiment, we've activated your support network. "
                "You're not alone in this fight. "
                "Veterans Crisis Line: 1-800-273-8255 (press 1). "
                "[{indicator}]"
            ),
            "priority": "high"
        },
        FallbackType.UNKNOWN: {
            "response": (
                "Thank you for checking in. While I process your message, please "
                "know that your wellbeing matters and support is available. "
                "Your trusted contacts have been notified if intervention is needed. "
                "24/7 support: Veterans Crisis Line 1-800-273-8255, press 1. "
                "[{indicator}]"
            ),
            "priority": "low"
        }
    }
    
    # High-risk sentiment threshold
    HIGH_RISK_THRESHOLD = -0.8
    
    @classmethod
    def get_response(cls, 
                    fallback_type: FallbackType,
                    context: Dict[str, any]) -> Dict[str, any]:
        """
        Get appropriate fallback response with context
        """
        template = cls.FALLBACK_TEMPLATES.get(
            fallback_type, 
            cls.FALLBACK_TEMPLATES[FallbackType.UNKNOWN]
        )
        
        # Format response with indicator
        response_text = template["response"].format(
            indicator=fallback_type.value
        )
        
        # Enhance for high-risk situations
        sentiment_score = context.get("sentiment_score", 0)
        if sentiment_score < cls.HIGH_RISK_THRESHOLD:
            response_text = cls._enhance_for_high_risk(response_text, context)
        
        # Build metadata
        metadata = {
            "fallback": True,
            "fallback_type": fallback_type.value,
            "priority": template["priority"],
            "context": {
                "user_id": context.get("user_id"),
                "sentiment_score": sentiment_score,
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": context.get("error_type"),
                "retry_count": context.get("retry_count", 0)
            }
        }
        
        # Log fallback usage
        logger.warning(f"Fallback response used: {json.dumps(metadata)}")
        
        return {
            "response": response_text,
            "metadata": metadata
        }
    
    @classmethod
    def _enhance_for_high_risk(cls, response: str, context: Dict) -> str:
        """
        Enhance response for high-risk situations
        """
        # Prepend urgent message
        urgent_prefix = (
            "🚨 Your message indicates you may be in crisis. "
            "Please reach out for help immediately. "
        )
        
        # Add personal touch if user_id available
        user_id = context.get("user_id", "friend")
        personal_note = f"\n\n{user_id}, you matter and people care about you. "
        
        return urgent_prefix + response + personal_note
    
    @classmethod
    def should_alert_operations(cls, 
                               fallback_type: FallbackType,
                               context: Dict) -> bool:
        """
        Determine if operations team should be alerted
        """
        sentiment_score = context.get("sentiment_score", 0)
        priority = cls.FALLBACK_TEMPLATES[fallback_type]["priority"]
        
        # Alert for high-risk + high priority fallbacks
        if sentiment_score < cls.HIGH_RISK_THRESHOLD and priority == "high":
            return True
        
        # Alert for repeated fallbacks
        if context.get("retry_count", 0) >= 3:
            return True
        
        # Alert for circuit breaker open
        if fallback_type == FallbackType.CIRCUIT_OPEN:
            return True
        
        return False

class FallbackOrchestrator:
    """Orchestrates fallback responses and alerting"""
    
    def __init__(self, sns_client, cloudwatch_client):
        self.sns = sns_client
        self.cloudwatch = cloudwatch_client
        self.ops_topic_arn = None  # Set via environment variable
    
    def handle_fallback(self,
                       error_type: str,
                       context: Dict,
                       original_error: Optional[Exception] = None) -> Dict:
        """
        Main entry point for fallback handling
        """
        # Map error to fallback type
        fallback_type = self._map_error_to_fallback(error_type, original_error)
        
        # Get fallback response
        response_data = FallbackResponse.get_response(fallback_type, context)
        
        # Check if ops alert needed
        if FallbackResponse.should_alert_operations(fallback_type, context):
            self._alert_operations(fallback_type, context, response_data)
        
        # Record metrics
        self._record_fallback_metrics(fallback_type, context)
        
        return response_data
    
    def _map_error_to_fallback(self, 
                              error_type: str, 
                              error: Optional[Exception]) -> FallbackType:
        """Map error types to fallback types"""
        
        error_mapping = {
            "bedrock_error": FallbackType.BEDROCK_ERROR,
            "validation_failed": FallbackType.VALIDATION_FAILED,
            "timeout": FallbackType.TIMEOUT,
            "circuit_open": FallbackType.CIRCUIT_OPEN,
            "retry_exhausted": FallbackType.RETRY_EXHAUSTED
        }
        
        return error_mapping.get(error_type, FallbackType.UNKNOWN)
    
    def _alert_operations(self, 
                         fallback_type: FallbackType,
                         context: Dict,
                         response_data: Dict):
        """Send alert to operations team"""
        
        if not self.ops_topic_arn:
            logger.warning("Operations topic ARN not configured")
            return
        
        alert_message = {
            "alert_type": "HIGH_RISK_FALLBACK",
            "fallback_type": fallback_type.value,
            "user_id": context.get("user_id"),
            "sentiment_score": context.get("sentiment_score"),
            "timestamp": datetime.utcnow().isoformat(),
            "response_metadata": response_data["metadata"],
            "action_required": "Review user check-in and verify alert was sent"
        }
        
        try:
            self.sns.publish(
                TopicArn=self.ops_topic_arn,
                Subject=f"Your6 URGENT: High-risk fallback for {context.get('user_id')}",
                Message=json.dumps(alert_message, indent=2)
            )
            logger.info("Operations team alerted for high-risk fallback")
        except Exception as e:
            logger.error(f"Failed to alert operations: {str(e)}")
    
    def _record_fallback_metrics(self, 
                                fallback_type: FallbackType,
                                context: Dict):
        """Record CloudWatch metrics for fallback usage"""
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace='Your6/AI',
                MetricData=[
                    {
                        'MetricName': 'FallbackUsage',
                        'Dimensions': [
                            {'Name': 'Type', 'Value': fallback_type.name},
                            {'Name': 'Priority', 'Value': 
                             FallbackResponse.FALLBACK_TEMPLATES[fallback_type]["priority"]}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            # Record high-risk fallback separately
            if context.get("sentiment_score", 0) < FallbackResponse.HIGH_RISK_THRESHOLD:
                self.cloudwatch.put_metric_data(
                    Namespace='Your6/AI',
                    MetricData=[
                        {
                            'MetricName': 'HighRiskFallback',
                            'Value': 1,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow()
                        }
                    ]
                )
        except Exception as e:
            logger.error(f"Failed to record fallback metrics: {str(e)}")