import base64
import ipaddress
import json
import re
from urllib.request import Request, urlopen

from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import AuditLog, Notification, Pickup, RecyclingRecord, RewardTransaction, RewardWallet, Subscription


def request_audit_context(request):
	remote_address = request.META.get('REMOTE_ADDR', '')
	try:
		ipaddress.ip_address(remote_address)
	except ValueError:
		remote_address = ''

	trusted_proxy_count = max(0, getattr(settings, 'AUDIT_TRUSTED_PROXY_COUNT', 0))
	forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
	if trusted_proxy_count and remote_address and forwarded_for:
		try:
			forwarded_addresses = [str(ipaddress.ip_address(value.strip())) for value in forwarded_for.split(',')]
			proxy_chain = forwarded_addresses + [remote_address]
			if len(proxy_chain) > trusted_proxy_count:
				remote_address = proxy_chain[-trusted_proxy_count - 1]
		except ValueError:
			pass

	user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
	user_agent_lower = user_agent.lower()
	if 'edg/' in user_agent_lower or 'edge/' in user_agent_lower:
		browser = 'Edge'
	elif 'opr/' in user_agent_lower or 'opera' in user_agent_lower:
		browser = 'Opera'
	elif 'samsungbrowser/' in user_agent_lower:
		browser = 'Samsung Internet'
	elif 'firefox/' in user_agent_lower or 'fxios/' in user_agent_lower:
		browser = 'Firefox'
	elif 'chrome/' in user_agent_lower or 'crios/' in user_agent_lower:
		browser = 'Chrome'
	elif 'safari/' in user_agent_lower:
		browser = 'Safari'
	else:
		browser = 'Unknown'

	if 'android' in user_agent_lower:
		operating_system = 'Android'
	elif any(marker in user_agent_lower for marker in ('iphone', 'ipad', 'ipod')):
		operating_system = 'iOS'
	elif 'windows' in user_agent_lower:
		operating_system = 'Windows'
	elif 'mac os x' in user_agent_lower or 'macintosh' in user_agent_lower:
		operating_system = 'macOS'
	elif 'cros' in user_agent_lower:
		operating_system = 'Chrome OS'
	elif 'linux' in user_agent_lower:
		operating_system = 'Linux'
	else:
		operating_system = 'Unknown'

	if 'ipad' in user_agent_lower or 'tablet' in user_agent_lower:
		device = 'Tablet'
	elif any(marker in user_agent_lower for marker in ('mobile', 'iphone', 'ipod', 'android')):
		device = 'Mobile'
	else:
		device = 'Desktop'

	resolver_match = getattr(request, 'resolver_match', None)
	return {
		'ip_address': remote_address or None,
		'user_agent': user_agent,
		'browser': browser,
		'operating_system': operating_system,
		'device': device,
		'route_name': getattr(resolver_match, 'view_name', '')[:200],
	}


def audit_request_path(request):
	resolver_match = getattr(request, 'resolver_match', None)
	if getattr(resolver_match, 'view_name', '') == 'password_reset_confirm':
		return '/reset/[redacted]/[redacted]/'
	return request.path[:500]


def safe_audit_field_names(field_names):
	secret_field = re.compile(r'(password|otp|token|secret|csrf|authorization|api.?key|code)', re.IGNORECASE)
	return [name[:100] for name in field_names if not secret_field.search(name)][:50]


def audit_submitted_fields(request):
	if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
		return []
	return safe_audit_field_names(request.POST.keys())


def audit_event(request, event, obj=None, success=True, severity='INFO', description='', metadata=None, actor=None):
	user = actor if actor is not None else getattr(request, 'user', None)
	return AuditLog.objects.create(
		user=user if user and user.is_authenticated else None,
		event=event,
		action=request.method,
		**request_audit_context(request),
		request_method=request.method,
		request_path=audit_request_path(request),
		success=success,
		severity=severity,
		object_type=obj.__class__.__name__ if obj else '',
		object_uuid=obj.pk if obj else None,
		description=description[:500],
		metadata=metadata or {},
	)


