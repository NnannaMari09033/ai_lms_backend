from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta

from .models import AIUsageLog, GeneratedContent, AIUsageLimit, AIServiceConfig
from .serializers import (
    AIUsageLogSerializer, GeneratedContentSerializer, AIUsageLimitSerializer,
    QuizGenerationRequestSerializer, SummarizationRequestSerializer,
    FlashcardGenerationRequestSerializer, ContentReviewSerializer,
    AIServiceConfigSerializer
)
from .services import QuizGenerationService, SummarizationService, FlashcardService
from app.authentication.permissions import IsAdmin, IsInstructor
from app.courses.models import Lesson


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AIUsageLogViewSet(viewsets.ReadOnlyModelViewSet):
    """View AI usage logs - Admin can see all, users see their own"""
    serializer_class = AIUsageLogSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return AIUsageLog.objects.all().select_related('user', 'course', 'lesson', 'quiz')
        return AIUsageLog.objects.filter(user=user).select_related('course', 'lesson', 'quiz')
    
    @action(detail=False, methods=['get'])
    def usage_stats(self, request):
        """Get usage statistics for current user or all users (admin only)"""
        user = request.user
        queryset = self.get_queryset()
        
        # Current month stats
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_usage = queryset.filter(created_at__gte=current_month, success=True)
        
        stats = {
            'current_month': {
                'total_requests': current_month_usage.count(),
                'total_tokens': current_month_usage.aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0,
                'total_cost': float(current_month_usage.aggregate(Sum('cost_estimate'))['cost_estimate__sum'] or 0),
                'by_service': list(
                    current_month_usage.values('service_type')
                    .annotate(count=Count('id'), tokens=Sum('tokens_used'))
                    .order_by('-count')
                )
            }
        }
        
        # Add user limit info
        try:
            limit_obj = AIUsageLimit.objects.get(role=user.role)
            stats['monthly_limit'] = limit_obj.monthly_limit
        except AIUsageLimit.DoesNotExist:
            from django.conf import settings
            stats['monthly_limit'] = settings.AI_USAGE_LIMITS.get(user.role, 50)
        
        stats['remaining_requests'] = max(0, stats['monthly_limit'] - stats['current_month']['total_requests'])
        
        return Response(stats)


class GeneratedContentViewSet(viewsets.ModelViewSet):
    """Manage AI-generated content"""
    serializer_class = GeneratedContentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return GeneratedContent.objects.all().select_related('user', 'source_lesson', 'reviewed_by')
        elif user.role == 'instructor':
            # Instructors can see content from their courses + their own generated content
            return GeneratedContent.objects.filter(
                Q(user=user) | 
                Q(source_lesson__course__instructor=user)
            ).select_related('user', 'source_lesson', 'reviewed_by')
        else:
            # Students see only their own content
            return GeneratedContent.objects.filter(user=user).select_related('source_lesson', 'reviewed_by')
    
    @action(detail=True, methods=['post'], permission_classes=[IsInstructor])
    def review(self, request, pk=None):
        """Review generated content (approve/reject)"""
        content = self.get_object()
        serializer = ContentReviewSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        action_type = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        if action_type == 'approve':
            content.approve(reviewer=request.user, notes=notes)
        else:
            content.reject(reviewer=request.user, notes=notes)
        
        return Response(GeneratedContentSerializer(content).data)


class QuizGenerationViewSet(viewsets.GenericViewSet):
    """Generate quizzes from lesson content"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a quiz from lesson content"""
        serializer = QuizGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify lesson exists and user has access
            lesson = get_object_or_404(Lesson, id=serializer.validated_data['lesson_id'])
            
            # Check if user can access this lesson
            if request.user.role == 'student':
                from app.courses.models import Enrollment
                if not Enrollment.objects.filter(student=request.user, course=lesson.course).exists():
                    return Response(
                        {'detail': 'You must be enrolled in this course to generate quizzes.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif request.user.role == 'instructor':
                if lesson.course.instructor != request.user:
                    return Response(
                        {'detail': 'You can only generate quizzes for your own courses.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Generate quiz
            service = QuizGenerationService()
            result = service.generate_quiz(
                user=request.user,
                lesson_id=serializer.validated_data['lesson_id'],
                num_questions=serializer.validated_data['num_questions'],
                difficulty=serializer.validated_data['difficulty'],
                question_types=serializer.validated_data['question_types']
            )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'detail': 'Failed to generate quiz. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SummarizationViewSet(viewsets.GenericViewSet):
    """Generate lesson summaries"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a summary of lesson content"""
        serializer = SummarizationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify lesson access
            lesson = get_object_or_404(Lesson, id=serializer.validated_data['lesson_id'])
            
            if request.user.role == 'student':
                from app.courses.models import Enrollment
                if not Enrollment.objects.filter(student=request.user, course=lesson.course).exists():
                    return Response(
                        {'detail': 'You must be enrolled in this course to generate summaries.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif request.user.role == 'instructor':
                if lesson.course.instructor != request.user:
                    return Response(
                        {'detail': 'You can only generate summaries for your own courses.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Generate summary
            service = SummarizationService()
            result = service.generate_summary(
                user=request.user,
                lesson_id=serializer.validated_data['lesson_id'],
                summary_length=serializer.validated_data['summary_length'],
                focus_areas=serializer.validated_data.get('focus_areas')
            )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'detail': 'Failed to generate summary. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FlashcardViewSet(viewsets.GenericViewSet):
    """Generate flashcards from lesson content"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate flashcards from lesson content"""
        serializer = FlashcardGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify lesson access
            lesson = get_object_or_404(Lesson, id=serializer.validated_data['lesson_id'])
            
            if request.user.role == 'student':
                from app.courses.models import Enrollment
                if not Enrollment.objects.filter(student=request.user, course=lesson.course).exists():
                    return Response(
                        {'detail': 'You must be enrolled in this course to generate flashcards.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif request.user.role == 'instructor':
                if lesson.course.instructor != request.user:
                    return Response(
                        {'detail': 'You can only generate flashcards for your own courses.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Generate flashcards
            service = FlashcardService()
            result = service.generate_flashcards(
                user=request.user,
                lesson_id=serializer.validated_data['lesson_id'],
                num_cards=serializer.validated_data['num_cards'],
                difficulty=serializer.validated_data['difficulty']
            )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'detail': 'Failed to generate flashcards. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminAIViewSet(viewsets.GenericViewSet):
    """Admin endpoints for AI service management"""
    permission_classes = [IsAdmin]
    
    @action(detail=False, methods=['get'])
    def usage_overview(self, request):
        """Get system-wide AI usage overview"""
        # Current month stats
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        current_usage = AIUsageLog.objects.filter(created_at__gte=current_month, success=True)
        last_month_usage = AIUsageLog.objects.filter(
            created_at__gte=last_month, 
            created_at__lt=current_month, 
            success=True
        )
        
        stats = {
            'current_month': {
                'total_requests': current_usage.count(),
                'total_tokens': current_usage.aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0,
                'total_cost': float(current_usage.aggregate(Sum('cost_estimate'))['cost_estimate__sum'] or 0),
                'unique_users': current_usage.values('user').distinct().count(),
                'by_service': list(
                    current_usage.values('service_type')
                    .annotate(count=Count('id'), tokens=Sum('tokens_used'))
                    .order_by('-count')
                ),
                'by_role': list(
                    current_usage.values('user__role')
                    .annotate(count=Count('id'), tokens=Sum('tokens_used'))
                    .order_by('-count')
                )
            },
            'last_month': {
                'total_requests': last_month_usage.count(),
                'total_tokens': last_month_usage.aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0,
                'total_cost': float(last_month_usage.aggregate(Sum('cost_estimate'))['cost_estimate__sum'] or 0),
            }
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def top_users(self, request):
        """Get top AI users by usage"""
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        top_users = (
            AIUsageLog.objects.filter(created_at__gte=current_month, success=True)
            .values('user__email', 'user__role')
            .annotate(
                total_requests=Count('id'),
                total_tokens=Sum('tokens_used'),
                total_cost=Sum('cost_estimate')
            )
            .order_by('-total_requests')[:20]
        )
        
        return Response(list(top_users))


class AIServiceConfigViewSet(viewsets.ModelViewSet):
    """Manage AI service configurations"""
    queryset = AIServiceConfig.objects.all()
    serializer_class = AIServiceConfigSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination


class AIUsageLimitViewSet(viewsets.ModelViewSet):
    """Manage AI usage limits per role"""
    queryset = AIUsageLimit.objects.all()
    serializer_class = AIUsageLimitSerializer
    permission_classes = [IsAdmin]