import json
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from celery import shared_task

from .models import AIUsageLog, GeneratedContent, AIUsageLimit, AIServiceConfig
from .providers.base import AIProviderFactory
from .utils.security import ContentValidator, EncryptionManager, RateLimiter
from .utils.circuit_breaker import circuit_breaker, retry_with_backoff
from app.courses.models import Lesson

logger = logging.getLogger(__name__)


class AIUsageTracker:
    """Enhanced AI usage tracking with security and limits"""
    
    @staticmethod
    def check_usage_limit(user, service_type: str) -> Dict[str, Any]:
        """Check if user has exceeded their monthly AI usage limit"""
        try:
            # Get user's role-based limit
            limit_obj = AIUsageLimit.objects.get(role=user.role)
            monthly_limit = limit_obj.monthly_limit
        except AIUsageLimit.DoesNotExist:
            # Fallback to settings if no limit defined
            monthly_limit = settings.AI_USAGE_LIMITS.get(user.role, 50)
        
        # Check rate limiting (per hour)
        if not RateLimiter.check_rate_limit(user, service_type, limit=10, window=3600):
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded (10 requests per hour)',
                'retry_after': 3600
            }
        
        # Count current month usage
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_usage = AIUsageLog.objects.filter(
            user=user,
            created_at__gte=current_month,
            success=True
        ).count()
        
        remaining = monthly_limit - current_usage
        
        return {
            'allowed': current_usage < monthly_limit,
            'current_usage': current_usage,
            'monthly_limit': monthly_limit,
            'remaining': max(0, remaining),
            'reason': 'Monthly limit exceeded' if current_usage >= monthly_limit else None
        }
    
    @staticmethod
    def log_usage(user, service_type: str, tokens_used: int = 0, 
                  cost_estimate: float = 0.0, success: bool = True,
                  error_message: str = None, request_data: Dict = None,
                  response_data: Dict = None, provider: str = None,
                  model_used: str = None, **kwargs) -> AIUsageLog:
        """Enhanced usage logging with encryption for sensitive data"""
        
        # Encrypt sensitive data
        encryption_manager = EncryptionManager()
        encrypted_request = None
        encrypted_response = None
        
        try:
            if request_data:
                encrypted_request = encryption_manager.encrypt(json.dumps(request_data))
            if response_data:
                encrypted_response = encryption_manager.encrypt(json.dumps(response_data))
        except Exception as e:
            logger.error(f"Failed to encrypt usage data: {e}")
        
        return AIUsageLog.objects.create(
            user=user,
            service_type=service_type,
            tokens_used=tokens_used,
            cost_estimate=Decimal(str(cost_estimate)),
            success=success,
            error_message=error_message,
            request_data=encrypted_request or json.dumps(request_data or {}),
            response_data=encrypted_response or json.dumps(response_data or {}),
            provider=provider,
            model_used=model_used,
            **kwargs
        )


