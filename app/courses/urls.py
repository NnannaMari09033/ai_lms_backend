from django.urls import path
from .views import (
    CourseViewSet, EnrollmentViewSet, LessonProgressViewSet,
    CourseReviewViewSet
)

urlpatterns = [

    path("courses/", CourseViewSet.as_view({"get": "list", "post": "create"}), name="course-list"),
    path("courses/<int:pk>/", CourseViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="course-detail"),
    path("enrollments/", EnrollmentViewSet.as_view({"get": "list", "post": "create"}), name="enrollment-list"),
    path("enrollments/<int:pk>/", EnrollmentViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="enrollment-detail"),
    path("lessons/", LessonProgressViewSet.as_view({"get": "list", "post": "create"}), name="lessonprogress-list"),
    path("lessons/<int:pk>/", LessonProgressViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="lessonprogress-detail"),
    path("reviews/", CourseReviewViewSet.as_view({"get": "list", "post": "create"}), name="review-list"),
    path("reviews/<int:pk>/", CourseReviewViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="review-detail"),


]
