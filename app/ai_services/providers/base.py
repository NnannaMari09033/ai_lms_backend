from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AIResponse:
    """Standardized AI response format"""
    content: str
    tokens_used: int
    cost_estimate: float
    model_used: str
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, api_key: str, model: str = None, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for given token count"""
        pass
    
    @abstractmethod
    def get_max_tokens(self) -> int:
        """Get maximum tokens for the model"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass


class AIProviderFactory:
    """Factory for creating AI providers"""
    
    _providers = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class):
        """Register a new AI provider"""
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> BaseAIProvider:
        """Create an AI provider instance"""
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        return provider_class(**kwargs)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available providers"""
        return list(cls._providers.keys())