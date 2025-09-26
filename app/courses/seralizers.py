from rest_framework import serializers
from .models import Course, Lesson, Enrollment, LessonProgress, CourseReview


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "title", "content", "order", "course", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CourseSerializer(serializers.ModelSerializer):
    instructor = serializers.StringRelatedField(read_only=True)
    lessons = LessonSerializer(many=True, read_only=True)  # nested lessons

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "category",
            "difficulty_level",
            "instructor",
            "is_published",
            "created_at",
            "updated_at",
            "lessons",
        ]
        read_only_fields = ["id", "instructor", "created_at", "updated_at"]


class EnrollmentSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField(read_only=True)
    course = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "student", "course", "status", "enrolled_on"]
        read_only_fields = ["id", "student", "course", "enrolled_on"]


class LessonProgressSerializer(serializers.ModelSerializer):
    lesson = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = LessonProgress
        fields = ["id", "lesson", "is_completed", "completed_at"]
        read_only_fields = ["id", "lesson", "completed_at"]


class CourseReviewSerializer(serializers.ModelSerializer):
    enrollment = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CourseReview
        fields = ["id", "enrollment", "rating", "comment", "created_at"]
        read_only_fields = ["id", "enrollment", "created_at"]
