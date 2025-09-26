from rest_framework import serializers
from django.utils import timezone
from .models import Quiz, Question, Choice, Submission, Answer
from app.courses.models import Enrollment


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]  


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "question_type", "order", "points", "choices"]


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "question_count", "is_published", "time_limit_minutes"]


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "is_published",
            "time_limit_minutes",
            "max_attempts",
            "allow_review_after_submit",
            "questions",
        ]


# --- WRITE serializers for submissions ---
class AnswerCreateSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    selected_choice = serializers.PrimaryKeyRelatedField(queryset=Choice.objects.all(), required=False, allow_null=True)
    text_answer = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Answer
        fields = ["question", "selected_choice", "text_answer"]

    def validate(self, data):
        q = data["question"]
        sel = data.get("selected_choice")
        # If question is MCQ, selected_choice must be provided and belong to the question
        if q.question_type == Question.MULTIPLE_CHOICE:
            if not sel:
                raise serializers.ValidationError("selected_choice is required for multiple-choice questions.")
            if sel.question_id != q.id:
                raise serializers.ValidationError("selected_choice must belong to the referenced question.")
        else:
            # For text questions, selected_choice should not be provided
            if sel:
                raise serializers.ValidationError("selected_choice not allowed for text questions.")
        return data


class SubmissionCreateSerializer(serializers.ModelSerializer):
    answers = AnswerCreateSerializer(many=True)
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.filter(is_published=True))

    class Meta:
        model = Submission
        fields = ["quiz", "answers"]

    def validate(self, data):
        user = self.context["request"].user
        quiz = data["quiz"]

        # Must be enrolled in the parent course
        if not Enrollment.objects.filter(user=user, course=quiz.course).exists():
            raise serializers.ValidationError("You must be enrolled in the course to take this quiz.")

        # Attempt limits
        attempts = Submission.objects.filter(quiz=quiz, student=user).count()
        if attempts >= quiz.max_attempts:
            raise serializers.ValidationError("Maximum attempts reached for this quiz.")

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        answers_data = validated_data.pop("answers")
        quiz = validated_data["quiz"]
        attempt_number = Submission.objects.filter(quiz=quiz, student=user).count() + 1

        submission = Submission.objects.create(
            quiz=quiz,
            student=user,
            attempt_number=attempt_number,
            started_at=timezone.now(),
        )

        # Create answers
        for a in answers_data:
            Answer.objects.create(
                submission=submission,
                question=a["question"],
                selected_choice=a.get("selected_choice"),
                text_answer=a.get("text_answer"),
            )

        # Grade MCQs synchronously for V1
        from .utils import grade_submission
        score = grade_submission(submission)

        submission.score = score
        submission.submitted_at = timezone.now()
        submission.finished = True
        submission.save(update_fields=["score", "submitted_at", "finished"])

        return submission


class AnswerReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["question", "selected_choice", "text_answer", "points_awarded"]


class SubmissionReadSerializer(serializers.ModelSerializer):
    answers = AnswerReadSerializer(many=True, read_only=True)
    quiz_title = serializers.ReadOnlyField(source="quiz.title")
    student_username = serializers.ReadOnlyField(source="student.username")

    class Meta:
        model = Submission
        fields = [
            "id",
            "quiz",
            "quiz_title",
            "student",
            "student_username",
            "started_at",
            "submitted_at",
            "score",
            "finished",
            "attempt_number",
            "answers",
        ]
        read_only_fields = fields
