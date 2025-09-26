# courses/permissions.py
from rest_framework import permissions


class IsInstructor(permissions.BasePermission):
    """
    Allows only instructors to create, edit, or delete courses.
    """
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and getattr(request.user, "is_instructor", False)
        )


class IsStudentOrReadOnly(permissions.BasePermission):
    """
    Students can interact with ratings and progress;
    everyone else has read-only access.
    """
    def has_permission(self, request, view):
        # Safe methods = GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user 
            and request.user.is_authenticated 
            and not getattr(request.user, "is_instructor", False)
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Ensure only the owner of an object (like a rating or progress record)
    can update or delete it. Others have read-only access.
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or getattr(obj, "user", None) == request.user
        )
