import secrets
import uuid
from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Case, IntegerField, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ContactInquiryForm, PickupForm, RecyclingRecordForm, RegistrationForm
from .models import ContactInquiry, Notification, OTPVerification, Payment, Pickup, RecyclingRecord, Reward, RewardWallet, Subscription, SubscriptionPlan, User
from .payments import verify_paystack
from .permissions import admin_required, collector_required, customer_required, is_admin
from .rate_limits import rate_limit
from .services import audit_event, notify, redeem_reward, reject_recycling_record, verify_recycling_record


def home(request):
	return render(request, 'home.html')


def about(request):
	return render(request, 'pages/about.html')


def services(request):
	return render(request, 'pages/services.html')


def how_it_works(request):
	return render(request, 'pages/how_it_works.html')


def faq(request):
	return render(request, 'pages/faq.html')


def plan_detail(request, plan_slug):
	plan = get_object_or_404(SubscriptionPlan, name__iexact=plan_slug, is_active=True)
	return render(request, 'pages/plan_detail.html', {'plan': plan})


@rate_limit('contact', limit=5, window=3600)
def contact(request):
	if request.method == 'POST':
		form = ContactInquiryForm(request.POST)
		if form.is_valid():
			inquiry = form.save()
			audit_event(request, 'CONTACT_INQUIRY_CREATED', inquiry, description='Public contact enquiry submitted')
			if inquiry.email:
				notify_user = User.objects.filter(email=inquiry.email).first()
				if notify_user:
					notify(notify_user, 'Contact request received', 'Your EcoBin enquiry has been received and is ready for follow-up.', email=False)
			return render(request, 'pages/contact.html', {'form': ContactInquiryForm(), 'submitted': True})
	else:
		form = ContactInquiryForm()
	return render(request, 'pages/contact.html', {'form': form})


@login_required
@customer_required
def dashboard(request):
	pickups = Pickup.objects.all() if is_admin(request.user) else request.user.pickups.all()
	records = RecyclingRecord.objects.all() if is_admin(request.user) else request.user.recycling_records.all()
	subscriptions = Subscription.objects.all() if is_admin(request.user) else request.user.subscriptions.all()
	upcoming = pickups.exclude(status__in=[Pickup.Status.CANCELLED, Pickup.Status.COMPLETED, Pickup.Status.FAILED]).order_by('pickup_date').first()
	recycled = sum((record.weight_kg for record in records.filter(verification_status=RecyclingRecord.VerificationStatus.VERIFIED)), 0)
	wallet, _ = RewardWallet.objects.get_or_create(customer=request.user)
	subscription = subscriptions.filter(status=Subscription.Status.ACTIVE).select_related('plan').first()
	return render(request, 'dashboard.html', {'upcoming': upcoming, 'recycled': recycled, 'wallet': wallet, 'subscription': subscription, 'notifications': request.user.notifications.order_by('-created_at')[:10]})


@login_required
@customer_required
def customer_pickups(request):
	pickups = (Pickup.objects.all() if is_admin(request.user) else request.user.pickups.all()).select_related('customer', 'collector').order_by('-pickup_date', '-created_at')
	return render(request, 'customer_pickups.html', {'pickups': pickups})


@login_required
@customer_required
def customer_subscription(request):
	subscriptions = (Subscription.objects.all() if is_admin(request.user) else request.user.subscriptions.all()).select_related('customer', 'plan').order_by('-created_at')
	return render(request, 'customer_subscription.html', {'subscriptions': subscriptions})


@login_required
@customer_required
def customer_profile(request):
	return render(request, 'customer_profile.html', {'profile': getattr(request.user, 'customer_profile', None)})


@login_required
@customer_required
def notifications(request):
	if request.method == 'POST':
		request.user.notifications.filter(is_read=False).update(is_read=True, updated_at=timezone.now())
		return redirect('dashboard')
	return render(request, 'dashboard.html', {'notifications': request.user.notifications.order_by('-created_at')[:50], 'wallet': RewardWallet.objects.get_or_create(customer=request.user)[0], 'upcoming': None, 'recycled': 0, 'subscription': None})


@login_required
@customer_required
@rate_limit('pickup-create', limit=5, window=3600)
def create_pickup(request):
	if request.method == 'POST':
		form = PickupForm(request.POST)
		if form.is_valid():
			pickup = form.save(commit=False)
			pickup.customer = request.user
			pickup.save()
			audit_event(request, 'PICKUP_CREATED', pickup, description='Customer created a pickup request')
			return redirect('dashboard')
	else:
		form = PickupForm()
	return render(request, 'pickup_form.html', {'form': form})


