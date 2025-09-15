from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    email = models.EmailField(unique=True)

    # attach the custom manager
    objects = CustomUserManager()

    USERNAME_FIELD = "email"          # login with email instead of username
    REQUIRED_FIELDS = ["username"]    # still required when creating superuser

    def is_student(self):
        return self.role == 'student'

    def is_instructor(self):
        return self.role == 'instructor'

    def is_admin(self):
        return self.role == 'admin'


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    bio = models.TextField(blank=True, null=True)
    major = models.CharField(max_length=100, blank=True, null=True)
    enrolled_courses = models.ManyToManyField('courses.Course', blank=True, related_name='enrolled_students')
    date_of_birth = models.DateField(blank=True, null=True)
    grade_level = models.CharField(max_length=50, blank=True, null=True)
    interests = models.TextField(blank=True, null=True)
    email_address = models.EmailField(blank=True, null=True)


class InstructorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    bio = models.TextField(blank=True, null=True)
    expertise = models.CharField(max_length=255, blank=True, null=True)
    years_of_experience = models.IntegerField(blank=True, null=True)
    contact_info = models.EmailField(blank=True, null=True)
    office_hours = models.CharField(max_length=255, blank=True, null=True)
    email_address = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

