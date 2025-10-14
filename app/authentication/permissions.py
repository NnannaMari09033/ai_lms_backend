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
        # NOTE: This __init__ is called when the permission is INSTANTIATED (by the factory function).
        self.roles = roles or []
        self.read_only = read_only
        self.owner_check = owner_check

    def has_permission(self, request, view):
        # Allow Django superusers full access at the view level
        if request.user and request.user.is_superuser:
            return True
            
        if not request.user or not request.user.is_authenticated:
            return False
            
        if self.read_only and request.method in SAFE_METHODS:
            return True
            
        return request.user.role in self.roles

    def has_object_permission(self, request, view, obj):
        # Allow Django superusers full access at the object level
        if request.user and request.user.is_superuser:
             return True
             
        if self.read_only and request.method in SAFE_METHODS:
            return True

        if self.owner_check and hasattr(obj, "user"):
            # Check if user is the owner OR has one of the allowed roles
            return obj.user == request.user or request.user.role in self.roles

        # Otherwise, check only for roles
        return request.user.role in self.roles


def IsAdmin():
    return RolePermission(roles=["admin"])
    
def IsInstructor():
    return RolePermission(roles=["instructor"])
    
def IsStudent():
    return RolePermission(roles=["student"])

def IsAdminOrInstructor():
    return RolePermission(roles=["admin", "instructor"])
    
def IsAdminOrStudent():
    return RolePermission(roles=["admin", "student"])
    
def IsInstructorOrStudent():
    return RolePermission(roles=["instructor", "student"])
    
def IsAdminOrInstructorOrStudent():
    return RolePermission(roles=["admin", "instructor", "student"])


# 2. Read-Only Role Checks
def IsAdminOrReadOnly():
    return RolePermission(roles=["admin"], read_only=True)
    
def IsInstructorOrReadOnly():
    return RolePermission(roles=["instructor"], read_only=True)
    
def IsStudentOrReadOnly():
    return RolePermission(roles=["student"], read_only=True)
    
def IsAdminOrInstructorOrReadOnly():
    return RolePermission(roles=["admin", "instructor"], read_only=True)
    
def IsAdminOrStudentOrReadOnly():
    return RolePermission(roles=["admin", "student"], read_only=True)
    
def IsInstructorOrStudentOrReadOnly():
    return RolePermission(roles=["instructor", "student"], read_only=True)
    
def IsAdminOrInstructorOrStudentOrReadOnly():
    return RolePermission(roles=["admin", "instructor", "student"], read_only=True)


# 3. Owner-Based Checks
def IsOwnerOrReadOnly():
    return RolePermission(read_only=True, owner_check=True)
    
def IsOwnerOrAdmin():
    return RolePermission(roles=["admin"], owner_check=True)
    
def IsOwnerOrInstructor():
    return RolePermission(roles=["instructor"], owner_check=True)
    
def IsOwnerOrStudent():
    return RolePermission(roles=["student"], owner_check=True)
    
def IsOwnerOrAdminOrInstructor():
    return RolePermission(roles=["admin", "instructor"], owner_check=True)
    
def IsOwnerOrAdminOrStudent():
    return RolePermission(roles=["admin", "student"], owner_check=True)
    
def IsOwnerOrInstructorOrStudent():
    return RolePermission(roles=["instructor", "student"], owner_check=True)
    
def IsOwnerOrAdminOrInstructorOrStudent():
    return RolePermission(roles=["admin", "instructor", "student"], owner_check=True)
              