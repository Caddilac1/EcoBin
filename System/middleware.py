from django.core.cache import cache
from django.http import HttpResponse

from .models import AuditLog
from .services import audit_request_path, audit_submitted_fields, request_audit_context


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
        if not request.path.startswith('/static/'):
            metadata = {'submitted_fields': audit_submitted_fields(request)}
            success = getattr(request, 'audit_success', response.status_code < 400)
            AuditLog.objects.create(user=user, event='REQUEST', action=request.method, **request_audit_context(request), request_method=request.method, request_path=audit_request_path(request), success=success, severity='WARNING' if not success else 'INFO', metadata=metadata)
        return response