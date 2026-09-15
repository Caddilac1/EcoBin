from django.core.cache import cache
from django.http import HttpResponse

from .models import AuditLog


class SensitiveRateLimitMiddleware:
    LIMITS = {
        '/login/': (10, 300),
        '/register/': (5, 3600),
        '/verify-otp/': (10, 600),
        '/password-reset/': (5, 3600),
        '/payments/': (10, 3600),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST':
            for path, (limit, window) in self.LIMITS.items():
                if request.path == path or request.path.startswith(path):
                    ip = request.META.get('REMOTE_ADDR', 'unknown')
                    key = f'endpoint-limit:{path}:{ip}'
                    count = cache.get(key, 0)
                    if count >= limit:
                        return HttpResponse('Too many attempts. Please try again later.', status=429)
                    cache.set(key, count + 1, window)
                    break
        return self.get_response(request)


class RequestAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        ip_address = forwarded_for.split(',')[0].strip() if forwarded_for else request.META.get('REMOTE_ADDR')
        if not request.path.startswith('/static/'):
            AuditLog.objects.create(user=user, event='REQUEST', action=request.method, ip_address=ip_address, user_agent=request.META.get('HTTP_USER_AGENT', '')[:500], request_method=request.method, request_path=request.path[:500], success=response.status_code < 400, severity='WARNING' if response.status_code >= 400 else 'INFO')
        return response