class EnhancedAIService:
    """Enhanced AI service with multi-provider support and security"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.config = self._get_service_config()
        self.provider = self._get_provider()
        self.content_validator = ContentValidator()
    
    def _get_service_config(self) -> Dict:
        """Get service configuration"""
        try:
            config_obj = AIServiceConfig.objects.get(service_name=self.service_name)
            if not config_obj.is_enabled:
                raise ValueError(f"Service {self.service_name} is disabled")
            return config_obj.config_data
        except AIServiceConfig.DoesNotExist:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for service"""
        defaults = {
            'quiz_generation': {
                'provider': 'openai',
                'model': 'gpt-3.5-turbo',
                'temperature': 0.7,
                'max_tokens': 2000,
                'fallback_provider': 'anthropic',
                'fallback_model': 'claude-3-haiku-20240307'
            },
            'lesson_summary': {
                'provider': 'openai',
                'model': 'gpt-3.5-turbo',
                'temperature': 0.3,
                'max_tokens': 1000,
                'fallback_provider': 'anthropic',
                'fallback_model': 'claude-3-haiku-20240307'
            },
            'flashcard_generation': {
                'provider': 'openai',
                'model': 'gpt-3.5-turbo',
                'temperature': 0.5,
                'max_tokens': 1500,
                'fallback_provider': 'anthropic',
                'fallback_model': 'claude-3-haiku-20240307'
            }
        }
        return defaults.get(self.service_name, defaults['quiz_generation'])
    
    def _get_provider(self):
        """Get AI provider instance with fallback"""
        provider_name = self.config.get('provider', 'openai')
        model = self.config.get('model', 'gpt-3.5-turbo')
        
        try:
            
            if provider_name == 'openai':
                api_key = settings.OPENAI_API_KEY
            elif provider_name == 'anthropic':
                api_key = settings.ANTHROPIC_API_KEY
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
            
            provider = AIProviderFactory.create_provider(
                provider_name,
                api_key=api_key,
                model=model,
                temperature=self.config.get('temperature', 0.7),
                max_tokens=self.config.get('max_tokens', 2000)
            )
            
            # Validate provider configuration
            if not provider.validate_config():
                raise ValueError(f"Provider {provider_name} configuration is invalid")
            
            return provider
            
        except Exception as e:
            logger.error(f"Failed to initialize primary provider {provider_name}: {e}")
            return self._get_fallback_provider()
    
    def _get_fallback_provider(self):
        """Get fallback provider"""
        fallback_provider = self.config.get('fallback_provider')
        fallback_model = self.config.get('fallback_model')
        
        if not fallback_provider:
            raise ValueError("No fallback provider configured")
        
        try:
            if fallback_provider == 'openai':
                api_key = settings.OPENAI_API_KEY
            elif fallback_provider == 'anthropic':
                api_key = settings.ANTHROPIC_API_KEY
            else:
                raise ValueError(f"Unknown fallback provider: {fallback_provider}")
            
            return AIProviderFactory.create_provider(
                fallback_provider,
                api_key=api_key,
                model=fallback_model,
                temperature=self.config.get('temperature', 0.7),
                max_tokens=self.config.get('max_tokens', 2000)
            )
        except Exception as e:
            logger.error(f"Failed to initialize fallback provider: {e}")
            raise ValueError("No working AI provider available")
    
    @circuit_breaker('ai_service')
    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def generate_content(self, user, prompt: str, system_prompt: str = None, 
                        **kwargs) -> Dict[str, Any]:
        """Generate content with enhanced error handling and validation"""
        
        # Check usage limits
        usage_check = AIUsageTracker.check_usage_limit(user, self.service_name)
        if not usage_check['allowed']:
            raise ValueError(usage_check['reason'])
        
        # Sanitize input
        sanitized_prompt = self.content_validator.sanitize_user_input(prompt)
        if system_prompt:
            system_prompt = self.content_validator.sanitize_user_input(system_prompt)
        
        # Generate content using provider
        response = self.provider.generate_text(
            prompt=sanitized_prompt,
            system_prompt=system_prompt,
            **kwargs
        )
        
        if not response.success:
            raise ValueError(f"AI generation failed: {response.error_message}")
        
        # Validate generated content
        validation_result = self.content_validator.validate_educational_content(response.content)
        
        # Log usage
        usage_log = AIUsageTracker.log_usage(
            user=user,
            service_type=self.service_name,
            tokens_used=response.tokens_used,
            cost_estimate=response.cost_estimate,
            success=True,
            provider=self.config.get('provider'),
            model_used=response.model_used,
            request_data={
                'prompt_length': len(sanitized_prompt),
                'system_prompt_length': len(system_prompt) if system_prompt else 0,
                **kwargs
            },
            response_data={
                'content_length': len(response.content),
                'validation_score': validation_result['score'],
                'validation_issues': validation_result['issues']
            }
        )
        
        return {
            'content': response.content,
            'tokens_used': response.tokens_used,
            'cost_estimate': response.cost_estimate,
            'model_used': response.model_used,
            'provider': self.config.get('provider'),
            'validation': validation_result,
            'usage_log_id': usage_log.id,
            'metadata': response.metadata
        }


