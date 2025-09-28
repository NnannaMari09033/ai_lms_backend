import time
import logging
from typing import Callable, Any, Optional
from functools import wraps
from pybreaker import CircuitBreaker
from django.core.cache import cache

logger = logging.getLogger(__name__)


class AIServiceCircuitBreaker:
    """Circuit breaker for AI services"""
    
    def __init__(self, service_name: str, failure_threshold: int = 5, 
                 recovery_timeout: int = 60, expected_exception: type = Exception):
        self.service_name = service_name
        self.breaker = CircuitBreaker(
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            exclude=[KeyboardInterrupt]
        )
        
        # Add listeners
        self.breaker.add_listener(self._on_circuit_open)
        self.breaker.add_listener(self._on_circuit_close)
        self.breaker.add_listener(self._on_circuit_half_open)
    
    def _on_circuit_open(self):
        """Called when circuit opens"""
        logger.warning(f"Circuit breaker OPENED for {self.service_name}")
        cache.set(f"circuit_breaker:{self.service_name}:status", "OPEN", 300)
    
    def _on_circuit_close(self):
        """Called when circuit closes"""
        logger.info(f"Circuit breaker CLOSED for {self.service_name}")
        cache.set(f"circuit_breaker:{self.service_name}:status", "CLOSED", 300)
    
    def _on_circuit_half_open(self):
        """Called when circuit is half-open"""
        logger.info(f"Circuit breaker HALF-OPEN for {self.service_name}")
        cache.set(f"circuit_breaker:{self.service_name}:status", "HALF_OPEN", 300)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        try:
            return self.breaker(func)(*args, **kwargs)
        except Exception as e:
            logger.error(f"Circuit breaker call failed for {self.service_name}: {e}")
            raise
    
    def get_status(self) -> dict:
        """Get circuit breaker status"""
        return {
            'service': self.service_name,
            'state': self.breaker.current_state,
            'failure_count': self.breaker.fail_counter,
            'last_failure_time': getattr(self.breaker, 'last_failure', None),
            'next_attempt_time': getattr(self.breaker, 'next_attempt_time', None)
        }


# Global circuit breakers for different AI services
_circuit_breakers = {}


def get_circuit_breaker(service_name: str) -> AIServiceCircuitBreaker:
    """Get or create circuit breaker for service"""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = AIServiceCircuitBreaker(service_name)
    return _circuit_breakers[service_name]


def circuit_breaker(service_name: str):
    """Decorator to add circuit breaker protection to functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(service_name)
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


class RetryManager:
    """Manage retry logic for AI operations"""
    
    @staticmethod
    def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        """Calculate exponential backoff delay"""
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)
    
    @staticmethod
    def should_retry(exception: Exception, attempt: int, max_attempts: int = 3) -> bool:
        """Determine if operation should be retried"""
        if attempt >= max_attempts:
            return False
        
        # Don't retry on authentication errors
        if "authentication" in str(exception).lower() or "unauthorized" in str(exception).lower():
            return False
        
        # Don't retry on quota exceeded errors
        if "quota" in str(exception).lower() or "rate limit" in str(exception).lower():
            return False
        
        return True


def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator to add retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not RetryManager.should_retry(e, attempt, max_attempts):
                        break
                    
                    if attempt < max_attempts - 1:  # Don't sleep on last attempt
                        delay = RetryManager.exponential_backoff(attempt, base_delay)
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                        time.sleep(delay)
            
            # All attempts failed
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator