from django.urls import path
from . import views # Imports all your ViewSets

urlpatterns = [
    # ----------------------------------------------------
    # 1. AIUsageLogViewSet (ReadOnlyModelViewSet)
    # ----------------------------------------------------
    path(
        'ai-logs/',
        views.AIUsageLogViewSet.as_view({'get': 'list'}),
        name='ai-usage-log-list'
    ),
    path(
        'ai-logs/<int:pk>/',
        views.AIUsageLogViewSet.as_view({'get': 'retrieve'}),
        name='ai-usage-log-detail'
    ),
    # Custom action: usage_stats
    path(
        'ai-logs/usage-stats/',
        views.AIUsageLogViewSet.as_view({'get': 'usage_stats'}),
        name='ai-usage-log-stats'
    ),

    # ----------------------------------------------------
    # 2. GeneratedContentViewSet (ModelViewSet)
    # ----------------------------------------------------
    path(
        'generated-content/',
        views.GeneratedContentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='generated-content-list'
    ),
    path(
        'generated-content/<int:pk>/',
        views.GeneratedContentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='generated-content-detail'
    ),
    # Custom action: review
    path(
        'generated-content/<int:pk>/review/',
        views.GeneratedContentViewSet.as_view({'post': 'review'}),
        name='generated-content-review'
    ),

    # ----------------------------------------------------
    # 3. Generation ViewSets (GenericViewSet - only custom actions)
    # ----------------------------------------------------
    # QuizGenerationViewSet - generate
    path(
        'quiz-generation/generate/',
        views.QuizGenerationViewSet.as_view({'post': 'generate'}),
        name='quiz-generation-generate'
    ),
    # SummarizationViewSet - generate
    path(
        'summarization/generate/',
        views.SummarizationViewSet.as_view({'post': 'generate'}),
        name='summarization-generate'
    ),
    # FlashcardViewSet - generate
    path(
        'flashcards/generate/',
        views.FlashcardViewSet.as_view({'post': 'generate'}),
        name='flashcards-generate'
    ),

    # ----------------------------------------------------
    # 4. AdminAIViewSet (GenericViewSet - only custom actions)
    # ----------------------------------------------------
    # AdminAIViewSet - usage_overview
    path(
        'admin-ai/usage-overview/',
        views.AdminAIViewSet.as_view({'get': 'usage_overview'}),
        name='admin-ai-usage-overview'
    ),
    # AdminAIViewSet - top_users
    path(
        'admin-ai/top-users/',
        views.AdminAIViewSet.as_view({'get': 'top_users'}),
        name='admin-ai-top-users'
    ),

    # ----------------------------------------------------
    # 5. AIServiceConfigViewSet & AIUsageLimitViewSet (ModelViewSet - Admin)
    # ----------------------------------------------------
    # AIServiceConfigViewSet
    path(
        'ai-config/',
        views.AIServiceConfigViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='ai-config-list'
    ),
    path(
        'ai-config/<int:pk>/',
        views.AIServiceConfigViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='ai-config-detail'
    ),
    # AIUsageLimitViewSet
    path(
        'ai-limits/',
        views.AIUsageLimitViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='ai-limits-list'
    ),
    path(
        'ai-limits/<int:pk>/',
        views.AIUsageLimitViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='ai-limits-detail'
    ),
]