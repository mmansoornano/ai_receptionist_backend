"""Authentication views."""
import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken


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

        # Login user (creates session for web clients)
        login(request, user)

        # Generate JWT tokens (for API/mobile clients)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Build user response with admin flags
        user_response = {
            'id': user.id,
            'email': user.email or user.username,
            'name': user.get_full_name() or user.username,
            'role': 'admin' if user.is_staff else 'user',
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser
        }
        
        # Check if user has is_admin attribute (custom field)
        if hasattr(user, 'is_admin'):
            user_response['is_admin'] = user.is_admin

        return JsonResponse({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_response
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
        
        # Build user response with admin flags
        user_response = {
            'id': user.id,
            'email': user.email or user.username,
            'name': user.get_full_name() or user.username,
            'role': 'admin' if user.is_staff else 'user',
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser
        }
        
        # Check if user has is_admin attribute (custom field)
        if hasattr(user, 'is_admin'):
            user_response['is_admin'] = user.is_admin
        
        return JsonResponse(user_response, status=status.HTTP_200_OK)
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


@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    """Signup endpoint. POST /api/auth/signup/"""
    try:
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        phone = request.data.get('phone', '').strip()

        # Validation errors dictionary
        errors = {}

        # Validate required fields
        if not name:
            errors['name'] = ['This field is required']
        elif len(name) > 255:
            errors['name'] = ['Name must be at most 255 characters']

        if not email:
            errors['email'] = ['This field is required']
        else:
            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = ['Enter a valid email address.']
            else:
                # Check email uniqueness
                if User.objects.filter(email=email).exists():
                    errors['email'] = ['This email is already registered']
                # Also check username uniqueness (we use email as username)
                if User.objects.filter(username=email).exists():
                    errors['email'] = ['This email is already registered']

        if not password:
            errors['password'] = ['This field is required']
        elif len(password) < 6:
            errors['password'] = ['Password must be at least 6 characters']

        # Return validation errors if any
        if errors:
            return JsonResponse({
                'error': 'Validation failed' if any(errors.values()) else 'Missing required fields',
                'details': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        try:
            # Split name into first and last name
            name_parts = name.split()
            first_name = name_parts[0] if name_parts else name
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            # Create user with email as username
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,  # Django's create_user automatically hashes the password
                first_name=first_name,
                last_name=last_name
            )

            # Create customer record if Customer model exists
            try:
                from apps.core.models import Customer
                # Get or create customer linked to user
                customer, created = Customer.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': name,
                        'email': email,
                        'phone': phone or f'user_{user.id}'
                    }
                )
                # Update existing customer if needed
                if not created:
                    updated = False
                    if customer.name != name:
                        customer.name = name
                        updated = True
                    if customer.email != email:
                        customer.email = email
                        updated = True
                    if phone and customer.phone != phone:
                        customer.phone = phone
                        updated = True
                    if updated:
                        customer.save()
            except ImportError:
                # Customer model might not exist, that's okay
                pass
            except Exception as e:
                # If customer creation fails, log but don't fail signup
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to create customer record for user {user.id}: {str(e)}")

            # Auto-login the user after signup (creates session for web clients)
            login(request, user)

            # Generate JWT tokens (for API/mobile clients)
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Build user response with admin flags
            user_response = {
                'id': user.id,
                'email': user.email,
                'name': name,
                'phone': phone if phone else '',
                'role': 'admin' if user.is_staff else 'user',
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            }
            
            # Check if user has is_admin attribute (custom field)
            if hasattr(user, 'is_admin'):
                user_response['is_admin'] = user.is_admin

            # Return success response with both session and tokens
            return JsonResponse({
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user_response
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'error': 'Internal server error',
                'message': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        import traceback
        from django.conf import settings
        DEBUG = getattr(settings, 'DEBUG', False)
        error_msg = str(e)
        if DEBUG:
            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        return JsonResponse({
            'error': 'Internal server error',
            'message': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _is_backend_request(request):
    """Check if request is coming from backend/localhost only."""
    # Get client IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    
    # Check if IP is localhost
    localhost_ips = ['127.0.0.1', '::1', 'localhost']
    is_localhost = ip in localhost_ips or ip.startswith('127.') or ip.startswith('::1')
    
    # Optionally check for secret token from environment
    secret_token = os.getenv('SUPERUSER_CREATE_TOKEN')
    if secret_token:
        provided_token = request.headers.get('X-Superuser-Token', '')
        if provided_token != secret_token:
            return False
    
    return is_localhost


@api_view(['POST'])
@permission_classes([AllowAny])
def create_superuser(request):
    """Create superuser endpoint - backend only. POST /api/auth/create-superuser/
    
    This endpoint is only accessible from localhost/backend.
    Optionally requires X-Superuser-Token header if SUPERUSER_CREATE_TOKEN is set in .env.
    
    Request body:
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "secure_password",
        "first_name": "Admin",
        "last_name": "User"
    }
    """
    try:
        # Check if request is from backend/localhost
        if not _is_backend_request(request):
            return JsonResponse({
                'success': False,
                'error': 'Access denied. This endpoint is only accessible from the backend.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get request data
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        first_name = request.data.get('first_name', '').strip()
        last_name = request.data.get('last_name', '').strip()
        
        # Validation errors dictionary
        errors = {}
        
        # Validate required fields
        if not username:
            errors['username'] = ['This field is required']
        elif len(username) < 3:
            errors['username'] = ['Username must be at least 3 characters']
        elif User.objects.filter(username=username).exists():
            errors['username'] = ['Username already exists']
        
        if not email:
            errors['email'] = ['This field is required']
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = ['Enter a valid email address.']
            else:
                if User.objects.filter(email=email).exists():
                    errors['email'] = ['This email is already registered']
        
        if not password:
            errors['password'] = ['This field is required']
        elif len(password) < 8:
            errors['password'] = ['Password must be at least 8 characters']
        
        # Return validation errors if any
        if errors:
            return JsonResponse({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create superuser
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_superuser=True
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Superuser created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            import traceback
            from django.conf import settings
            DEBUG = getattr(settings, 'DEBUG', False)
            error_msg = str(e)
            if DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return JsonResponse({
                'success': False,
                'error': 'Failed to create superuser',
                'message': error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        import traceback
        from django.conf import settings
        DEBUG = getattr(settings, 'DEBUG', False)
        error_msg = str(e)
        if DEBUG:
            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'message': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
