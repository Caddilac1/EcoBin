from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse, HttpResponse


def rate_limit(key_prefix, limit=5, window=300):
	def decorator(view):
		@wraps(view)
		def wrapped(request, *args, **kwargs):
			if request.method == 'POST':
				ip = request.META.get('REMOTE_ADDR', 'unknown')
				identity = str(getattr(request.user, 'pk', 'anonymous'))
				key = f'ratelimit:{key_prefix}:{ip}:{identity}'
				if cache.add(key, 1, window):
					return view(request, *args, **kwargs)
				count = cache.get(key, 0)
				if count >= limit:
					return JsonResponse({'detail': 'Too many attempts. Please try again later.'}, status=429) if request.headers.get('Accept') == 'application/json' else HttpResponse('Too many attempts. Please try again later.', status=429)
				cache.incr(key)
			return view(request, *args, **kwargs)
		return wrapped
	return decorator