
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
	path('', views.home, name='home'),
	path('about/', views.about, name='about'),
	path('services/', views.services, name='services'),
	path('how-it-works/', views.how_it_works, name='how-it-works'),
	path('faq/', views.faq, name='faq'),
	path('contact/', views.contact, name='contact'),
	path('dashboard/', views.dashboard, name='dashboard'),
	path('dashboard/pickups/', views.customer_pickups, name='customer-pickups'),
	path('dashboard/subscription/', views.customer_subscription, name='customer-subscription'),
	path('dashboard/profile/', views.customer_profile, name='customer-profile'),
	path('notifications/', views.notifications, name='notifications'),
	path('pricing/', views.pricing, name='pricing'),
	path('pricing/<slug:plan_slug>/', views.plan_detail, name='plan-detail'),
	path('subscriptions/<uuid:plan_id>/subscribe/', views.subscribe, name='subscribe'),
	path('payments/<uuid:payment_id>/verify/', views.verify_payment, name='verify-payment'),
	path('rewards/', views.rewards, name='rewards'),
	path('rewards/<uuid:reward_id>/redeem/', views.redeem, name='redeem-reward'),
	path('pickups/new/', views.create_pickup, name='create-pickup'),
	path('collector/', views.collector_dashboard, name='collector-dashboard'),
	path('collector/pickups/<uuid:pickup_id>/status/', views.update_pickup_status, name='update-pickup-status'),
	path('collector/pickups/<uuid:pickup_id>/recycling/', views.record_recycling, name='record-recycling'),
	path('operations/', views.admin_dashboard, name='admin-dashboard'),
	path('operations/recycling/<uuid:record_id>/verify/', views.verify_recycling, name='verify-recycling'),
	path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
	path('logout/', auth_views.LogoutView.as_view(), name='logout'),
	path('register/', views.register, name='register'),
	path('verify-otp/', views.verify_otp, name='verify-otp'),
	path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html', email_template_name='registration/password_reset_email.txt'), name='password_reset'),
	path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
	path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
	path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]