class QuizGenerationService(EnhancedAIService):
    """Enhanced quiz generation service"""
    
    def __init__(self):
        super().__init__('quiz_generation')
    
    def generate_quiz(self, user, lesson_id: int, num_questions: int = 5,
                     difficulty: str = 'medium', question_types: List[str] = None) -> Dict:
        """Generate a quiz from lesson content with enhanced features"""
        
        try:
            # Get lesson content
            lesson = Lesson.objects.get(id=lesson_id)
            
            # Check cache first
            cache_key = f"quiz_gen_{lesson_id}_{num_questions}_{difficulty}_{hash(str(question_types))}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached quiz for lesson {lesson_id}")
                return cached_result
            
            # Prepare prompts
            question_types = question_types or ['multiple_choice']
            system_prompt = self._build_quiz_system_prompt(difficulty, question_types)
            human_prompt = self._build_quiz_human_prompt(lesson.content, num_questions)
            
            # Generate content
            result = self.generate_content(
                user=user,
                prompt=human_prompt,
                system_prompt=system_prompt,
                lesson_id=lesson_id
            )
            
            # Parse and validate quiz data
            quiz_data = self._parse_quiz_response(result['content'])
            
            # Store generated content for review
            generated_content = GeneratedContent.objects.create(
                user=user,
                content_type='quiz',
                source_lesson=lesson,
                source_text=lesson.content[:1000],
                generated_data=quiz_data,
                prompt_used=f"{system_prompt}\n\n{human_prompt}",
                usage_log_id=result['usage_log_id'],
                status='auto_approved' if user.is_instructor() else 'pending',
                validation_score=result['validation']['score']
            )
            
            final_result = {
                'quiz_data': quiz_data,
                'generated_content_id': generated_content.id,
                'status': generated_content.status,
                'tokens_used': result['tokens_used'],
                'cost_estimate': result['cost_estimate'],
                'provider': result['provider'],
                'model_used': result['model_used'],
                'validation': result['validation']
            }
            
            # Cache result for 2 hours if validation score is good
            if result['validation']['score'] >= 80:
                cache.set(cache_key, final_result, 7200)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Quiz generation failed for lesson {lesson_id}: {e}")
            # Log failed usage
            AIUsageTracker.log_usage(
                user=user,
                service_type='quiz_generation',
                success=False,
                error_message=str(e),
                request_data={
                    'lesson_id': lesson_id,
                    'num_questions': num_questions,
                    'difficulty': difficulty
                }
            )
            raise
    
    def _build_quiz_system_prompt(self, difficulty: str, question_types: List[str]) -> str:
        """Build enhanced system prompt for quiz generation"""
        return f"""You are an expert educational content creator specializing in assessment design. Generate a high-quality quiz based on the provided lesson content.

REQUIREMENTS:
- Difficulty level: {difficulty}
- Question types: {', '.join(question_types)}
- Ensure questions test understanding, application, and analysis - not just memorization
- Questions should be clear, unambiguous, and educationally sound
- For multiple choice questions, include 4 plausible options with only one correct answer
- Provide detailed explanations for correct answers
- Ensure content is appropriate for educational use
- Return response in valid JSON format only

QUALITY STANDARDS:
- Questions should align with learning objectives
- Distractors should be plausible but clearly incorrect
- Language should be clear and accessible
- Content should be factually accurate

JSON STRUCTURE:
{{
    "questions": [
        {{
            "question": "Clear, specific question text",
            "type": "multiple_choice|true_false|short_answer",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A",
            "explanation": "Detailed explanation of why this answer is correct",
            "difficulty": "{difficulty}",
            "learning_objective": "What this question tests"
        }}
    ],
    "metadata": {{
        "total_questions": {len(question_types)},
        "difficulty_level": "{difficulty}",
        "estimated_time_minutes": 15
    }}
}}"""
    
    def _build_quiz_human_prompt(self, lesson_content: str, num_questions: int) -> str:
        """Build human prompt with lesson content"""
        # Limit content to avoid token limits while preserving key information
        max_content_length = 3000
        if len(lesson_content) > max_content_length:
            # Try to preserve complete sentences
            truncated = lesson_content[:max_content_length]
            last_period = truncated.rfind('.')
            if last_period > max_content_length * 0.8:  # If we can preserve 80% and get complete sentence
                lesson_content = truncated[:last_period + 1]
            else:
                lesson_content = truncated + "..."
        
        return f"""Generate {num_questions} quiz questions based on this lesson content:

LESSON CONTENT:
{lesson_content}

Focus on the key concepts, main ideas, and learning objectives. Ensure questions test different levels of understanding (knowledge, comprehension, application, analysis)."""
     
    def _parse_quiz_response(self, response_content: str) -> Dict:
        """Enhanced quiz response parsing with validation"""
        try:
            # Try to extract JSON from response
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON found in response")
            
            json_str = response_content[start_idx:end_idx]
            quiz_data = json.loads(json_str)
            
            # Validate structure
            if 'questions' not in quiz_data:
                raise ValueError("Invalid quiz format: missing 'questions' key")
            
            # Validate each question
            for i, question in enumerate(quiz_data['questions']):
                required_fields = ['question', 'type', 'correct_answer']
                for field in required_fields:
                    if field not in question:
                        raise ValueError(f"Question {i+1} missing required field: {field}")
                
                # Validate multiple choice questions have options
                if question['type'] == 'multiple_choice' and 'options' not in question:
                    raise ValueError(f"Multiple choice question {i+1} missing options")
            
            return quiz_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {e}")
            raise ValueError("Invalid JSON response from AI service")


