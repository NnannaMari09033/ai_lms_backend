import anthropic
import logging
from typing import Dict, Optional
from .base import BaseAIProvider, AIResponse, AIProviderFactory

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude provider implementation"""
    
    COST_PER_1K_TOKENS = {
        'claude-3-haiku-20240307': 0.00025,
        'claude-3-sonnet-20240229': 0.003,
        'claude-3-opus-20240229': 0.015,
    }
    
    MAX_TOKENS = {
        'claude-3-haiku-20240307': 200000,
        'claude-3-sonnet-20240229': 200000,
        'claude-3-opus-20240229': 200000,
    }
    
    def __init__(self, api_key: str, model: str = 'claude-3-haiku-20240307', **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2000)
    
    def generate_text(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        """Generate text using Anthropic API"""
        try:
            message_kwargs = {
                'model': self.model,
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                'temperature': kwargs.get('temperature', self.temperature),
                'messages': [{"role": "user", "content": prompt}]
            }
            
            if system_prompt:
                message_kwargs['system'] = system_prompt
            
            response = self.client.messages.create(**message_kwargs)
            
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            cost_estimate = self.estimate_cost(tokens_used)
            
            return AIResponse(
                content=content,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                model_used=self.model,
                success=True,
                metadata={
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'stop_reason': response.stop_reason
                }
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return AIResponse(
                content="",
                tokens_used=0,
                cost_estimate=0.0,
                model_used=self.model,
                success=False,
                error_message=str(e)
            )
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for given token count"""
        cost_per_1k = self.COST_PER_1K_TOKENS.get(self.model, 0.00025)
        return (tokens / 1000) * cost_per_1k
    
    def get_max_tokens(self) -> int:
        """Get maximum tokens for the model"""
        return self.MAX_TOKENS.get(self.model, 200000)
    
    def validate_config(self) -> bool:
        """Validate Anthropic configuration"""
        try:
            # Test API key with a minimal request
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic config validation failed: {e}")
            return False


# Register the provider
AIProviderFactory.register_provider('anthropic', AnthropicProvider)