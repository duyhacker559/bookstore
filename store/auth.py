"""
Authentication utilities for API endpoints.

Provides helpers for token-based authentication and decorators
to protect API views.

Usage:
    from store.auth import require_api_auth
    
    @require_api_auth
    def my_api_view(request):
        return JsonResponse({'data': 'secret'})
"""

import logging
from functools import wraps
from django.http import JsonResponse
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def get_or_create_user_token(user: User) -> str:
    """
    Get or create an API token for a user.
    
    Args:
        user: Django User instance
        
    Returns:
        str: API token
        
    Example:
        from django.contrib.auth.models import User
        from store.auth import get_or_create_user_token
        
        user = User.objects.get(username='john')
        token = get_or_create_user_token(user)
        print(f"API Token: {token}")
    """
    token, created = Token.objects.get_or_create(user=user)
    action = "created" if created else "retrieved"
    logger.info(f"Token {action} for user {user.username}")
    return token.key


def require_api_auth(view_func):
    """
    Decorator to require API token authentication on a view.
    
    Returns 401 Unauthorized if auth header is missing or invalid.
    
    Usage:
        from django.http import JsonResponse
        from store.auth import require_api_auth
        
        @require_api_auth
        def protected_api(request):
            return JsonResponse({'data': 'protected', 'user': request.user.username})
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'error': 'Missing or invalid Authorization header'},
                status=401
            )
        
        token_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            token = Token.objects.get(key=token_key)
            request.user = token.user
            logger.debug(f"API request authenticated for user: {token.user.username}")
        except Token.DoesNotExist:
            logger.warning(f"Invalid token attempted: {token_key[:10]}...")
            return JsonResponse(
                {'error': 'Invalid authentication token'},
                status=401
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_auth_decorator():
    """
    Return DRF authentication decorators for APIView usage.
    
    Usage with DRF:
        from rest_framework.decorators import api_view
        from store.auth import get_auth_decorator
        
        @api_view(['GET'])
        @get_auth_decorator()
        def protected_view(request):
            return Response({'data': 'protected'})
    """
    return [
        authentication_classes([TokenAuthentication]),
        permission_classes([IsAuthenticated])
    ]


class APIKeyAuthentication:
    """
    Custom authentication for service-to-service communication.
    
    Services authenticate using an API key instead of user tokens.
    
    Usage:
        # In settings.py
        REST_FRAMEWORK = {
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.TokenAuthentication',
                'store.auth.APIKeyAuthentication',
            ]
        }
    """
    
    def authenticate(self, request):
        """Authenticate using X-API-Key header."""
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
        
        # Validate API key (can be configured via settings)
        from django.conf import settings
        valid_keys = getattr(settings, 'VALID_API_KEYS', {})
        
        if api_key in valid_keys:
            service_name = valid_keys[api_key]
            logger.info(f"API request authenticated for service: {service_name}")
            # Return authenticated user and auth object
            # For service-to-service, we could use a special system user
            return (None, api_key)
        
        logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
        raise Exception('Invalid API key')
    
    def authenticate_header(self, request):
        return 'X-API-Key'


def create_service_token(service_name: str) -> str:
    """
    Create an authentication token for a service account.
    
    Args:
        service_name: Name of the service (e.g., 'payment-service')
        
    Returns:
        str: API token for the service
        
    Example:
        from store.auth import create_service_token
        
        token = create_service_token('payment-service')
        # Use token in HTTP header: Authorization: Bearer {token}
    """
    # Create or get service user
    service_user, created = User.objects.get_or_create(
        username=f'service_{service_name}',
        defaults={
            'first_name': f'{service_name} Service',
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
        }
    )
    
    token = get_or_create_user_token(service_user)
    
    if created:
        logger.info(f"Created service account: {service_user.username}")
    
    return token
