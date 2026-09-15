from functools import wraps

from django.shortcuts import render

from .models import User


def is_admin(user):
	return user.is_authenticated and (user.is_superuser or user.is_staff or user.role == User.Role.ADMIN)


def role_required(*roles, require_active_collector=False):
	allowed_roles = set(roles)

	def decorator(view):
		@wraps(view)
		def wrapped(request, *args, **kwargs):
			user = request.user
			if not user.is_authenticated or (not is_admin(user) and user.role not in allowed_roles):
				return render(request, '403.html', status=403)
			if require_active_collector:
				profile = getattr(user, 'collector_profile', None)
				if not is_admin(user) and (not profile or not profile.is_active or not profile.is_verified):
					return render(request, '403.html', status=403)
			return view(request, *args, **kwargs)
		return wrapped
	return decorator


def customer_required(view):
	return role_required(User.Role.CUSTOMER, User.Role.COLLECTOR)(view)


def collector_required(view):
	return role_required(User.Role.COLLECTOR, require_active_collector=True)(view)


def admin_required(view):
	@wraps(view)
	def wrapped(request, *args, **kwargs):
		user = request.user
		if not is_admin(user):
			return render(request, '403.html', status=403)
		return view(request, *args, **kwargs)
	return wrapped
