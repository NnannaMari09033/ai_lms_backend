from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = settings.AUTH_USER_MODEL


class AIUsageLimit(models.Model):
    """Define AI usage limits per user role"""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    monthly_limit = models.PositiveIntegerField(
        help_text="Maximum AI requests per month for this role"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['role']
    
    def __str__(self):
        return f"{self.role.title()} - {self.monthly_limit} requests/month"


class AIUsageLog(models.Model):
    """Enhanced AI API usage tracking"""
    SERVICE_CHOICES = [
        ('quiz_generation', 'Quiz Generation'),
        ('lesson_summary', 'Lesson Summary'),
        ('flashcard_generation', 'Flashcard Generation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_usage_logs')
    service_type = models.CharField(max_length=30, choices=SERVICE_CHOICES)
    tokens_used = models.PositiveIntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    request_data = models.TextField(help_text="Encrypted request parameters")
    response_data = models.TextField(help_text="Encrypted response data")
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    provider = models.CharField(max_length=50, default='openai', help_text="AI provider used")
    model_used = models.CharField(max_length=100, blank=True, null=True, help_text="Specific model used")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Related content
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey('quizzes.Quiz', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'service_type', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.service_type} - {self.created_at.date()}"


class GeneratedContent(models.Model):
    """Store AI-generated content for caching and review"""
    CONTENT_TYPES = [
        ('quiz', 'Quiz'),
        ('summary', 'Summary'),
        ('flashcards', 'Flashcards'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('auto_approved', 'Auto Approved'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_content')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Source content
    source_lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE, null=True, blank=True)
    source_text = models.TextField(help_text="Original text used for generation")
    
    # Generated content
    generated_data = models.JSONField(help_text="AI-generated content")
    prompt_used = models.TextField(help_text="Prompt sent to AI service")
    
    # Review information
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='reviewed_content'
    )
    review_notes = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    usage_log_id = models.PositiveIntegerField(help_text="Reference to usage log")
    validation_score = models.PositiveIntegerField(default=0, help_text="Content validation score (0-100)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.content_type.title()} - {self.user} - {self.status}"
    
    def approve(self, reviewer=None, notes=None):
        """Approve the generated content"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()
    
    def reject(self, reviewer=None, notes=None):
        """Reject the generated content"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()


class AIServiceConfig(models.Model):
    """Configuration settings for AI services"""
    service_name = models.CharField(max_length=50, unique=True)
    is_enabled = models.BooleanField(default=True)
    config_data = models.JSONField(
        default=dict,
        help_text="Service-specific configuration (temperature, max_tokens, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['service_name']
    
    def __str__(self):
        return f"{self.service_name} ({'Enabled' if self.is_enabled else 'Disabled'})"