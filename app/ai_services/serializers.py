from rest_framework import serializers
from .models import AIUsageLog, GeneratedContent, AIUsageLimit, AIServiceConfig


class AIUsageLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIUsageLimit
        fields = ['id', 'role', 'monthly_limit', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AIUsageLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = AIUsageLog
        fields = [
            'id', 'user', 'user_email', 'service_type', 'tokens_used', 
            'cost_estimate', 'success', 'error_message', 'created_at',
            'course', 'lesson', 'quiz'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class GeneratedContentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    reviewed_by_email = serializers.CharField(source='reviewed_by.email', read_only=True)
    
    class Meta:
        model = GeneratedContent
        fields = [
            'id', 'user', 'user_email', 'content_type', 'status',
            'source_lesson', 'generated_data', 'reviewed_by', 'reviewed_by_email',
            'review_notes', 'reviewed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at'
        ]


class QuizGenerationRequestSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    num_questions = serializers.IntegerField(min_value=1, max_value=20, default=5)
    difficulty = serializers.ChoiceField(
        choices=['easy', 'medium', 'hard'], 
        default='medium'
    )
    question_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['multiple_choice', 'true_false', 'short_answer']),
        default=['multiple_choice']
    )


class SummarizationRequestSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    summary_length = serializers.ChoiceField(
        choices=['short', 'medium', 'long'], 
        default='medium'
    )
    focus_areas = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="Specific topics to focus on in the summary"
    )


class FlashcardGenerationRequestSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    num_cards = serializers.IntegerField(min_value=1, max_value=30, default=10)
    difficulty = serializers.ChoiceField(
        choices=['easy', 'medium', 'hard'], 
        default='medium'
    )


class ContentReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    notes = serializers.CharField(max_length=1000, required=False)


class AIServiceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIServiceConfig
        fields = ['id', 'service_name', 'is_enabled', 'config_data', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']