def pricing(request):
	plan_order = Case(
		When(name='Basic', then=0),
		When(name='Standard', then=1),
		When(name='Business', then=2),
		default=3,
		output_field=IntegerField(),
	)
	plans = SubscriptionPlan.objects.filter(is_active=True).order_by(plan_order, 'name')
	return render(request, 'pricing.html', {'plans': plans})


@login_required
@customer_required
@rate_limit('subscribe', limit=5, window=3600)
def subscribe(request, plan_id):
	plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
	if request.method != 'POST':
		return redirect('pricing')
	subscription = Subscription.objects.create(customer=request.user, plan=plan)
	reference = f'ecobin-{uuid.uuid4().hex}'
	Payment.objects.create(customer=request.user, subscription=subscription, amount=plan.price or 0, provider_reference=reference)
	audit_event(request, 'SUBSCRIPTION_CREATED', subscription, description=f'{plan.name} subscription created')
	notify(request.user, 'Subscription payment started', f'Your {plan.name} subscription is awaiting payment verification.', email=False)
	return render(request, 'payment_pending.html', {'subscription': subscription, 'payment': subscription.payments.latest('created_at'), 'paystack_configured': bool(settings.PAYSTACK_PUBLIC_KEY)})


@login_required
@customer_required
def verify_payment(request, payment_id):
	payment = get_object_or_404(Payment, id=payment_id) if is_admin(request.user) else get_object_or_404(Payment, id=payment_id, customer=request.user)
	if request.method != 'POST':
		return redirect('dashboard')
	if payment.status == Payment.Status.SUCCESSFUL:
		return redirect('dashboard')
	data = verify_paystack(payment.provider_reference)
	expected_amount = int(payment.amount * 100)
	amount_matches = data and int(data.get('amount', -1)) == expected_amount
	currency_matches = not data or not data.get('currency') or data.get('currency') == payment.currency
	if data and data.get('status') == 'success' and amount_matches and currency_matches:
		with transaction.atomic():
			payment = Payment.objects.select_for_update().get(pk=payment.pk)
			if payment.status == Payment.Status.SUCCESSFUL:
				return redirect('dashboard')
			payment.status = Payment.Status.SUCCESSFUL
			payment.verified_at = timezone.now()
			payment.metadata = {'provider': 'paystack', 'channel': data.get('channel', '')}
			payment.save(update_fields=['status', 'verified_at', 'metadata', 'updated_at'])
			payment.subscription.status = Subscription.Status.ACTIVE
			payment.subscription.starts_on = timezone.localdate()
			payment.subscription.save(update_fields=['status', 'starts_on', 'updated_at'])
			audit_event(request, 'PAYMENT_VERIFIED', payment, description='Payment verified server-side')
			notify(payment.customer, 'Subscription active', f'Your {payment.subscription.plan.name} plan is now active.')
		return redirect('dashboard')
	if data:
		payment.status = Payment.Status.FAILED
		payment.save(update_fields=['status', 'updated_at'])
	return render(request, 'payment_pending.html', {'subscription': payment.subscription, 'payment': payment, 'payment_failed': True})


def rewards(request):
	wallet = None
	transactions = []
	if request.user.is_authenticated:
		wallet, _ = RewardWallet.objects.get_or_create(customer=request.user)
		transactions = wallet.transactions.select_related('reward', 'recycling_record')[:20]
	return render(request, 'rewards.html', {'wallet': wallet, 'rewards': Reward.objects.filter(is_active=True, availability__gt=0), 'transactions': transactions})


@login_required
@customer_required
@rate_limit('reward-redemption', limit=5, window=3600)
def redeem(request, reward_id):
	if request.method != 'POST':
		return redirect('rewards')
	reward = get_object_or_404(Reward, id=reward_id)
	redemption = redeem_reward(request.user, reward)
	if redemption is None:
		return render(request, 'rewards.html', {'wallet': RewardWallet.objects.get_or_create(customer=request.user)[0], 'rewards': Reward.objects.filter(is_active=True, availability__gt=0), 'error': 'This reward is unavailable or your points balance is too low.'}, status=400)
	audit_event(request, 'REWARD_REDEEMED', redemption, description=f'Reward redemption created for {reward.name}')
	return redirect('rewards')


@login_required
@collector_required
def record_recycling(request, pickup_id):
	pickup_filters = {'id': pickup_id, 'status': Pickup.Status.COLLECTED}
	if not is_admin(request.user):
		pickup_filters['collector'] = request.user
	pickup = get_object_or_404(Pickup, **pickup_filters)
	if request.method == 'POST':
		form = RecyclingRecordForm(request.POST)
		if form.is_valid():
			record = form.save(commit=False)
			record.customer = pickup.customer
			record.pickup = pickup
			record.collector = pickup.collector or request.user
			record.save()
			notify(pickup.customer, 'Recycling recorded', 'Your collected recyclable material is awaiting verification.')
			return redirect('collector-dashboard')
	else:
		form = RecyclingRecordForm()
	return render(request, 'recycling_form.html', {'form': form, 'pickup': pickup})


