from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import ContactInquiry, CollectorProfile, CustomerProfile, Pickup, RecyclingRecord, User


class OTPLoginForm(forms.Form):
    email = forms.EmailField(label='Email address')


class PasswordLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email address')


class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(choices=((User.Role.CUSTOMER, 'Customer'), (User.Role.COLLECTOR, 'Collector')), initial=User.Role.CUSTOMER, required=False)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    customer_type = forms.ChoiceField(choices=CustomerProfile.CustomerType.choices, required=False)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'data-location-address': 'true'}))
    area = forms.CharField(max_length=100, initial='Greater Accra')
    organization_name = forms.CharField(max_length=160, required=False)
    location_lat = forms.DecimalField(required=False, widget=forms.HiddenInput())
    location_lng = forms.DecimalField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'role', 'email', 'phone', 'customer_type', 'organization_name', 'address', 'area', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data.get('role', self.initial.get('role')) == User.Role.COLLECTOR:
            self.fields['address'].required = False
            self.fields['customer_type'].required = False
            self.fields['organization_name'].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.role = self.cleaned_data['role']
        user.is_active = False
        if commit:
            user.save()
            if user.role == User.Role.COLLECTOR:
                CollectorProfile.objects.create(user=user, service_area=self.cleaned_data['area'])
            else:
                CustomerProfile.objects.create(user=user, customer_type=self.cleaned_data['customer_type'], organization_name=self.cleaned_data['organization_name'], address=self.cleaned_data['address'], area=self.cleaned_data['area'])
        return user

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['role'] = cleaned_data.get('role') or User.Role.CUSTOMER
        address = cleaned_data.get('address', '').strip()
        latitude = cleaned_data.get('location_lat')
        longitude = cleaned_data.get('location_lng')
        if cleaned_data.get('role') == User.Role.COLLECTOR:
            return cleaned_data
        if not address and (latitude is None or longitude is None):
            self.add_error('address', 'Enter an address or use your current location.')
        if not address and latitude is not None and longitude is not None:
            cleaned_data['address'] = f'GPS location ({latitude}, {longitude})'
        return cleaned_data


class PickupForm(forms.ModelForm):
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'data-location-address': 'true'}))
    location_lat = forms.DecimalField(required=False, widget=forms.HiddenInput())
    location_lng = forms.DecimalField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Pickup
        fields = ('address', 'pickup_date', 'time_window', 'waste_type', 'estimated_weight_kg', 'notes')
        widgets = {'pickup_date': forms.DateInput(attrs={'type': 'date'}), 'notes': forms.Textarea(attrs={'rows': 3})}

    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data.get('address', '').strip()
        latitude = cleaned_data.get('location_lat')
        longitude = cleaned_data.get('location_lng')
        if not address and (latitude is None or longitude is None):
            self.add_error('address', 'Enter an address or use your current location.')
        if not address and latitude is not None and longitude is not None:
            cleaned_data['address'] = f'GPS location ({latitude}, {longitude})'
        return cleaned_data


class RecyclingRecordForm(forms.ModelForm):
    class Meta:
        model = RecyclingRecord
        fields = ('material_type', 'weight_kg')


class ContactInquiryForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ('name', 'email', 'organization', 'message')
        widgets = {'message': forms.Textarea(attrs={'rows': 5})}