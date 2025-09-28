from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable
from .providers.base import AIProviderFactory
from .utils.circuit_breaker import get_circuit_breaker
import logging

logger = logging.getLogger(__name__)


class OpenAIHealthCheck(BaseHealthCheckBackend):
    """Health check for OpenAI service"""
    
    critical_service = True
    
    def check_status(self):
        try:
            provider = AIProviderFactory.create_provider(
                'openai',
                api_key=settings.OPENAI_API_KEY,
                model='gpt-3.5-turbo'
            )
            
            if not provider.validate_config():
                raise ServiceUnavailable("OpenAI API validation failed")
            
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            raise ServiceUnavailable(f"OpenAI service unavailable: {e}")
    
    def identifier(self):
        return "OpenAI API"


class AnthropicHealthCheck(BaseHealthCheckBackend):
    """Health check for Anthropic service"""
    
    critical_service = False  # Fallback service
    
    def check_status(self):
        try:
            if not hasattr(settings, 'ANTHROPIC_API_KEY') or not settings.ANTHROPIC_API_KEY:
                self.add_error("Anthropic API key not configured")
                return
            
            provider = AIProviderFactory.create_provider(
                'anthropic',
                api_key=settings.ANTHROPIC_API_KEY,
                model='claude-3-haiku-20240307'
            )
            
            if not provider.validate_config():
                raise ServiceUnavailable("Anthropic API validation failed")
            
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            self.add_error(f"Anthropic service error: {e}")
    
    def identifier(self):
        return "Anthropic API"


class AICircuitBreakerHealthCheck(BaseHealthCheckBackend):
    """Health check for AI service circuit breakers"""
    
    critical_service = True
    
    def check_status(self):
        try:
            services = ['quiz_generation', 'lesson_summary', 'flashcard_generation']
            failed_services = []
            
            for service in services:
                breaker = get_circuit_breaker(service)
                status = breaker.get_status()
                
                if status['state'] == 'open':
                    failed_services.append(f"{service} (circuit open)")
                elif status['failure_count'] > 3:
                    failed_services.append(f"{service} (high failure rate)")
            
            if failed_services:
                raise ServiceUnavailable(f"Circuit breakers failing: {', '.join(failed_services)}")
            
        except Exception as e:
            logger.error(f"Circuit breaker health check failed: {e}")
            raise ServiceUnavailable(f"Circuit breaker check failed: {e}")
    
    def identifier(self):
        return "AI Circuit Breakers"


class AIUsageLimitsHealthCheck(BaseHealthCheckBackend):
    """Health check for AI usage limits"""
    
    critical_service = False
    
    def check_status(self):
        try:
            from .models import AIUsageLimit
            
            # Check if usage limits are configured
            limits = AIUsageLimit.objects.all()
            if not limits.exists():
                self.add_error("No AI usage limits configured")
            
            # Check for reasonable limits
            for limit in limits:
                if limit.monthly_limit <= 0:
                    self.add_error(f"Invalid limit for {limit.role}: {limit.monthly_limit}")
                elif limit.monthly_limit > 10000:
                    self.add_error(f"Unusually high limit for {limit.role}: {limit.monthly_limit}")
            
        except Exception as e:
            logger.error(f"AI usage limits health check failed: {e}")
            self.add_error(f"Usage limits check failed: {e}")
    
    def identifier(self):
        return "AI Usage Limits"