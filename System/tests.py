from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import PickupForm, RegistrationForm
from .admin import PickupAdmin
from .models import AuditLog, CollectorProfile, ContactInquiry, Notification, OTPVerification, Payment, Pickup, RecyclingRecord, Reward, RewardTransaction, RewardWallet, Subscription, SubscriptionPlan
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

	def test_registration_form_creates_collector_profile(self):
		form = RegistrationForm(data={'first_name': 'Kojo', 'last_name': 'Mensah', 'role': 'COLLECTOR', 'email': 'kojo@example.com', 'phone': '0240000000', 'area': 'Tema', 'password1': 'A-strong-password-2026', 'password2': 'A-strong-password-2026'})
		self.assertTrue(form.is_valid(), form.errors)
		user = form.save()
		self.assertEqual(user.role, 'COLLECTOR')
		self.assertEqual(user.collector_profile.service_area, 'Tema')
		self.assertFalse(hasattr(user, 'customer_profile'))

	def test_location_can_replace_typed_address_and_pickup_weight_is_optional(self):
		form = RegistrationForm(data={'first_name': 'Ama', 'last_name': 'Mensah', 'email': 'location@example.com', 'phone': '0240000000', 'customer_type': 'HOUSEHOLD', 'address': '', 'area': 'Greater Accra', 'location_lat': '5.6037', 'location_lng': '-0.1870', 'password1': 'A-strong-password-2026', 'password2': 'A-strong-password-2026'})
		self.assertTrue(form.is_valid(), form.errors)
		pickup_form = PickupForm(data={'address': 'GPS location', 'pickup_date': '2026-10-01', 'time_window': '10:00 - 12:00', 'waste_type': 'RECYCLABLE'})
		self.assertTrue(pickup_form.is_valid(), pickup_form.errors)

	def test_public_pages_use_dedicated_routes(self):
		for route_name in ('home', 'about', 'services', 'pricing', 'how-it-works', 'rewards', 'faq', 'contact'):
			response = self.client.get(reverse(route_name))
			self.assertEqual(response.status_code, 200, route_name)
		self.assertContains(self.client.get(reverse('home')), 'data-scroll-story')
		self.assertContains(self.client.get(reverse('home')), 'data-story-step="reward"')
		self.assertContains(self.client.get(reverse('home')), 'data-hero-wave')

	def test_contact_form_persists_an_inquiry(self):
		response = self.client.post(reverse('contact'), {'name': 'Ama Mensah', 'email': 'ama@example.com', 'organization': 'Amasaman School', 'message': 'We need a weekly collection route.'})
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['submitted'])
		self.assertTrue(ContactInquiry.objects.filter(email='ama@example.com', status='NEW').exists())

	def test_request_audit_captures_security_context_without_form_values(self):
		response = self.client.post(reverse('contact'), {'name': 'Ama Mensah', 'email': 'ama@example.com', 'message': 'Private message'}, REMOTE_ADDR='203.0.113.7', HTTP_USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36')
		self.assertEqual(response.status_code, 200)
		request_log = AuditLog.objects.filter(event='REQUEST', request_path=reverse('contact')).latest('created_at')
		self.assertEqual(request_log.ip_address, '203.0.113.7')
		self.assertEqual(request_log.browser, 'Chrome')
		self.assertEqual(request_log.operating_system, 'Windows')
		self.assertEqual(request_log.device, 'Desktop')
		self.assertEqual(request_log.route_name, 'contact')
		self.assertEqual(request_log.metadata, {'submitted_fields': ['name', 'email', 'message']})
		self.assertNotIn('Private message', str(request_log.metadata))

	def test_request_audit_redacts_password_reset_path_tokens(self):
		response = self.client.get(reverse('password_reset_confirm', kwargs={'uidb64': 'dXNlcg', 'token': 'sensitive-reset-token'}), REMOTE_ADDR='203.0.113.8')
		self.assertIn(response.status_code, (200, 302))
		request_log = AuditLog.objects.filter(route_name='password_reset_confirm').latest('created_at')
		self.assertEqual(request_log.request_path, '/reset/[redacted]/[redacted]/')
		self.assertNotIn('sensitive-reset-token', request_log.request_path)

	def test_pickup_requires_authentication(self):
		response = self.client.get(reverse('create-pickup'))
		self.assertRedirects(response, f'{reverse("login")}?next={reverse("create-pickup")}')

	def test_otp_is_default_login_and_completes_sign_in(self):
		user = get_user_model().objects.create_user(email='otp-login@example.com', username='otp-login@example.com', password='A-strong-password-2026', is_active=True, is_verified=True)
		response = self.client.get(reverse('login'))
		self.assertContains(response, 'Send login code')
		self.assertContains(response, 'Use your password instead')
		with patch('System.views.secrets.randbelow', return_value=123456), patch('System.views.send_mail'):
			response = self.client.post(reverse('login'), {'mode': 'otp', 'email': user.email})
		self.assertRedirects(response, reverse('verify-otp'))
		self.assertEqual(self.client.session['pending_login_user'], str(user.pk))
		response = self.client.post(reverse('verify-otp'), {'code': '123456'})
		self.assertRedirects(response, reverse('dashboard'))
		self.assertTrue(response.wsgi_request.user.is_authenticated)
		self.assertTrue(AuditLog.objects.filter(user=user, event='LOGIN', metadata={'method': 'otp'}).exists())
		self.assertTrue(AuditLog.objects.filter(event='REQUEST', request_path=reverse('verify-otp'), success=True).exists())

	def test_password_login_remains_available_as_fallback(self):
		user = get_user_model().objects.create_user(email='password-login@example.com', username='password-login@example.com', password='A-strong-password-2026', is_active=True, is_verified=True)
		response = self.client.post(reverse('login'), {'mode': 'password', 'username': user.email, 'password': 'A-strong-password-2026'})
		self.assertRedirects(response, reverse('dashboard'))
		self.assertTrue(response.wsgi_request.user.is_authenticated)
		self.assertTrue(AuditLog.objects.filter(user=user, event='LOGIN', metadata={'method': 'password'}).exists())

	def test_failed_password_login_is_audited_without_credentials(self):
		user = get_user_model().objects.create_user(email='failed-login@example.com', username='failed-login@example.com', password='A-strong-password-2026', is_active=True, is_verified=True)
		response = self.client.post(reverse('login'), {'mode': 'password', 'username': user.email, 'password': 'incorrect-secret'})
		self.assertEqual(response.status_code, 200)
		failure = AuditLog.objects.get(event='LOGIN_FAILED')
		self.assertFalse(failure.success)
		self.assertIsNone(failure.user)
		self.assertEqual(failure.metadata, {'method': 'password'})
		self.assertNotIn('incorrect-secret', str(failure.metadata))
		request_log = AuditLog.objects.get(event='REQUEST', request_path=reverse('login'))
		self.assertFalse(request_log.success)

	def test_admin_edits_and_deletions_are_audited(self):
		admin_user = get_user_model().objects.create_superuser(email='audit-admin@example.com', username='audit-admin@example.com', password='A-strong-password-2026')
		pickup = Pickup.objects.create(customer=admin_user, address='Accra', pickup_date='2026-10-01', time_window='10:00', waste_type='GENERAL')
		request = RequestFactory().post(f'/admin/System/pickup/{pickup.pk}/change/')
		request.user = admin_user
		request.resolver_match = SimpleNamespace(view_name='admin:System_pickup_change')
		pickup_admin = PickupAdmin(Pickup, AdminSite())
		pickup_admin.save_model(request, pickup, SimpleNamespace(changed_data=['status', 'password']), change=True)
		update_event = AuditLog.objects.get(event='ADMIN_OBJECT_UPDATED')
		self.assertEqual(update_event.object_uuid, pickup.pk)
		self.assertEqual(update_event.metadata, {'changed_fields': ['status']})
		pickup_admin.delete_queryset(request, Pickup.objects.filter(pk=pickup.pk))
		delete_event = AuditLog.objects.get(event='ADMIN_OBJECT_DELETED')
		self.assertEqual(delete_event.object_uuid, pickup.pk)
		self.assertFalse(Pickup.objects.filter(pk=pickup.pk).exists())

	def test_pickup_is_owned_by_authenticated_customer(self):
		user = get_user_model().objects.create_user(email='customer@example.com', username='customer@example.com', password='A-strong-password-2026', is_active=True, is_verified=True)
		self.client.force_login(user)
		response = self.client.post(reverse('create-pickup'), {'address': 'Pokuase', 'location_lat': '5.554500', 'location_lng': '-0.190200', 'pickup_date': '2026-10-01', 'time_window': '10:00 - 12:00', 'waste_type': 'RECYCLABLE', 'estimated_weight_kg': '2.5', 'notes': ''})
		self.assertRedirects(response, reverse('dashboard'))
		pickup = Pickup.objects.get()
		self.assertEqual(pickup.customer, user)
		self.assertEqual(str(pickup.location_latitude), '5.554500')
		self.assertEqual(str(pickup.location_longitude), '-0.190200')

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
		customer = get_user_model().objects.create_user(email='route-customer@example.com', username='route-customer@example.com', password='A-strong-password-2026')
		Pickup.objects.create(customer=customer, collector=collector, address='Customer entered address', pickup_date='2026-10-01', time_window='10:00', waste_type='GENERAL', status=Pickup.Status.ASSIGNED, location_latitude='5.554500', location_longitude='-0.190200')
		self.client.force_login(collector)
		response = self.client.get(reverse('collector-dashboard'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'destination=5.554500,-0.190200')
		self.assertNotContains(response, 'origin=')

	def test_pending_collector_can_see_approval_status_instead_of_forbidden(self):
		collector = get_user_model().objects.create_user(email='pending-dashboard@example.com', username='pending-dashboard@example.com', password='A-strong-password-2026', role='COLLECTOR', is_active=True, is_verified=True)
		CollectorProfile.objects.create(user=collector, is_verified=False, is_active=True)
		self.client.force_login(collector)
		response = self.client.get(reverse('dashboard'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'awaiting approval')

	def test_password_login_switch_preserves_typed_email(self):
		response = self.client.get(reverse('login'), {'mode': 'password', 'email': 'admin12@gmail.com'})
		self.assertContains(response, 'value="admin12@gmail.com"')

	def test_collector_can_claim_an_unassigned_pickup_once(self):
		customer = get_user_model().objects.create_user(email='claim-customer@example.com', username='claim-customer@example.com', password='A-strong-password-2026')
		collector = get_user_model().objects.create_user(email='claim-collector@example.com', username='claim-collector@example.com', password='A-strong-password-2026', role='COLLECTOR')
		CollectorProfile.objects.create(user=collector, is_verified=True, is_active=True)
		pickup = Pickup.objects.create(customer=customer, address='Tema', pickup_date='2026-10-01', time_window='10:00 - 12:00', waste_type='RECYCLABLE')
		self.client.force_login(collector)
		self.assertRedirects(self.client.post(reverse('claim-pickup', args=[pickup.id])), reverse('collector-dashboard'))
		pickup.refresh_from_db()
		self.assertEqual(pickup.collector, collector)
		self.assertEqual(pickup.status, Pickup.Status.ASSIGNED)
		other_collector = get_user_model().objects.create_user(email='second-claim-collector@example.com', username='second-claim-collector@example.com', password='A-strong-password-2026', role='COLLECTOR')
		CollectorProfile.objects.create(user=other_collector, is_verified=True, is_active=True)
		self.client.force_login(other_collector)
		self.assertRedirects(self.client.post(reverse('claim-pickup', args=[pickup.id])), reverse('collector-dashboard'))
		pickup.refresh_from_db()
		self.assertEqual(pickup.collector, collector)

	def test_admin_dashboard_shows_operations_and_downloads_report(self):
		customer = get_user_model().objects.create_user(email='report-customer@example.com', username='report-customer@example.com', password='A-strong-password-2026')
		Pickup.objects.create(customer=customer, address='Accra', pickup_date='2026-10-01', time_window='10:00 - 12:00', waste_type='GENERAL')
		admin = get_user_model().objects.create_superuser(email='report-admin@example.com', username='report-admin@example.com', password='A-strong-password-2026')
		self.client.force_login(admin)
		self.assertEqual(self.client.get(reverse('admin-dashboard')).status_code, 200)
		response = self.client.get(reverse('download-pickup-report'))
		self.assertEqual(response.status_code, 200)
		self.assertIn(b'Accra', response.content)

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
		failure = AuditLog.objects.get(event='ACCOUNT_VERIFICATION_FAILED')
		self.assertFalse(failure.success)
		self.assertEqual(failure.user, user)
		self.assertNotIn('123456', str(failure.metadata))
		request_log = AuditLog.objects.get(event='REQUEST', request_path=reverse('verify-otp'))
		self.assertFalse(request_log.success)

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
