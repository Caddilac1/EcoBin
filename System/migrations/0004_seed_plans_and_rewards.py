from decimal import Decimal

from django.db import migrations


def seed_catalogue(apps, schema_editor):
	Plan = apps.get_model('System', 'SubscriptionPlan')
	Reward = apps.get_model('System', 'Reward')
	Plan.objects.get_or_create(name='Basic', defaults={'price': Decimal('40.00'), 'description': 'Shared-route pickup twice weekly, standard separation bags, and base reward rate.', 'reward_multiplier': Decimal('1.00')})
	Plan.objects.get_or_create(name='Standard', defaults={'price': Decimal('75.00'), 'description': 'Dedicated pickup window, free starter bin set, and 1.5x reward rate.', 'reward_multiplier': Decimal('1.50')})
	Plan.objects.get_or_create(name='Business', defaults={'price': None, 'description': 'Daily pickup for restaurants and schools, compliance reporting, priority support, and bulk rewards.', 'reward_multiplier': Decimal('2.00')})
	Reward.objects.get_or_create(name='Airtime reward', defaults={'description': 'Redeem points for airtime through an available reward partner.', 'category': 'Airtime', 'points_cost': 100, 'availability': 100})
	Reward.objects.get_or_create(name='Retail voucher', defaults={'description': 'Redeem points for a retail voucher through an available reward partner.', 'category': 'Voucher', 'points_cost': 250, 'availability': 50})
	Reward.objects.get_or_create(name='Bill discount', defaults={'description': 'Redeem points for a bill discount through an available reward partner.', 'category': 'Bill discount', 'points_cost': 500, 'availability': 25})


def reverse_catalogue(apps, schema_editor):
	apps.get_model('System', 'SubscriptionPlan').objects.filter(name__in=['Basic', 'Standard', 'Business']).delete()
	apps.get_model('System', 'Reward').objects.filter(name__in=['Airtime reward', 'Retail voucher', 'Bill discount']).delete()


class Migration(migrations.Migration):
	dependencies = [('System', '0003_notification_emailed_at_payment')]
	operations = [migrations.RunPython(seed_catalogue, reverse_catalogue)]