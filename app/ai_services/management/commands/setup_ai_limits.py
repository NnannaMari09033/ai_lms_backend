from django.core.management.base import BaseCommand
from django.conf import settings
from app.ai_services.models import AIUsageLimit, AIServiceConfig


class Command(BaseCommand):
    help = 'Setup default AI usage limits and service configurations'
    
    def handle(self, *args, **options):
        # Create default usage limits
        limits = [
            ('student', settings.AI_USAGE_LIMITS.get('student', 50)),
            ('instructor', settings.AI_USAGE_LIMITS.get('instructor', 200)),
            ('admin', settings.AI_USAGE_LIMITS.get('admin', 1000)),
        ]
        
        for role, limit in limits:
            obj, created = AIUsageLimit.objects.get_or_create(
                role=role,
                defaults={'monthly_limit': limit}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created usage limit for {role}: {limit} requests/month')
                )
            else:
                self.stdout.write(f'Usage limit for {role} already exists: {obj.monthly_limit} requests/month')
        
        # Create default service configurations
        services = [
            ('quiz_generation', {
                'model': 'gpt-3.5-turbo',
                'temperature': 0.7,
                'max_tokens': 2000,
            }),
            ('lesson_summary', {
                'model': 'gpt-3.5-turbo',
                'temperature': 0.3,
                'max_tokens': 1000,
            }),
            ('flashcard_generation', {
                'model': 'gpt-3.5-turbo',
                'temperature': 0.5,
                'max_tokens': 1500,
            }),
        ]
        
        for service_name, config in services:
            obj, created = AIServiceConfig.objects.get_or_create(
                service_name=service_name,
                defaults={
                    'is_enabled': True,
                    'config_data': config
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created service config for {service_name}')
                )
            else:
                self.stdout.write(f'Service config for {service_name} already exists')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully setup AI limits and service configurations')
        )