# Async task for background processing
@shared_task
def generate_quiz_async(user_id: int, lesson_id: int, **kwargs):
    """Generate quiz asynchronously"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        service = QuizGenerationService()
        result = service.generate_quiz(user, lesson_id, **kwargs)
        
        # Notify user of completion (could send email, websocket, etc.)
        logger.info(f"Async quiz generation completed for user {user_id}, lesson {lesson_id}")
        return result
        
    except Exception as e:
        logger.error(f"Async quiz generation failed: {e}")
        raise


class SummarizationService(EnhancedAIService):
    """Enhanced summarization service"""
    
    def __init__(self):
        super().__init__('lesson_summary')
    
    def generate_summary(self, user, lesson_id: int, summary_length: str = 'medium',
                        focus_areas: List[str] = None) -> Dict:
        """Generate enhanced lesson summary"""
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            
            # Check cache
            cache_key = f"summary_{lesson_id}_{summary_length}_{hash(str(focus_areas))}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Prepare prompts
            system_prompt = self._build_summary_system_prompt(summary_length, focus_areas)
            human_prompt = f"Summarize this lesson content:\n\n{lesson.content}"
            
            # Generate content
            result = self.generate_content(
                user=user,
                prompt=human_prompt,
                system_prompt=system_prompt,
                lesson_id=lesson_id
            )
            
            # Store generated content
            generated_content = GeneratedContent.objects.create(
                user=user,
                content_type='summary',
                source_lesson=lesson,
                source_text=lesson.content[:1000],
                generated_data={'summary': result['content']},
                prompt_used=f"{system_prompt}\n\n{human_prompt}",
                usage_log_id=result['usage_log_id'],
                status='auto_approved',
                validation_score=result['validation']['score']
            )
            
            final_result = {
                'summary': result['content'],
                'generated_content_id': generated_content.id,
                'tokens_used': result['tokens_used'],
                'cost_estimate': result['cost_estimate'],
                'provider': result['provider'],
                'model_used': result['model_used'],
                'validation': result['validation']
            }
            
            # Cache for 4 hours if validation score is good
            if result['validation']['score'] >= 70:
                cache.set(cache_key, final_result, 14400)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Summary generation failed for lesson {lesson_id}: {e}")
            AIUsageTracker.log_usage(
                user=user,
                service_type='lesson_summary',
                success=False,
                error_message=str(e),
                request_data={'lesson_id': lesson_id}
            )
            raise
    
    def _build_summary_system_prompt(self, length: str, focus_areas: List[str] = None) -> str:
        """Build enhanced system prompt for summarization"""
        length_guide = {
            'short': '2-3 sentences (50-100 words)',
            'medium': '1-2 paragraphs (150-300 words)',
            'long': '3-4 paragraphs (400-600 words)'
        }
        
        prompt = f"""You are an expert educational content summarizer. Create a {length} summary ({length_guide[length]}) of the provided lesson content.

REQUIREMENTS:
- Capture the main concepts, key points, and learning objectives
- Use clear, concise, and educational language
- Maintain factual accuracy and educational value
- Structure the summary logically with smooth transitions
- Ensure content is appropriate for educational use
- Include relevant examples or applications where helpful

