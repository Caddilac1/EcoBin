from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import AuditLog, Notification, Pickup, RecyclingRecord, RewardTransaction, RewardWallet, Subscription


def audit_event(request, event, obj=None, success=True, severity='INFO', description='', metadata=None):
	return AuditLog.objects.create(
		user=request.user if request.user.is_authenticated else None,
		event=event,
		action=request.method,
		ip_address=request.META.get('REMOTE_ADDR'),
		user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
		request_method=request.method,
		request_path=request.path[:500],
		success=success,
		severity=severity,
		object_type=obj.__class__.__name__ if obj else '',
		object_uuid=obj.pk if obj else None,
		description=description[:500],
		metadata=metadata or {},
	)


def notify(user, title, message, email=True):
	notification = Notification.objects.create(user=user, title=title, message=message)
	if email and user.email:
		send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
		notification.emailed_at = timezone.now()
		notification.save(update_fields=['emailed_at', 'updated_at'])
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