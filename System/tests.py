from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import RegistrationForm
from .models import CollectorProfile, ContactInquiry, Notification, OTPVerification, Payment, Pickup, RecyclingRecord, Reward, RewardTransaction, RewardWallet, Subscription, SubscriptionPlan
from .services import redeem_reward, verify_recycling_record


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EcoBinFoundationTests(TestCase):
	def test_users_use_uuid_primary_keys(self):
		user = get_user_model().objects.create_user(email='customer@example.com', username='customer@example.com', password='A-strong-password-2026')
		self.assertIsNotNone(user.pk)
		self.assertEqual(user.pk.version, 4)

	def test_registration_form_validates_customer_details(self):
		form = RegistrationForm(data={'first_name': 'Ama', 'last_name': 'Mensah', 'email': 'ama@example.com', 'phone': '0240000000', 'customer_type': 'HOUSEHOLD', 'address': 'Amasaman', 'area': 'Greater Accra', 'password1': 'A-strong-password-2026', 'password2': 'A-strong-password-2026'})
		self.assertTrue(form.is_valid(), form.errors)

	def test_public_pages_use_dedicated_routes(self):
		for route_name in ('home', 'about', 'services', 'pricing', 'how-it-works', 'rewards', 'faq', 'contact'):
			response = self.client.get(reverse(route_name))
			self.assertEqual(response.status_code, 200, route_name)

	def test_contact_form_persists_an_inquiry(self):
		response = self.client.post(reverse('contact'), {'name': 'Ama Mensah', 'email': 'ama@example.com', 'organization': 'Amasaman School', 'message': 'We need a weekly collection route.'})
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['submitted'])
		self.assertTrue(ContactInquiry.objects.filter(email='ama@example.com', status='NEW').exists())

	def test_pickup_requires_authentication(self):
		response = self.client.get(reverse('create-pickup'))
		self.assertRedirects(response, f'{reverse("login")}?next={reverse("create-pickup")}')

	def test_pickup_is_owned_by_authenticated_customer(self):
		user = get_user_model().objects.create_user(email='customer@example.com', username='customer@example.com', password='A-strong-password-2026', is_active=True, is_verified=True)
		self.client.force_login(user)
		response = self.client.post(reverse('create-pickup'), {'address': 'Pokuase', 'pickup_date': '2026-10-01', 'time_window': '10:00 - 12:00', 'waste_type': 'RECYCLABLE', 'estimated_weight_kg': '2.5', 'notes': ''})
		self.assertRedirects(response, reverse('dashboard'))
		self.assertEqual(Pickup.objects.get().customer, user)

	def test_customer_cannot_access_collector_or_admin_workspaces(self):
		user = get_user_model().objects.create_user(email='workspace-customer@example.com', username='workspace-customer@example.com', password='A-strong-password-2026')
		self.client.force_login(user)
		self.assertEqual(self.client.get(reverse('collector-dashboard')).status_code, 403)
		self.assertEqual(self.client.get(reverse('admin-dashboard')).status_code, 403)

	def test_collector_must_be_verified_and_active_for_operations(self):
		collector = get_user_model().objects.create_user(email='unverified-collector@example.com', username='unverified-collector@example.com', password='A-strong-password-2026', role='COLLECTOR')
		CollectorProfile.objects.create(user=collector, is_verified=False, is_active=True)
		self.client.force_login(collector)
		self.assertEqual(self.client.get(reverse('collector-dashboard')).status_code, 403)
		collector.collector_profile.is_verified = True
		collector.collector_profile.is_active = False
		collector.collector_profile.save(update_fields=['is_verified', 'is_active', 'updated_at'])
		self.assertEqual(self.client.get(reverse('collector-dashboard')).status_code, 403)

	def test_verified_active_collector_can_access_operations(self):
		collector = get_user_model().objects.create_user(email='verified-collector@example.com', username='verified-collector@example.com', password='A-strong-password-2026', role='COLLECTOR')
		CollectorProfile.objects.create(user=collector, is_verified=True, is_active=True)
		self.client.force_login(collector)
		self.assertEqual(self.client.get(reverse('collector-dashboard')).status_code, 200)

	def test_collector_inherits_customer_pickup_access(self):
		collector = get_user_model().objects.create_user(email='collector-customer@example.com', username='collector-customer@example.com', password='A-strong-password-2026', role='COLLECTOR')
		CollectorProfile.objects.create(user=collector, is_verified=True, is_active=True)
		self.client.force_login(collector)
		response = self.client.post(reverse('create-pickup'), {'address': 'Pokuase', 'pickup_date': '2026-10-01', 'time_window': '10:00 - 12:00', 'waste_type': 'RECYCLABLE', 'estimated_weight_kg': '2.5', 'notes': ''})
		self.assertRedirects(response, reverse('dashboard'))
		self.assertEqual(Pickup.objects.get().customer, collector)

	def test_admin_inherits_collector_access_and_can_update_any_pickup(self):
		customer = get_user_model().objects.create_user(email='admin-access-customer@example.com', username='admin-access-customer@example.com', password='A-strong-password-2026')
		collector = get_user_model().objects.create_user(email='admin-access-collector@example.com', username='admin-access-collector@example.com', password='A-strong-password-2026', role='COLLECTOR')
		CollectorProfile.objects.create(user=collector, is_verified=True, is_active=True)
		pickup = Pickup.objects.create(customer=customer, collector=collector, address='Amasaman', pickup_date='2026-10-01', time_window='10:00', waste_type='RECYCLABLE', status='ASSIGNED')
		admin = get_user_model().objects.create_superuser(email='full-admin@example.com', username='full-admin@example.com', password='A-strong-password-2026')
		self.client.force_login(admin)
		self.assertEqual(self.client.get(reverse('collector-dashboard')).status_code, 200)
		self.assertRedirects(self.client.post(reverse('update-pickup-status', args=[pickup.id]), {'status': 'EN_ROUTE'}), reverse('collector-dashboard'))
		pickup.refresh_from_db()
		self.assertEqual(pickup.status, Pickup.Status.EN_ROUTE)

	def test_customer_cannot_verify_another_customers_payment(self):
		owner = get_user_model().objects.create_user(email='payment-owner@example.com', username='payment-owner@example.com', password='A-strong-password-2026')
		attacker = get_user_model().objects.create_user(email='payment-attacker@example.com', username='payment-attacker@example.com', password='A-strong-password-2026')
		plan = SubscriptionPlan.objects.create(name='Authorization plan', price=75, description='Test')
		subscription = Subscription.objects.create(customer=owner, plan=plan)
		payment = Payment.objects.create(customer=owner, subscription=subscription, amount=plan.price, provider_reference='authorization-reference')
		self.client.force_login(attacker)
		self.assertEqual(self.client.post(reverse('verify-payment', args=[payment.id])).status_code, 404)

	def test_expired_otp_cannot_verify(self):
		user = get_user_model().objects.create_user(email='customer@example.com', username='customer@example.com', password='A-strong-password-2026', is_active=False)
		OTPVerification.objects.create(user=user, code_hash=make_password('123456'), expires_at=timezone.now() - timedelta(minutes=1))
		session = self.client.session
		session['pending_verification_user'] = str(user.pk)
		session.save()
		response = self.client.post(reverse('verify-otp'), {'code': '123456'})
		user.refresh_from_db()
		self.assertEqual(response.status_code, 200)
		self.assertFalse(user.is_verified)

	def test_verified_recycling_awards_multiplier_points_once(self):
		user = get_user_model().objects.create_user(email='standard@example.com', username='standard@example.com', password='A-strong-password-2026')
		collector = get_user_model().objects.create_user(email='collector@example.com', username='collector@example.com', password='A-strong-password-2026', role='COLLECTOR')
		plan = SubscriptionPlan.objects.create(name='Test Standard', price=75, description='Test', reward_multiplier=1.5)
		from .models import Subscription, RewardWallet
		Subscription.objects.create(customer=user, plan=plan, status='ACTIVE')
		pickup = Pickup.objects.create(customer=user, collector=collector, address='Amasaman', pickup_date='2026-10-01', time_window='10:00', waste_type='RECYCLABLE', status='COLLECTED')
		record = RecyclingRecord.objects.create(customer=user, pickup=pickup, collector=collector, material_type='Plastic', weight_kg=2)
		self.assertTrue(verify_recycling_record(record))
		self.assertFalse(verify_recycling_record(record))
		self.assertEqual(RewardWallet.objects.get(customer=user).balance, 30)
		self.assertEqual(RewardTransaction.objects.filter(wallet__customer=user).count(), 1)

	def test_reward_redemption_cannot_overdraw_wallet(self):
		user = get_user_model().objects.create_user(email='rewards@example.com', username='rewards@example.com', password='A-strong-password-2026')
		wallet = RewardWallet.objects.create(customer=user, balance=50)
		reward = Reward.objects.create(name='Test voucher', description='Test', category='Voucher', points_cost=100, availability=1)
		self.assertIsNone(redeem_reward(user, reward))
		wallet.refresh_from_db()
		self.assertEqual(wallet.balance, 50)

	def test_reward_redemption_reserves_stock_and_notifies_customer(self):
		user = get_user_model().objects.create_user(email='stock@example.com', username='stock@example.com', password='A-strong-password-2026')
		RewardWallet.objects.create(customer=user, balance=100)
		reward = Reward.objects.create(name='Airtime', description='Test', category='Airtime', points_cost=100, availability=1)
		redemption = redeem_reward(user, reward)
		reward.refresh_from_db()
		self.assertIsNotNone(redemption)
		self.assertEqual(reward.availability, 0)
		self.assertEqual(Notification.objects.filter(user=user).count(), 1)

	def test_payment_verification_activates_subscription_and_is_idempotent(self):
		user = get_user_model().objects.create_user(email='payer@example.com', username='payer@example.com', password='A-strong-password-2026')
		plan = SubscriptionPlan.objects.create(name='Paid plan', price=75, description='Test')
		subscription = Subscription.objects.create(customer=user, plan=plan)
		payment = Payment.objects.create(customer=user, subscription=subscription, amount=plan.price, provider_reference='test-reference')
		self.client.force_login(user)
		with patch('System.views.verify_paystack', return_value={'status': 'success', 'amount': 7500, 'currency': 'GHS', 'channel': 'card'}) as verify:
			response = self.client.post(reverse('verify-payment', args=[payment.id]))
			self.assertRedirects(response, reverse('dashboard'))
			self.client.post(reverse('verify-payment', args=[payment.id]))
		self.assertEqual(verify.call_count, 1)
		payment.refresh_from_db()
		subscription.refresh_from_db()
		self.assertEqual(payment.status, Payment.Status.SUCCESSFUL)
		self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
		self.assertEqual(Notification.objects.filter(user=user).count(), 1)

	def test_payment_amount_mismatch_does_not_activate_subscription(self):
		user = get_user_model().objects.create_user(email='mismatch@example.com', username='mismatch@example.com', password='A-strong-password-2026')
		plan = SubscriptionPlan.objects.create(name='Mismatch plan', price=75, description='Test')
		subscription = Subscription.objects.create(customer=user, plan=plan)
		payment = Payment.objects.create(customer=user, subscription=subscription, amount=plan.price, provider_reference='mismatch-reference')
		self.client.force_login(user)
		with patch('System.views.verify_paystack', return_value={'status': 'success', 'amount': 1, 'currency': 'GHS'}):
			self.client.post(reverse('verify-payment', args=[payment.id]))
		payment.refresh_from_db()
		subscription.refresh_from_db()
		self.assertEqual(payment.status, Payment.Status.FAILED)
		self.assertEqual(subscription.status, Subscription.Status.PENDING)

	def test_recycling_verification_requires_admin_and_can_reject(self):
		user = get_user_model().objects.create_user(email='recycle-user@example.com', username='recycle-user@example.com', password='A-strong-password-2026')
		collector = get_user_model().objects.create_user(email='recycle-collector@example.com', username='recycle-collector@example.com', password='A-strong-password-2026', role='COLLECTOR')
		pickup = Pickup.objects.create(customer=user, collector=collector, address='Amasaman', pickup_date='2026-10-01', time_window='10:00', waste_type='RECYCLABLE', status='COLLECTED')
		record = RecyclingRecord.objects.create(customer=user, pickup=pickup, collector=collector, material_type='Plastic', weight_kg=2)
		self.client.force_login(user)
		self.assertEqual(self.client.post(reverse('verify-recycling', args=[record.id])).status_code, 403)
		admin = get_user_model().objects.create_user(email='ops@example.com', username='ops@example.com', password='A-strong-password-2026', role='ADMIN')
		self.client.force_login(admin)
		self.assertRedirects(self.client.post(reverse('verify-recycling', args=[record.id]), {'decision': 'reject'}), reverse('admin-dashboard'))
		record.refresh_from_db()
		self.assertEqual(record.verification_status, RecyclingRecord.VerificationStatus.REJECTED)
