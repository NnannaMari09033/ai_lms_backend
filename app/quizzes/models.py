from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Quiz(models.Model):
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="quizzes"
    )
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)  # None = unlimited
    max_attempts = models.PositiveIntegerField(default=1)
    allow_review_after_submit = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["course", "is_published"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.course}"


class Question(models.Model):
    MULTIPLE_CHOICE = "mcq"
    SHORT_TEXT = "text"
    QUESTION_TYPES = [
        (MULTIPLE_CHOICE, "Multiple choice"),
        (SHORT_TEXT, "Short answer"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default=MULTIPLE_CHOICE)
    order = models.PositiveIntegerField(default=0)
    points = models.FloatField(default=1.0)

    class Meta:
        ordering = ("order",)
        unique_together = ("quiz", "order")

    def __str__(self):
        return f"Q{self.order} ({self.quiz.title})"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Submission(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_submissions")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    finished = models.BooleanField(default=False)
    attempt_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["quiz", "student"]),
        ]

    def __str__(self):
        return f"Submission: {self.student} — {self.quiz} (attempt {self.attempt_number})"


class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    text_answer = models.TextField(blank=True, null=True)
    points_awarded = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("submission", "question")

    def __str__(self):
        return f"Answer: submission {self.submission_id} — q{self.question_id}"