def _send_sms(user, message):
	if not user.phone or not settings.SMS_API_URL or not settings.SMS_API_KEY:
		return False
	payload = json.dumps({'to': user.phone, 'message': message, 'sender': settings.SMS_SENDER_ID}).encode()
	request = Request(settings.SMS_API_URL, data=payload, headers={'Authorization': f'Bearer {settings.SMS_API_KEY}', 'Content-Type': 'application/json'}, method='POST')
	try:
		with urlopen(request, timeout=5):
			return True
	except OSError:
		return False


def _send_push(user, title, message):
	if not user.push_subscription or not settings.VAPID_PRIVATE_KEY:
		return False
	try:
		from pywebpush import webpush
		webpush(user.push_subscription, json.dumps({'title': title, 'body': message}), vapid_private_key=settings.VAPID_PRIVATE_KEY, vapid_claims={'sub': settings.VAPID_CLAIMS_EMAIL})
		return True
	except Exception:
		return False


def notify(user, title, message, email=True, sms=True, push=True):
	notification = Notification.objects.create(user=user, title=title, message=message)
	if email and user.email:
		send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
		notification.emailed_at = timezone.now()
	if sms and _send_sms(user, message):
		notification.sms_sent_at = timezone.now()
	if push and _send_push(user, title, message):
		notification.pushed_at = timezone.now()
	notification.save(update_fields=['emailed_at', 'sms_sent_at', 'pushed_at', 'updated_at'])
	return notification


def reward_points_for(record):
	multiplier = Decimal('1')
	subscription = record.customer.subscriptions.filter(status=Subscription.Status.ACTIVE).select_related('plan').first()
	if subscription:
		multiplier = subscription.plan.reward_multiplier
	return int(record.weight_kg * Decimal('10') * multiplier)


@transaction.atomic
def verify_recycling_record(record):
	record = RecyclingRecord.objects.select_for_update().select_related('customer').get(pk=record.pk)
	if record.verification_status != RecyclingRecord.VerificationStatus.PENDING:
		return False
	record.verification_status = RecyclingRecord.VerificationStatus.VERIFIED
	record.verified_at = timezone.now()
	record.save(update_fields=['verification_status', 'verified_at', 'updated_at'])
	record.pickup.status = Pickup.Status.VERIFIED
	record.pickup.save(update_fields=['status', 'updated_at'])
	wallet, _ = RewardWallet.objects.select_for_update().get_or_create(customer=record.customer)
	points = reward_points_for(record)
	wallet.balance = wallet.balance + points
	wallet.save(update_fields=['balance', 'updated_at'])
	RewardTransaction.objects.create(wallet=wallet, kind=RewardTransaction.Kind.EARNED, points=points, description=f'{record.weight_kg} kg {record.material_type} verified', recycling_record=record)
	notify(record.customer, 'Recycling verified', f'{points} EcoBin points were added to your wallet.')
	return True


@transaction.atomic
def reject_recycling_record(record):
	record = RecyclingRecord.objects.select_for_update().select_related('customer').get(pk=record.pk)
	if record.verification_status != RecyclingRecord.VerificationStatus.PENDING:
		return False
	record.verification_status = RecyclingRecord.VerificationStatus.REJECTED
	record.save(update_fields=['verification_status', 'updated_at'])
	notify(record.customer, 'Recycling record declined', 'Your recycling record was not approved. Please contact support if you need more information.')
	return True


@transaction.atomic
def redeem_reward(customer, reward):
	wallet = RewardWallet.objects.select_for_update().get_or_create(customer=customer)[0]
	reward = type(reward).objects.select_for_update().get(pk=reward.pk)
	if not reward.is_active or reward.availability < 1 or wallet.balance < reward.points_cost:
		return None
	wallet.balance -= reward.points_cost
	wallet.save(update_fields=['balance', 'updated_at'])
	RewardTransaction.objects.create(wallet=wallet, kind=RewardTransaction.Kind.SPENT, points=reward.points_cost, description=f'Redeemed {reward.name}', reward=reward)
	redemption = customer.redemptions.create(reward=reward, points_spent=reward.points_cost, status='PENDING')
	reward.availability -= 1
	reward.save(update_fields=['availability', 'updated_at'])
	notify(customer, 'Reward redemption received', f'Your {reward.name} redemption is being processed.')
	return redemption