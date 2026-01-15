"""Authentication views."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.contrib.auth.models import User


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login endpoint. POST /api/auth/login/"""
    try:
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return JsonResponse({
                'success': False,
                'error': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Django User model uses username, but we'll accept email
        # Try to find user by email (if you have email field) or username
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Try username as fallback
            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)

        # Authenticate user
        user = authenticate(request, username=user.username, password=password)
        if user is None:
            return JsonResponse({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Login user (creates session)
        login(request, user)

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email or user.username,
                'name': user.get_full_name() or user.username,
                'role': 'admin' if user.is_staff else 'user'
            }
        }, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        from django.conf import settings
        DEBUG = getattr(settings, 'DEBUG', False)
        error_msg = str(e)
        if DEBUG:
            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current user endpoint. GET /api/auth/me/"""
    try:
        user = request.user
        return JsonResponse({
            'id': user.id,
            'email': user.email or user.username,
            'name': user.get_full_name() or user.username,
            'role': 'admin' if user.is_staff else 'user'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        from django.conf import settings
        DEBUG = getattr(settings, 'DEBUG', False)
        error_msg = str(e)
        if DEBUG:
            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint. POST /api/auth/logout/"""
    try:
        logout(request)
        return JsonResponse({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        from django.conf import settings
        DEBUG = getattr(settings, 'DEBUG', False)
        error_msg = str(e)
        if DEBUG:
            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
