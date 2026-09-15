import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


class UUIDModel(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class User(AbstractUser):
	class Role(models.TextChoices):
		CUSTOMER = 'CUSTOMER', 'Customer'
		COLLECTOR = 'COLLECTOR', 'Collector'
		PARTNER = 'PARTNER', 'Partner'
		ADMIN = 'ADMIN', 'Administrator'

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	email = models.EmailField(unique=True)
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
	phone = models.CharField(max_length=30, blank=True)
	is_verified = models.BooleanField(default=False)
	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = ['username']

	def __str__(self):
		return self.get_full_name() or self.email


class CustomerProfile(UUIDModel):
	class CustomerType(models.TextChoices):
		HOUSEHOLD = 'HOUSEHOLD', 'Household'
		SCHOOL = 'SCHOOL', 'School'
		RESTAURANT = 'RESTAURANT', 'Restaurant'
		SME = 'SME', 'SME'

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
	customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.HOUSEHOLD)
	organization_name = models.CharField(max_length=160, blank=True)
	address = models.TextField()
	area = models.CharField(max_length=100, default='Greater Accra')
	notifications_enabled = models.BooleanField(default=True)


class CollectorProfile(UUIDModel):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='collector_profile')
	is_verified = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	service_area = models.CharField(max_length=120, default='Greater Accra')


class SubscriptionPlan(UUIDModel):
	name = models.CharField(max_length=40, unique=True)
	price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	description = models.TextField()
	reward_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return self.name


class Subscription(UUIDModel):
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pending payment'
		ACTIVE = 'ACTIVE', 'Active'
		PAUSED = 'PAUSED', 'Paused'
		CANCELLED = 'CANCELLED', 'Cancelled'
		EXPIRED = 'EXPIRED', 'Expired'

	customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='subscriptions')
	plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	starts_on = models.DateField(null=True, blank=True)
	renews_on = models.DateField(null=True, blank=True)

	class Meta:
		indexes = [models.Index(fields=['customer', 'status'])]


class Payment(UUIDModel):
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pending'
		SUCCESSFUL = 'SUCCESSFUL', 'Successful'
		FAILED = 'FAILED', 'Failed'
		CANCELLED = 'CANCELLED', 'Cancelled'

	customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments')
	subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name='payments')
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	currency = models.CharField(max_length=3, default='GHS')
	provider = models.CharField(max_length=30, default='PAYSTACK')
	provider_reference = models.CharField(max_length=120, unique=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	verified_at = models.DateTimeField(null=True, blank=True)
	metadata = models.JSONField(default=dict, blank=True)

	class Meta:
		indexes = [models.Index(fields=['customer', 'status']), models.Index(fields=['provider_reference'])]


class Pickup(UUIDModel):
	class Status(models.TextChoices):
		REQUESTED = 'REQUESTED', 'Requested'
		SCHEDULED = 'SCHEDULED', 'Scheduled'
		ASSIGNED = 'ASSIGNED', 'Collector assigned'
		EN_ROUTE = 'EN_ROUTE', 'En route'
		ARRIVED = 'ARRIVED', 'Arrived'
		COLLECTED = 'COLLECTED', 'Collected'
		VERIFIED = 'VERIFIED', 'Verified'
		COMPLETED = 'COMPLETED', 'Completed'
		CANCELLED = 'CANCELLED', 'Cancelled'
		RESCHEDULED = 'RESCHEDULED', 'Rescheduled'
		FAILED = 'FAILED', 'Unable to collect'

	class WasteType(models.TextChoices):
		ORGANIC = 'ORGANIC', 'Organic'
		RECYCLABLE = 'RECYCLABLE', 'Plastic / recyclables'
		GENERAL = 'GENERAL', 'General'

	customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pickups')
	collector = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='assigned_pickups')
	address = models.TextField()
	pickup_date = models.DateField()
	time_window = models.CharField(max_length=80)
	waste_type = models.CharField(max_length=20, choices=WasteType.choices)
	notes = models.TextField(blank=True)
	estimated_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)

	class Meta:
		ordering = ['pickup_date', 'created_at']
		indexes = [models.Index(fields=['customer', 'status']), models.Index(fields=['pickup_date', 'status'])]


