from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework.pagination import PageNumberPagination
from .models import Quiz, Submission
from .seralizers import (
    QuizListSerializer,
    QuizDetailSerializer,
    SubmissionCreateSerializer,
    SubmissionReadSerializer,
)
from .permissions import IsInstructorOrReadOnly, IsSubmissionOwnerOrInstructor
from app.courses.models import Enrollment

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.select_related("course").prefetch_related("questions__choices")
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsInstructorOrReadOnly]
    filterset_fields = ["course", "is_published"]
    search_fields = ["title", "description"]

    def get_serializer_class(self):
        if self.action == "list":
            return QuizListSerializer
        return QuizDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # instructors see their course quizzes
        if user.is_authenticated and getattr(user, "is_instructor", False):
            return qs.filter(course__instructor=user)
        # students/anonymous see published quizzes only
        return qs.filter(is_published=True)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def start(self, request, pk=None):
        """
        Optional: create a submission record with started_at so quiz timing can be tracked.
        """
        quiz = self.get_object()
        user = request.user
        if not Enrollment.objects.filter(user=user, course=quiz.course).exists():
            return response.Response({"detail": "You must be enrolled in the course to start this quiz."}, status=status.HTTP_403_FORBIDDEN)
        attempt_number = Submission.objects.filter(quiz=quiz, student=user).count() + 1
        if attempt_number > quiz.max_attempts:
            return response.Response({"detail": "Max attempts reached."}, status=status.HTTP_403_FORBIDDEN)
        submission = Submission.objects.create(quiz=quiz, student=user, attempt_number=attempt_number)
        return response.Response({"submission_id": submission.id, "started_at": submission.started_at}, status=status.HTTP_201_CREATED)


class SubmissionViewSet(viewsets.GenericViewSet, viewsets.mixins.CreateModelMixin, viewsets.mixins.ListModelMixin, viewsets.mixins.RetrieveModelMixin):
    queryset = Submission.objects.select_related("quiz", "student").prefetch_related("answers__question")
    permission_classes = [IsSubmissionOwnerOrInstructor]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "create":
            return SubmissionCreateSerializer
        return SubmissionReadSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_instructor", False):
            # instructors can list submissions for quizzes they own
            return self.queryset.filter(quiz__course__instructor=user)
        if user.is_authenticated:
            # students see their own submissions
            return self.queryset.filter(student=user)
        return Submission.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = SubmissionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        read_ser = SubmissionReadSerializer(submission, context={"request": request})
        return response.Response(read_ser.data, status=status.HTTP_201_CREATED)