QUALITY STANDARDS:
- Summary should be self-contained and understandable
- Key terminology should be clearly explained
- Important relationships between concepts should be highlighted
- Content should be engaging and informative"""
        
        if focus_areas:
            prompt += f"\n- Focus particularly on these areas: {', '.join(focus_areas)}"
        
        return prompt


class FlashcardService(EnhancedAIService):
    """Enhanced flashcard generation service"""
    
    def __init__(self):
        super().__init__('flashcard_generation')
    
    def generate_flashcards(self, user, lesson_id: int, num_cards: int = 10,
                          difficulty: str = 'medium') -> Dict:
        """Generate enhanced flashcards"""
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            
            # Check cache
            cache_key = f"flashcards_{lesson_id}_{num_cards}_{difficulty}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Prepare prompts
            system_prompt = self._build_flashcard_system_prompt(difficulty)
            human_prompt = f"Create {num_cards} flashcards from this lesson content:\n\n{lesson.content[:3000]}"
            
            # Generate content
            result = self.generate_content(
                user=user,
                prompt=human_prompt,
                system_prompt=system_prompt,
                lesson_id=lesson_id
            )
            
            # Parse flashcards
            flashcards_data = self._parse_flashcards_response(result['content'])
            
            # Store generated content
            generated_content = GeneratedContent.objects.create(
                user=user,
                content_type='flashcards',
                source_lesson=lesson,
                source_text=lesson.content[:1000],
                generated_data=flashcards_data,
                prompt_used=f"{system_prompt}\n\n{human_prompt}",
                usage_log_id=result['usage_log_id'],
                status='auto_approved',
                validation_score=result['validation']['score']
            )
            
            final_result = {
                'flashcards': flashcards_data,
                'generated_content_id': generated_content.id,
                'tokens_used': result['tokens_used'],
                'cost_estimate': result['cost_estimate'],
                'provider': result['provider'],
                'model_used': result['model_used'],
                'validation': result['validation']
            }
            
            # Cache for 4 hours if validation score is good
            if result['validation']['score'] >= 70:
                cache.set(cache_key, final_result, 14400)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Flashcard generation failed for lesson {lesson_id}: {e}")
            AIUsageTracker.log_usage(
                user=user,
                service_type='flashcard_generation',
                success=False,
                error_message=str(e),
                request_data={'lesson_id': lesson_id}
            )
            raise
    
    def _build_flashcard_system_prompt(self, difficulty: str) -> str:
        """Build enhanced system prompt for flashcard generation"""
        return f"""You are an expert educational content creator specializing in spaced repetition learning materials. Generate high-quality flashcards based on the provided lesson content.

REQUIREMENTS:
- Difficulty level: {difficulty}
- Create clear, concise question-answer pairs optimized for memorization and understanding
- Focus on key concepts, definitions, important facts, and relationships
- Questions should test both recall and comprehension
- Keep answers brief but complete and accurate
- Ensure educational appropriateness and factual accuracy
- Return response in valid JSON format only

QUALITY STANDARDS:
- Questions should be specific and unambiguous
- Answers should be concise but comprehensive
- Include a mix of factual recall and conceptual understanding
- Avoid overly complex or compound questions
- Use clear, accessible language

JSON STRUCTURE:
{{
    "flashcards": [
        {{
            "question": "Clear, specific question",
            "answer": "Concise, accurate answer",
            "category": "Topic/concept category",
            "difficulty": "{difficulty}",
            "type": "definition|concept|fact|application"
        }}
    ],
    "metadata": {{
        "total_cards": 10,
        "difficulty_level": "{difficulty}",
        "categories": ["list", "of", "categories"]
    }}
}}"""
    
    def _parse_flashcards_response(self, response_content: str) -> Dict:
        """Enhanced flashcards response parsing"""
        try:
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON found in response")
            
            json_str = response_content[start_idx:end_idx]
            flashcards_data = json.loads(json_str)
            
            if 'flashcards' not in flashcards_data:
                raise ValueError("Invalid flashcards format: missing 'flashcards' key")
            
            # Validate each flashcard
            for i, card in enumerate(flashcards_data['flashcards']):
                required_fields = ['question', 'answer']
                for field in required_fields:
                    if field not in card:
                        raise ValueError(f"Flashcard {i+1} missing required field: {field}")
            
            return flashcards_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse flashcards JSON: {e}")
            raise ValueError("Invalid JSON response from AI service")