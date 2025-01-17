from django.contrib.auth.forms import UserCreationForm
import random
from django import forms
from .models import Booking,Category, CustomUser

class BookingForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), empty_label=None)

    class Meta:
        model = Booking
        fields = ['number_of_tickets', 'category']
        widgets = {
            'number_of_tickets': forms.NumberInput(attrs={'min': 0})
        }

# blogapp/forms.py

from django import forms
from allauth.account.forms import SignupForm
from .models import CustomUser
from django import forms
# blogapp/forms.py
from django import forms

class ContactForm(forms.Form):
    email = forms.EmailField(label='Your Email', max_length=100, required=True)
    phone = forms.CharField(label='Your Phone_number', max_length=11, required=True)


class TicketCodeForm(forms.Form):
    code = forms.CharField(max_length=10, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter your ticket code'}))

class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=True)

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email address is already registered.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            new_usernames = []
            for _ in range(2):  # Generate 2 alternative usernames if original is taken
                random_number = str(random.randint(10000, 99999))
                new_username = username + random_number
                if not CustomUser.objects.filter(username=new_username).exists():
                    new_usernames.append(new_username)
            if new_usernames:
                error_message = f'Username is already taken. Available options: {", ".join(new_usernames)}'
            else:
                error_message = 'Username is already taken.'
            raise forms.ValidationError(error_message)
        return username

class CookiesConsentForm(forms.Form):
    consent_given = forms.BooleanField(label='I consent to the use of cookies', required=False)
