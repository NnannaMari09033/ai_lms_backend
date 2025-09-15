from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth import get_user_model

User = get_user_model()


class RolePermission(BasePermission):
    """
    Generic role-based permission checker.
    - roles: list of roles allowed (e.g. ['admin', 'instructor'])
    - read_only: if True, safe methods (GET, HEAD, OPTIONS) are always allowed
    - owner_check: if True, only owner of the object OR allowed roles can edit
    """

    def __init__(self, roles=None, read_only=False, owner_check=False):
        self.roles = roles or []
        self.read_only = read_only
        self.owner_check = owner_check

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if self.read_only and request.method in SAFE_METHODS:
            return True
        return request.user.role in self.roles

    def has_object_permission(self, request, view, obj):
        if self.read_only and request.method in SAFE_METHODS:
            return True

        if self.owner_check and hasattr(obj, "user"):
            return obj.user == request.user or request.user.role in self.roles

        return request.user.role in self.roles


# --- Common Role-Based Permissions --- #
IsAdmin = RolePermission(roles=["admin"])
IsInstructor = RolePermission(roles=["instructor"])
IsStudent = RolePermission(roles=["student"])

IsAdminOrInstructor = RolePermission(roles=["admin", "instructor"])
IsAdminOrStudent = RolePermission(roles=["admin", "student"])
IsInstructorOrStudent = RolePermission(roles=["instructor", "student"])
IsAdminOrInstructorOrStudent = RolePermission(roles=["admin", "instructor", "student"])

# --- Read-Only Variants --- #
IsAdminOrReadOnly = RolePermission(roles=["admin"], read_only=True)
IsInstructorOrReadOnly = RolePermission(roles=["instructor"], read_only=True)
IsStudentOrReadOnly = RolePermission(roles=["student"], read_only=True)
IsAdminOrInstructorOrReadOnly = RolePermission(roles=["admin", "instructor"], read_only=True)
IsAdminOrStudentOrReadOnly = RolePermission(roles=["admin", "student"], read_only=True)
IsInstructorOrStudentOrReadOnly = RolePermission(roles=["instructor", "student"], read_only=True)
IsAdminOrInstructorOrStudentOrReadOnly = RolePermission(roles=["admin", "instructor", "student"], read_only=True)

# --- Owner-Based Variants --- #
IsOwnerOrReadOnly = RolePermission(read_only=True, owner_check=True)
IsOwnerOrAdmin = RolePermission(roles=["admin"], owner_check=True)
IsOwnerOrInstructor = RolePermission(roles=["instructor"], owner_check=True)
IsOwnerOrStudent = RolePermission(roles=["student"], owner_check=True)
IsOwnerOrAdminOrInstructor = RolePermission(roles=["admin", "instructor"], owner_check=True)
IsOwnerOrAdminOrStudent = RolePermission(roles=["admin", "student"], owner_check=True)
IsOwnerOrInstructorOrStudent = RolePermission(roles=["instructor", "student"], owner_check=True)
IsOwnerOrAdminOrInstructorOrStudent = RolePermission(
    roles=["admin", "instructor", "student"], owner_check=True
)

  
              