import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model, authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle, AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView


from .seralizers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    StudentProfileSerializer,
    InstructorProfileSerializer,
    ChangePasswordSerializer,
    ResetPasswordEmailRequestSerializer,
    SetNewPasswordSerializer,
)
from .models import StudentProfile, InstructorProfile
from . import permissions as perms

User = get_user_model()
logger = logging.getLogger(__name__)


def _get_user_or_404_by_pk(pk):
    return get_object_or_404(User, pk=pk)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle, AnonRateThrottle])
def register_view(request):
    """Register a new user.

    Rate-limited (scoped as 'auth') to prevent abuse (signup storms).
    Creates role-specific profile automatically.
    """
    # assign throttle scope on the view function for ScopedRateThrottle
    register_view.throttle_scope = 'auth'

    logger.info("Register attempt: ip=%s email=%s", request.META.get('REMOTE_ADDR'), request.data.get('email'))
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning("Register failed validation: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = serializer.save()
        logger.info("User created: id=%s email=%s", user.pk, user.email)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    except Exception as exc:
        logger.exception("Error creating user: %s", exc)
        return Response({'detail': 'Unable to create user'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle, AnonRateThrottle])
def login_view(request):
    """Login with email + password. Returns JWT tokens and user data.

    Rate-limited (scoped as 'auth') to reduce brute force attempts.
    """
    login_view.throttle_scope = 'auth'

    logger.info("Login attempt: ip=%s email=%s", request.META.get('REMOTE_ADDR'), request.data.get('email'))
    serializer = LoginSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        logger.warning("Login failed: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    # Login serializer validated credentials and added access/refresh tokens to validated_data
    tokens = {
        'access': serializer.validated_data.get('access'),
        'refresh': serializer.validated_data.get('refresh'),
    }

    # fetch user instance to include user payload
    try:
        # serializer validated the credentials so fetching by email is safe
        user = User.objects.get(email=request.data.get('email'))
    except User.DoesNotExist:
        logger.error("Auth succeeded but user not found: %s", request.data.get('email'))
        return Response({'detail': 'Authentication error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    payload = {
        'user': UserSerializer(user).data,
        'tokens': tokens,
    }
    logger.info("Login success: user_id=%s", user.pk)
    return Response(payload, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Return current authenticated user."""
    logger.debug("Me request for user_id=%s", request.user.pk)
    return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    logger.info("Password changed for user_id=%s", request.user.pk)
    return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle, AnonRateThrottle])
def reset_password_request_view(request):
    reset_password_request_view.throttle_scope = 'auth'
    serializer = ResetPasswordEmailRequestSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    logger.info("Password reset requested for email=%s", request.data.get('email'))
    return Response({'detail': 'Password reset email sent.'}, status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([AllowAny])
def set_new_password_view(request):
    serializer = SetNewPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    logger.info("Password reset completed for user_id=%s", serializer.validated_data.get('user').pk)
    return Response({'detail': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([perms.IsAdmin])
def user_list_view(request):
    """Admin-only: list all users."""
    users = User.objects.all().order_by('-date_joined')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def user_detail_view(request, pk):
    """Retrieve / update / delete user. Owner or admin may update/delete; others denied."""
    target = _get_user_or_404_by_pk(pk)

    # permission check: owner or admin
    if not (request.user == target or request.user.role == 'admin'):
        return Response({'detail': 'Not permitted.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(UserSerializer(target).data)

    if request.method in ('PUT', 'PATCH'):
        partial = request.method == 'PATCH'
        data = request.data.copy()
        # disallow changing sensitive fields through this endpoint
        data.pop('password', None)
        data.pop('is_superuser', None)
        data.pop('is_staff', None)
        serializer = UserSerializer(target, data=data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        logger.info("User updated: target_id=%s by=%s", target.pk, request.user.pk)
        return Response(serializer.data)

    if request.method == 'DELETE':
        # admin can delete anyone; owner can delete themselves
        target.delete()
        logger.info("User deleted: target_id=%s by=%s", pk, request.user.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def student_profile_view(request):
    """Get or update the authenticated user's student profile. Admins can access any student's profile by providing ?user_id=.
    """
    user_id = request.query_params.get('user_id')
    if user_id and request.user.role != 'admin':
        return Response({'detail': 'Not permitted.'}, status=status.HTTP_403_FORBIDDEN)

    if user_id:
        user = _get_user_or_404_by_pk(user_id)
        profile = get_object_or_404(StudentProfile, user=user)
    else:
        profile = get_object_or_404(StudentProfile, user=request.user)

    if request.method == 'GET':
        return Response(StudentProfileSerializer(profile).data)

    # update
    if not (profile.user == request.user or request.user.role == 'admin'):
        return Response({'detail': 'Not permitted.'}, status=status.HTTP_403_FORBIDDEN)

    partial = request.method == 'PATCH'
    serializer = StudentProfileSerializer(profile, data=request.data, partial=partial, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    logger.info("Student profile updated: user_id=%s by=%s", profile.user.pk, request.user.pk)
    return Response(serializer.data)


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def instructor_profile_view(request):
    """Get or update the authenticated user's instructor profile. Admins can access any instructor's profile by providing ?user_id=.
    """
    user_id = request.query_params.get('user_id')
    if user_id and request.user.role != 'admin':
        return Response({'detail': 'Not permitted.'}, status=status.HTTP_403_FORBIDDEN)

    if user_id:
        user = _get_user_or_404_by_pk(user_id)
        profile = get_object_or_404(InstructorProfile, user=user)
    else:
        profile = get_object_or_404(InstructorProfile, user=request.user)

    if request.method == 'GET':
        return Response(InstructorProfileSerializer(profile).data)

    # update
    if not (profile.user == request.user or request.user.role == 'admin'):
        return Response({'detail': 'Not permitted.'}, status=status.HTTP_403_FORBIDDEN)

    partial = request.method == 'PATCH'
    serializer = InstructorProfileSerializer(profile, data=request.data, partial=partial, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    logger.info("Instructor profile updated: user_id=%s by=%s", profile.user.pk, request.user.pk)
    return Response(serializer.data)


