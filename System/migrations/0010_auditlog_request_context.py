from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('System', '0009_notification_pushed_at_notification_sms_sent_at_and_more'),
	]

	operations = [
		migrations.AddField(
			model_name='auditlog',
			name='browser',
			field=models.CharField(blank=True, max_length=80),
		),
		migrations.AddField(
			model_name='auditlog',
			name='device',
			field=models.CharField(blank=True, max_length=40),
		),
		migrations.AddField(
			model_name='auditlog',
			name='operating_system',
			field=models.CharField(blank=True, max_length=80),
		),
		migrations.AddField(
			model_name='auditlog',
			name='route_name',
			field=models.CharField(blank=True, max_length=200),
		),
	]