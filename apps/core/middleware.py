"""Custom middleware for API CSRF exemption."""
from django.utils.deprecation import MiddlewareMixin


class DisableCSRFForAPI(MiddlewareMixin):
    """Disable CSRF protection for API endpoints."""
    
    def process_request(self, request):
        # Exempt all /api/ endpoints from CSRF
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
