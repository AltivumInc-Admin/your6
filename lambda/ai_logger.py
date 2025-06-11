import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger()

class AIServiceLogger:
    """
    Structured logging for AI service interactions with detailed metrics
    """
    
    @staticmethod
    def log_request(service: str, operation: str, user_id: str, 
                   input_data: Dict[str, Any]) -> str:
        """Log the start of an AI service request"""
        request_id = str(uuid.uuid4())
        
        log_entry = {
            "event_type": "ai_service_request",
            "service": service,
            "operation": operation,
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "input": {
                "text_length": len(input_data.get("text", "")),
                "text_preview": input_data.get("text", "")[:50] + "..." if len(input_data.get("text", "")) > 50 else input_data.get("text", ""),
                "model": input_data.get("model", "default")
            }
        }
        
        logger.info(json.dumps(log_entry))
        return request_id
    
    @staticmethod
    def log_response(service: str, request_id: str, success: bool,
                    output_data: Optional[Dict[str, Any]] = None,
                    error_data: Optional[Dict[str, Any]] = None,
                    latency_ms: Optional[float] = None):
        """Log the completion of an AI service request"""
        
        log_entry = {
            "event_type": "ai_service_response",
            "service": service,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "latency_ms": latency_ms
        }
        
        if success and output_data:
            log_entry["output"] = {
                "response_length": len(output_data.get("response", "")),
                "sentiment_score": output_data.get("sentiment_score"),
                "confidence": output_data.get("confidence"),
                "fallback_used": output_data.get("fallback_used", False)
            }
        
        if not success and error_data:
            log_entry["error"] = {
                "type": error_data.get("type", "Unknown"),
                "message": error_data.get("message", ""),
                "retry_count": error_data.get("retry_count", 0),
                "will_retry": error_data.get("will_retry", False)
            }
        
        logger.info(json.dumps(log_entry))
    
    @staticmethod
    def log_fallback(reason: str, user_id: str, context: Dict[str, Any]):
        """Log when a fallback response is used"""
        
        log_entry = {
            "event_type": "ai_fallback_used",
            "reason": reason,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "context": {
                "sentiment_score": context.get("sentiment_score"),
                "original_error": context.get("error_type"),
                "fallback_type": context.get("fallback_type")
            }
        }
        
        logger.warning(json.dumps(log_entry))


class MetricsCollector:
    """
    Collect and emit CloudWatch metrics for AI services
    """
    
    def __init__(self, cloudwatch_client):
        self.cloudwatch = cloudwatch_client
        self.namespace = 'Your6/AI'
    
    def record_latency(self, service: str, operation: str, latency_ms: float):
        """Record service latency metric"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'Latency',
                        'Dimensions': [
                            {'Name': 'Service', 'Value': service},
                            {'Name': 'Operation', 'Value': operation}
                        ],
                        'Value': latency_ms,
                        'Unit': 'Milliseconds',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to record latency metric: {str(e)}")
    
    def record_error(self, service: str, error_type: str):
        """Record service error metric"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'Errors',
                        'Dimensions': [
                            {'Name': 'Service', 'Value': service},
                            {'Name': 'ErrorType', 'Value': error_type}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to record error metric: {str(e)}")
    
    def record_fallback(self, fallback_type: str, reason: str):
        """Record fallback usage metric"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'FallbackUsage',
                        'Dimensions': [
                            {'Name': 'Type', 'Value': fallback_type},
                            {'Name': 'Reason', 'Value': reason}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to record fallback metric: {str(e)}")
    
    def record_sentiment_distribution(self, sentiment: str, score: float):
        """Record sentiment score distribution"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'SentimentScore',
                        'Dimensions': [
                            {'Name': 'Sentiment', 'Value': sentiment}
                        ],
                        'Value': score,
                        'Unit': 'None',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to record sentiment metric: {str(e)}")
    
    def record_token_usage(self, model: str, tokens: int):
        """Record Bedrock token usage"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'TokenUsage',
                        'Dimensions': [
                            {'Name': 'Model', 'Value': model}
                        ],
                        'Value': tokens,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to record token usage metric: {str(e)}")


class AIServiceTimer:
    """Context manager for timing AI service calls"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
    
    @property
    def elapsed_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0