@login_required
@admin_required
def verify_recycling(request, record_id):
	if request.method != 'POST':
		return redirect('admin-dashboard')
	record = get_object_or_404(RecyclingRecord, id=record_id, verification_status=RecyclingRecord.VerificationStatus.PENDING)
	if request.POST.get('decision') == 'reject':
		reject_recycling_record(record)
		audit_event(request, 'RECYCLING_REJECTED', record, success=True, severity='WARNING', description='Administrator rejected a recycling record')
	else:
		verify_recycling_record(record)
		audit_event(request, 'RECYCLING_VERIFIED', record, description='Administrator verified a recycling record')
	return redirect('admin-dashboard')


@login_required
@collector_required
def collector_dashboard(request):
	pickups = (Pickup.objects.all() if is_admin(request.user) else request.user.assigned_pickups.all()).select_related('customer', 'collector').exclude(status__in=[Pickup.Status.COMPLETED, Pickup.Status.CANCELLED]).order_by('pickup_date')
	return render(request, 'collector_dashboard.html', {'pickups': pickups})


@login_required
@collector_required
def update_pickup_status(request, pickup_id):
	if request.method != 'POST':
		return render(request, '403.html', status=403)
	pickup = get_object_or_404(Pickup, id=pickup_id) if is_admin(request.user) else get_object_or_404(Pickup, id=pickup_id, collector=request.user)
	allowed = {
		Pickup.Status.ASSIGNED: {Pickup.Status.EN_ROUTE},
		Pickup.Status.EN_ROUTE: {Pickup.Status.ARRIVED},
		Pickup.Status.ARRIVED: {Pickup.Status.COLLECTED, Pickup.Status.FAILED},
		Pickup.Status.COLLECTED: {Pickup.Status.VERIFIED},
	}
	next_status = request.POST.get('status')
	if next_status in allowed.get(pickup.status, set()):
		previous_status = pickup.status
		pickup.status = next_status
		pickup.save(update_fields=['status', 'updated_at'])
		audit_event(request, 'PICKUP_STATUS_CHANGED', pickup, description=f'{previous_status} to {next_status}')
	return redirect('collector-dashboard')


@login_required
@admin_required
def admin_dashboard(request):
	return render(request, 'admin_dashboard.html', {'customers': User.objects.filter(role=User.Role.CUSTOMER).count(), 'collectors': User.objects.filter(role=User.Role.COLLECTOR, is_active=True).count(), 'pending_pickups': Pickup.objects.filter(status=Pickup.Status.REQUESTED).count(), 'completed_pickups': Pickup.objects.filter(status=Pickup.Status.COMPLETED).count(), 'recycling_kg': sum(record.weight_kg for record in RecyclingRecord.objects.filter(verification_status=RecyclingRecord.VerificationStatus.VERIFIED)), 'pending_recycling': RecyclingRecord.objects.filter(verification_status=RecyclingRecord.VerificationStatus.PENDING).select_related('customer', 'collector', 'pickup')})


def register(request):
	if request.method == 'POST':
		form = RegistrationForm(request.POST)
		if form.is_valid():
			user = form.save()
			code = f'{secrets.randbelow(1000000):06d}'
			OTPVerification.objects.create(user=user, code_hash=make_password(code), expires_at=timezone.now() + timedelta(minutes=10))
			send_mail('Verify your EcoBin Ghana account', f'Your EcoBin verification code is {code}. It expires in 10 minutes.', None, [user.email], fail_silently=False)
			request.session['pending_verification_user'] = str(user.pk)
			return redirect('verify-otp')
	else:
		form = RegistrationForm()
	return render(request, 'registration/register.html', {'form': form})


def verify_otp(request):
	user_id = request.session.get('pending_verification_user')
	if not user_id:
		return redirect('register')
	user = get_object_or_404(User, pk=user_id)
	verification = user.otp_verifications.filter(used_at__isnull=True).order_by('-created_at').first()
	if request.method == 'POST' and verification:
		code = request.POST.get('code', '').strip()
		verification.attempts += 1
		if verification.attempts <= 5 and verification.expires_at > timezone.now() and check_password(code, verification.code_hash):
			verification.used_at = timezone.now()
			verification.save(update_fields=['attempts', 'used_at', 'updated_at'])
			user.is_active = True
			user.is_verified = True
			user.save(update_fields=['is_active', 'is_verified'])
			login(request, user)
			request.session.pop('pending_verification_user', None)
			return redirect('dashboard')
		verification.save(update_fields=['attempts', 'updated_at'])
	return render(request, 'registration/verify_otp.html', {'expired': not verification or verification.expires_at <= timezone.now()})
