# quizzes/urls.py
from django.urls import path
from .views import QuizViewSet, SubmissionViewSet

urlpatterns = [
  path("quiz/", QuizViewSet.as_view({"get": "list", "post": "create"}), name="quiz-list"),
  path("quiz/<int:pk>/", QuizViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="quiz-detail"),
  path("submission/", SubmissionViewSet.as_view({"get": "list", "post": "create"}), name="submission-list"),
  path("submission/<int:pk>/", SubmissionViewSet.as_view({"get": "retrieve"}), name="submission-detail"),
]
   
  

  
