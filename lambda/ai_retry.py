import time
import random
import logging
from typing import Callable, Any, Dict, Optional, Tuple
from botocore.exceptions import ClientError

logger = logging.getLogger()

class RetryConfig:
    """Configuration for retry behavior per service"""
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

# Service-specific retry configurations
RETRY_CONFIGS = {
    "comprehend": RetryConfig(max_attempts=3, base_delay=0.5, max_delay=10.0),
    "bedrock": RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0),
    "transcribe": RetryConfig(max_attempts=2, base_delay=2.0, max_delay=20.0)
}

# Retryable error codes by service
RETRYABLE_ERRORS = {
    "comprehend": ["ThrottlingException", "InternalServerError", "ServiceUnavailable"],
    "bedrock": ["ThrottlingException", "ModelStreamErrorException", "ServiceException"],
    "transcribe": ["LimitExceededException", "InternalFailureException"]
}

def calculate_backoff(attempt: int, config: RetryConfig) -> float:
    """
    Calculate exponential backoff with jitter
    """
    delay = min(
        config.base_delay * (config.exponential_base ** (attempt - 1)),
        config.max_delay
    )
    # Add jitter to prevent thundering herd
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter

def is_retryable_error(error: Exception, service: str) -> bool:
    """
    Determine if an error should trigger a retry
    """
    if not isinstance(error, ClientError):
        return False
    
    error_code = error.response.get('Error', {}).get('Code', '')
    return error_code in RETRYABLE_ERRORS.get(service, [])

def retry_with_backoff(func: Callable, service: str, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
    """
    Execute function with exponential backoff retry logic
    
    Returns:
        Tuple of (result, retry_metadata)
    """
    config = RETRY_CONFIGS.get(service, RetryConfig())
    retry_metadata = {
        "attempts": 0,
        "total_delay_ms": 0,
        "errors": []
    }
    
    last_error = None
    
    for attempt in range(1, config.max_attempts + 1):
        retry_metadata["attempts"] = attempt
        
        try:
            # Log retry attempt if not first
            if attempt > 1:
                logger.info(f"Retry attempt {attempt}/{config.max_attempts} for {service}")
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Success - return result with metadata
            if attempt > 1:
                logger.info(f"{service} succeeded after {attempt} attempts")
            
            return result, retry_metadata
            
        except Exception as e:
            last_error = e
            error_info = {
                "attempt": attempt,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
            retry_metadata["errors"].append(error_info)
            
            # Check if retryable
            if not is_retryable_error(e, service):
                logger.warning(f"{service} non-retryable error: {type(e).__name__}")
                raise
            
            # Don't sleep on last attempt
            if attempt < config.max_attempts:
                delay = calculate_backoff(attempt, config)
                retry_metadata["total_delay_ms"] += int(delay * 1000)
                
                logger.warning(
                    f"{service} attempt {attempt} failed with {type(e).__name__}, "
                    f"retrying in {delay:.1f}s"
                )
                
                time.sleep(delay)
            else:
                logger.error(
                    f"{service} failed after {config.max_attempts} attempts: {str(e)}"
                )
    
    # All retries exhausted
    raise last_error

class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful call")
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise

# Global circuit breakers per service
CIRCUIT_BREAKERS = {
    "comprehend": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    "bedrock": CircuitBreaker(failure_threshold=3, recovery_timeout=120)
}