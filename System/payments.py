import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


def verify_paystack(reference):
	secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
	if not secret:
		return None
	request = Request(f'https://api.paystack.co/transaction/verify/{reference}', headers={'Authorization': f'Bearer {secret}', 'Content-Type': 'application/json'})
	try:
		with urlopen(request, timeout=10) as response:
			payload = json.loads(response.read().decode('utf-8'))
		return payload.get('data') if payload.get('status') else None
	except (HTTPError, URLError, TimeoutError, ValueError):
		return None