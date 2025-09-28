# Generated migration for AI services models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '0001_initial'),
        ('quizzes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AIUsageLimit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Student'), ('instructor', 'Instructor'), ('admin', 'Admin')], max_length=20, unique=True)),
                ('monthly_limit', models.PositiveIntegerField(help_text='Maximum AI requests per month for this role')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['role'],
            },
        ),
        migrations.CreateModel(
            name='AIServiceConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(max_length=50, unique=True)),
                ('is_enabled', models.BooleanField(default=True)),
                ('config_data', models.JSONField(default=dict, help_text='Service-specific configuration (temperature, max_tokens, etc.)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['service_name'],
            },
        ),
        migrations.CreateModel(
            name='AIUsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_type', models.CharField(choices=[('quiz_generation', 'Quiz Generation'), ('lesson_summary', 'Lesson Summary'), ('flashcard_generation', 'Flashcard Generation')], max_length=30)),
                ('tokens_used', models.PositiveIntegerField(default=0)),
                ('cost_estimate', models.DecimalField(decimal_places=6, default=0.0, max_digits=10)),
                ('request_data', models.TextField(help_text='Encrypted request parameters')),
                ('response_data', models.TextField(help_text='Encrypted response data')),
                ('success', models.BooleanField(default=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('provider', models.CharField(default='openai', help_text='AI provider used', max_length=50)),
                ('model_used', models.CharField(blank=True, help_text='Specific model used', max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.course')),
                ('lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.lesson')),
                ('quiz', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='quizzes.quiz')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_usage_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GeneratedContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', models.CharField(choices=[('quiz', 'Quiz'), ('summary', 'Summary'), ('flashcards', 'Flashcards')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('auto_approved', 'Auto Approved')], default='pending', max_length=20)),
                ('source_text', models.TextField(help_text='Original text used for generation')),
                ('generated_data', models.JSONField(help_text='AI-generated content')),
                ('prompt_used', models.TextField(help_text='Prompt sent to AI service')),
                ('review_notes', models.TextField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('usage_log_id', models.PositiveIntegerField(help_text='Reference to usage log')),
                ('validation_score', models.PositiveIntegerField(default=0, help_text='Content validation score (0-100)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_content', to=settings.AUTH_USER_MODEL)),
                ('source_lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.lesson')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='generated_content', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='aiusagelog',
            index=models.Index(fields=['user', 'service_type', 'created_at'], name='ai_services_user_service_created_idx'),
        ),
        migrations.AddIndex(
            model_name='aiusagelog',
            index=models.Index(fields=['created_at'], name='ai_services_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='generatedcontent',
            index=models.Index(fields=['content_type', 'status'], name='ai_services_content_type_status_idx'),
        ),
        migrations.AddIndex(
            model_name='generatedcontent',
            index=models.Index(fields=['user', 'created_at'], name='ai_services_user_created_idx'),
        ),
    ]