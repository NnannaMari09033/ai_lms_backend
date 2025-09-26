from django.contrib import admin

# Register your models here.
from .models import Quiz, Question, Choice, Answer, Submission
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Choice)
admin.site .register(Answer)
admin.site.register(Submission)
