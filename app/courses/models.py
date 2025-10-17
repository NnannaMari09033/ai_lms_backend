from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL  # Reuse your custom/auth app user


class Course(models.Model):
    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    difficulty_level = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="beginner"
    )
    instructor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="courses"
    )
    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=255)
    content = models.TextField()  # could hold text or embed links
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "order")  # avoid duplicate lesson order

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("dropped", "Dropped"),
    ]

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    enrolled_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")  # one enrollment per course
        ordering = ["-enrolled_on"]

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="progress"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="progress"
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("enrollment", "lesson")

    def __str__(self):
        return f"{self.enrollment.student} - {self.lesson.title} ({'done' if self.is_completed else 'in progress'})"


class CourseReview(models.Model):
    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="review"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        def __str__(self):
         return f"Review by {self.user} for {self.enrollment.course}"
