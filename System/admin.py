from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (AuditLog, CollectorProfile, ContactInquiry, CustomerProfile, Notification, OTPVerification, Payment, Pickup, RecyclingRecord, Reward, RewardRedemption, RewardTransaction, RewardWallet, Subscription, SubscriptionPlan, User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
	list_display = ('email', 'role', 'is_verified', 'is_active', 'date_joined')
	list_filter = ('role', 'is_verified', 'is_active')
	search_fields = ('email', 'first_name', 'last_name', 'phone')
	ordering = ('email',)
	fieldsets = DjangoUserAdmin.fieldsets + (
		('EcoBin access', {'fields': ('role', 'phone', 'is_verified')}),
	)
	add_fieldsets = DjangoUserAdmin.add_fieldsets + (
		('EcoBin access', {'fields': ('email', 'role', 'phone', 'is_verified')}),
	)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'customer_type', 'area')
	search_fields = ('user__email', 'user__first_name', 'user__last_name', 'area')


@admin.register(CollectorProfile)
class CollectorProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'is_verified', 'is_active', 'service_area')
	list_filter = ('is_verified', 'is_active', 'service_area')
	search_fields = ('user__email', 'user__first_name', 'user__last_name', 'service_area')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
	list_display = ('name', 'price', 'reward_multiplier', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name', 'description')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
	list_display = ('customer', 'plan', 'status', 'starts_on', 'renews_on')
	list_filter = ('status', 'plan')
	search_fields = ('customer__email', 'customer__first_name', 'customer__last_name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ('customer', 'amount', 'currency', 'provider', 'status', 'verified_at')
	list_filter = ('provider', 'status', 'currency')
	search_fields = ('customer__email', 'provider_reference')


@admin.register(Pickup)
class PickupAdmin(admin.ModelAdmin):
	list_display = ('customer', 'collector', 'pickup_date', 'waste_type', 'status')
	list_filter = ('status', 'waste_type', 'pickup_date')
	search_fields = ('customer__email', 'collector__email', 'address')


@admin.register(RecyclingRecord)
class RecyclingRecordAdmin(admin.ModelAdmin):
	list_display = ('customer', 'collector', 'material_type', 'weight_kg', 'verification_status', 'verified_at')
	list_filter = ('verification_status', 'material_type')
	search_fields = ('customer__email', 'collector__email', 'material_type')


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'points_cost', 'availability', 'is_active')
	list_filter = ('category', 'is_active')
	search_fields = ('name', 'description', 'partner_name')


@admin.register(RewardWallet, RewardTransaction, RewardRedemption, Notification, OTPVerification)
class OperationsAdmin(admin.ModelAdmin):
	list_display = ('__str__', 'created_at', 'updated_at')
	search_fields = ('id',)


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
	list_display = ('created_at', 'name', 'email', 'organization', 'status')
	list_filter = ('status', 'created_at')
	search_fields = ('name', 'email', 'organization', 'message')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
	list_display = ('created_at', 'event', 'user', 'success', 'severity', 'request_path')
	list_filter = ('event', 'success', 'severity', 'created_at')
	search_fields = ('event', 'action', 'ip_address', 'request_path', 'description')
	readonly_fields = [field.name for field in AuditLog._meta.fields]
