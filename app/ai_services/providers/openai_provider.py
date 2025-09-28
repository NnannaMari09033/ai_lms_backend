import openai
import logging
from typing import Dict, Optional
from .base import BaseAIProvider, AIResponse, AIProviderFactory

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider implementation"""
    
    COST_PER_1K_TOKENS = {
        'gpt-3.5-turbo': 0.002,
        'gpt-4': 0.03,
        'gpt-4-turbo': 0.01,
    }
    
    MAX_TOKENS = {
        'gpt-3.5-turbo': 4096,
        'gpt-4': 8192,
        'gpt-4-turbo': 128000,
    }
    
    def __init__(self, api_key: str, model: str = 'gpt-3.5-turbo', **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = openai.OpenAI(api_key=api_key)
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2000)
    
    def generate_text(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        """Generate text using OpenAI API"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens)
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            cost_estimate = self.estimate_cost(tokens_used)
            
            return AIResponse(
                content=content,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                model_used=self.model,
                success=True,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
        cost_per_1k = self.COST_PER_1K_TOKENS.get(self.model, 0.002)
        return (tokens / 1000) * cost_per_1k
    
    def get_max_tokens(self) -> int:
        """Get maximum tokens for the model"""
        return self.MAX_TOKENS.get(self.model, 4096)
    
    def validate_config(self) -> bool:
        """Validate OpenAI configuration"""
        try:
            # Test API key with a minimal request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI config validation failed: {e}")
            return False


# Register the provider
AIProviderFactory.register_provider('openai', OpenAIProvider)