class RecyclingRecord(UUIDModel):
	class VerificationStatus(models.TextChoices):
		PENDING = 'PENDING', 'Pending verification'
		VERIFIED = 'VERIFIED', 'Verified'
		REJECTED = 'REJECTED', 'Rejected'

	customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recycling_records')
	pickup = models.ForeignKey(Pickup, on_delete=models.PROTECT, related_name='recycling_records')
	collector = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recorded_recycling')
	material_type = models.CharField(max_length=80)
	weight_kg = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
	verification_status = models.CharField(max_length=12, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
	verified_at = models.DateTimeField(null=True, blank=True)


class RewardWallet(UUIDModel):
	customer = models.OneToOneField(User, on_delete=models.PROTECT, related_name='reward_wallet')
	balance = models.PositiveIntegerField(default=0)


class Reward(UUIDModel):
	name = models.CharField(max_length=120)
	description = models.TextField()
	category = models.CharField(max_length=50)
	points_cost = models.PositiveIntegerField()
	partner_name = models.CharField(max_length=120, blank=True)
	is_active = models.BooleanField(default=True)
	availability = models.PositiveIntegerField(default=0)


class RewardTransaction(UUIDModel):
	class Kind(models.TextChoices):
		EARNED = 'EARNED', 'Earned'
		SPENT = 'SPENT', 'Spent'

	wallet = models.ForeignKey(RewardWallet, on_delete=models.PROTECT, related_name='transactions')
	kind = models.CharField(max_length=10, choices=Kind.choices)
	points = models.PositiveIntegerField()
	description = models.CharField(max_length=200)
	recycling_record = models.ForeignKey(RecyclingRecord, null=True, blank=True, on_delete=models.PROTECT)
	reward = models.ForeignKey(Reward, null=True, blank=True, on_delete=models.PROTECT)


class RewardRedemption(UUIDModel):
	customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='redemptions')
	reward = models.ForeignKey(Reward, on_delete=models.PROTECT, related_name='redemptions')
	points_spent = models.PositiveIntegerField()
	status = models.CharField(max_length=20, default='PENDING')


class AuditLog(UUIDModel):
	user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_events')
	event = models.CharField(max_length=80)
	action = models.CharField(max_length=80, blank=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.CharField(max_length=500, blank=True)
	request_method = models.CharField(max_length=10, blank=True)
	request_path = models.CharField(max_length=500, blank=True)
	success = models.BooleanField(default=True)
	severity = models.CharField(max_length=20, default='INFO')
	object_type = models.CharField(max_length=100, blank=True)
	object_uuid = models.UUIDField(null=True, blank=True)
	description = models.CharField(max_length=500, blank=True)
	metadata = models.JSONField(default=dict, blank=True)


class Notification(UUIDModel):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
	title = models.CharField(max_length=160)
	message = models.TextField()
	is_read = models.BooleanField(default=False)
	emailed_at = models.DateTimeField(null=True, blank=True)


class ContactInquiry(UUIDModel):
	class Status(models.TextChoices):
		NEW = 'NEW', 'New'
		IN_PROGRESS = 'IN_PROGRESS', 'In progress'
		RESOLVED = 'RESOLVED', 'Resolved'

	name = models.CharField(max_length=120)
	email = models.EmailField()
	organization = models.CharField(max_length=160, blank=True)
	message = models.TextField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)


class OTPVerification(UUIDModel):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_verifications')
	code_hash = models.CharField(max_length=128)
	expires_at = models.DateTimeField()
	attempts = models.PositiveSmallIntegerField(default=0)
	used_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		indexes = [models.Index(fields=['user', 'expires_at'])]
