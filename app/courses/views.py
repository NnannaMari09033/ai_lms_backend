from rest_framework import viewsets, permissions, filters, status
from rest_framework.pagination import PageNumberPagination
from django.db.models import Avg
from .models import Course, Lesson, Enrollment, LessonProgress, CourseReview
from .seralizers import (
    CourseSerializer,
    LessonSerializer,
    EnrollmentSerializer,
    LessonProgressSerializer,
    CourseReviewSerializer,
)
from .permissions import IsInstructor, IsStudentOrReadOnly, IsOwnerOrReadOnly


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CourseViewSet(viewsets.ModelViewSet):
    """
    Courses — only instructors can create/update/delete their own courses.
    Students only see published courses.
    """

    serializer_class = CourseSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "category"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def get_queryset(self):
        qs = Course.objects.all().annotate(average_rating=Avg("enrollments__review__rating"))
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_instructor", False):
            # Instructors can see all their courses
            return qs.filter(instructor=user)
        # Students / anonymous see only published courses
        return qs.filter(is_published=True)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    def perform_update(self, serializer):
        # Ensure instructor owns the course
        course = self.get_object()
        if course.instructor != self.request.user:
            raise permissions.PermissionDenied("You can only update your own courses.")
        serializer.save()


class LessonViewSet(viewsets.ModelViewSet):
    """
    Lessons — instructors can manage lessons for their own courses.
    Students can only view lessons if enrolled.
    """

    serializer_class = LessonSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        course_id = self.request.query_params.get("course")
        qs = Lesson.objects.all()
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.instructor != self.request.user:
            raise permissions.PermissionDenied("You can only add lessons to your own courses.")
        serializer.save()

    def perform_update(self, serializer):
        lesson = self.get_object()
        if lesson.course.instructor != self.request.user:
            raise permissions.PermissionDenied("You can only update lessons in your own courses.")
        serializer.save()

    def retrieve(self, request, *args, **kwargs):
        lesson = self.get_object()
        # Students must be enrolled to view lessons
        if not getattr(request.user, "is_instructor", False):
            is_enrolled = Enrollment.objects.filter(student=request.user, course=lesson.course).exists()
            if not is_enrolled:
                raise permissions.PermissionDenied("You must be enrolled in this course to view lessons.")
        return super().retrieve(request, *args, **kwargs)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    Enrollments — students enroll in courses.
    """

    serializer_class = EnrollmentSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class LessonProgressViewSet(viewsets.ModelViewSet):
    """
    Track progress — students can only update their own progress.
    """

    serializer_class = LessonProgressSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return LessonProgress.objects.filter(enrollment__student=self.request.user)

    def perform_create(self, serializer):
        enrollment = serializer.validated_data["enrollment"]
        if enrollment.student != self.request.user:
            raise permissions.PermissionDenied("You can only track progress for your own enrollments.")
        serializer.save()


class CourseReviewViewSet(viewsets.ModelViewSet):
    """
    Course Reviews — students can review only courses they are enrolled in,
    and only once.
    """

    serializer_class = CourseReviewSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return CourseReview.objects.filter(enrollment__student=self.request.user)

    def perform_create(self, serializer):
        enrollment = serializer.validated_data["enrollment"]
        if enrollment.student != self.request.user:
            raise permissions.PermissionDenied("You can only review your own enrollments.")
        if enrollment.status != "completed":
            raise permissions.PermissionDenied("You can only review after completing the course.")
        if hasattr(enrollment, "review"):
            raise permissions.PermissionDenied("You have already reviewed this course.")
        serializer.save()

