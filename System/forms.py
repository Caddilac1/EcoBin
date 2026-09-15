from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import ContactInquiry, CustomerProfile, Pickup, RecyclingRecord


class RegistrationForm(UserCreationForm):
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    customer_type = forms.ChoiceField(choices=CustomerProfile.CustomerType.choices)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    area = forms.CharField(max_length=100, initial='Greater Accra')
    organization_name = forms.CharField(max_length=160, required=False)

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email', 'phone', 'customer_type', 'organization_name', 'address', 'area', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.is_active = False
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user, customer_type=self.cleaned_data['customer_type'], organization_name=self.cleaned_data['organization_name'], address=self.cleaned_data['address'], area=self.cleaned_data['area'])
        return user


class PickupForm(forms.ModelForm):
    class Meta:
        model = Pickup
        fields = ('address', 'pickup_date', 'time_window', 'waste_type', 'estimated_weight_kg', 'notes')
        widgets = {'pickup_date': forms.DateInput(attrs={'type': 'date'}), 'notes': forms.Textarea(attrs={'rows': 3})}


class RecyclingRecordForm(forms.ModelForm):
    class Meta:
        model = RecyclingRecord
        fields = ('material_type', 'weight_kg')


class ContactInquiryForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ('name', 'email', 'organization', 'message')
        widgets = {'message': forms.Textarea(attrs={'rows': 5})}