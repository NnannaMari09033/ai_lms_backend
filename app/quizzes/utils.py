from django.db import transaction

def grade_submission(submission):
    """
    Simple synchronous grader:
      - MCQ: full points if selected_choice.is_correct else 0.
      - Text answers: left for manual grading (points_awarded=None).
    Returns total score (float).
    """
    total = 0.0
    with transaction.atomic():
        answers = submission.answers.select_related("question", "selected_choice").all()
        for a in answers:
            q = a.question
            if q.question_type == q.MULTIPLE_CHOICE:
                if a.selected_choice and a.selected_choice.is_correct:
                    a.points_awarded = q.points
                else:
                    a.points_awarded = 0.0
                a.save(update_fields=["points_awarded"])
                total += a.points_awarded
            else:
                # text questions: leave null (manual grading later)
                a.points_awarded = None
                a.save(update_fields=["points_awarded"])
    return total
