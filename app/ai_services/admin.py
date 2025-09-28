from django.contrib import admin
from .models import AIUsageLog, GeneratedContent, AIUsageLimit, AIServiceConfig


@admin.register(AIUsageLimit)
class AIUsageLimitAdmin(admin.ModelAdmin):
    list_display = ['role', 'monthly_limit', 'created_at', 'updated_at']
    list_filter = ['role']
    search_fields = ['role']


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'service_type', 'tokens_used', 'cost_estimate', 'success', 'created_at']
    list_filter = ['service_type', 'success', 'created_at', 'user__role']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'course', 'lesson', 'quiz')


@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_type', 'status', 'reviewed_by', 'created_at']
    list_filter = ['content_type', 'status', 'created_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    actions = ['approve_content', 'reject_content']
    
    def approve_content(self, request, queryset):
        for content in queryset:
            content.approve(reviewer=request.user)
        self.message_user(request, f"Approved {queryset.count()} content items.")
    approve_content.short_description = "Approve selected content"
    
    def reject_content(self, request, queryset):
        for content in queryset:
            content.reject(reviewer=request.user)
        self.message_user(request, f"Rejected {queryset.count()} content items.")
    reject_content.short_description = "Reject selected content"


@admin.register(AIServiceConfig)
class AIServiceConfigAdmin(admin.ModelAdmin):
    list_display = ['service_name', 'is_enabled', 'created_at', 'updated_at']
    list_filter = ['is_enabled']
    search_fields = ['service_name']
