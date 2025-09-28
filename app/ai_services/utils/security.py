import bleach
import re
import logging
from typing import Dict, List, Optional
from profanity_check import predict as is_profane
from django.conf import settings
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class ContentValidator:
    """Validate and sanitize AI-generated content"""
    
    # Allowed HTML tags for educational content
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
        'code', 'pre', 'table', 'thead', 'tbody', 'tr', 'td', 'th'
    ]
    
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'table': ['border', 'cellpadding', 'cellspacing'],
    }
    
    @classmethod
    def sanitize_html(cls, content: str) -> str:
        """Sanitize HTML content"""
        return bleach.clean(
            content,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @classmethod
    def validate_educational_content(cls, content: str) -> Dict[str, any]:
        """Validate educational content quality"""
        issues = []
        score = 100
        
        # Check for profanity
        if is_profane(content):
            issues.append("Content contains inappropriate language")
            score -= 50
        
        # Check content length
        if len(content.strip()) < 10:
            issues.append("Content too short")
            score -= 30
        
        # Check for educational indicators
        educational_keywords = [
            'learn', 'understand', 'concept', 'example', 'definition',
            'explain', 'demonstrate', 'analyze', 'compare', 'evaluate'
        ]
        
        content_lower = content.lower()
        educational_score = sum(1 for keyword in educational_keywords if keyword in content_lower)
        
        if educational_score == 0:
            issues.append("Content lacks educational indicators")
            score -= 20
        
        # Check for proper structure (questions should have question marks, etc.)
        if 'question' in content_lower and '?' not in content:
            issues.append("Questions should end with question marks")
            score -= 10
        
        return {
            'is_valid': score >= 70,
            'score': max(0, score),
            'issues': issues,
            'educational_keywords_found': educational_score
        }
    
    @classmethod
    def sanitize_user_input(cls, user_input: str) -> str:
        """Sanitize user input before sending to AI"""
        # Remove potentially harmful content
        sanitized = bleach.clean(user_input, tags=[], strip=True)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length to prevent token overflow
        max_length = getattr(settings, 'AI_MAX_INPUT_LENGTH', 5000)
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
        
        return sanitized


class EncryptionManager:
    """Handle encryption/decryption of sensitive data"""
    
    def __init__(self):
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not encryption_key:
            # Generate a key if none exists (for development)
            encryption_key = Fernet.generate_key()
            logger.warning("No encryption key found, generated temporary key")
        
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted_data = self.cipher.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            decrypted_data = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


class RateLimiter:
    """Rate limiting utilities"""
    
    @staticmethod
    def get_rate_limit_key(user, service_type: str) -> str:
        """Generate rate limit key for user and service"""
        return f"ai_rate_limit:{user.id}:{service_type}"
    
    @staticmethod
    def check_rate_limit(user, service_type: str, limit: int = 10, window: int = 3600) -> bool:
        """Check if user has exceeded rate limit"""
        from django.core.cache import cache
        
        key = RateLimiter.get_rate_limit_key(user, service_type)
        current_count = cache.get(key, 0)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        cache.set(key, current_count + 1, window)
        return True