from rest_framework import permissions

class IsInstructorOrReadOnly(permissions.BasePermission):
    """
    Allow safe methods for all; only course instructors may create/edit quizzes for their course.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and getattr(request.user, "is_instructor", False)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # obj likely has course attribute (Quiz) or quiz attribute (Question)
        course = getattr(obj, "course", None) or getattr(getattr(obj, "quiz", None), "course", None)
        return course and course.instructor == request.user


class IsSubmissionOwnerOrInstructor(permissions.BasePermission):
    """
    Submissions may be viewed by their owner or the course instructor. Creation allowed for enrolled students (serializer checks).
    """
    def has_permission(self, request, view):
        # allow create for authenticated users; detailed create validation happens in serializer
        if view.action == "create":
            return request.user and request.user.is_authenticated
        return True

    def has_object_permission(self, request, view, obj):
        # obj is Submission
        if request.method in permissions.SAFE_METHODS:
            return obj.student == request.user or obj.quiz.course.instructor == request.user
        return obj.student == request.user
