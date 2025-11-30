# apps/celebrities/forms.py

from django import forms
from django.conf import settings
from .models import CelebrityProfile, KYCDocument, Subscription

class CelebrityProfileForm(forms.ModelForm):
    """Form for celebrity profile setup"""

    class Meta:
        model = CelebrityProfile
        fields = [
            'stage_name', 'categories', 'bio_extended',
            'default_subscription_price', 'subscription_description',
            'social_links', 'achievements'
        ]
        widgets = {
            'stage_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your stage/professional name'
            }),
            'bio_extended': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Tell your fans about yourself...'
            }),
            'default_subscription_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': 'Monthly subscription fee'
            }),
            'subscription_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What subscribers will get...'
            }),
        }


class KYCUploadForm(forms.ModelForm):
    """Form for KYC document upload with additional fields"""
    
    document_type = forms.ChoiceField(
        choices=[
            ('passport', 'Passport'),
            ('driving_license', 'Driving License'),
            ('national_id', 'National ID'),
            ('voter_id', 'Voter ID'),
            ('proof_of_address', 'Proof of Address'),
            ('professional_certificate', 'Professional Certificate'),
            ('other', 'Other'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    document_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Document number (optional)'
        })
    )

    class Meta:
        model = KYCDocument
        fields = ['document_type', 'document_file']
        widgets = {
            'document_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf'
            }),
        }
        
class SubscriptionSettingsForm(forms.ModelForm):
    """Form for subscription settings"""

    class Meta:
        model = CelebrityProfile
        fields = ['default_subscription_price', 'subscription_description']
        widgets = {
            'default_subscription_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01'
            }),
            'subscription_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe what subscribers will get access to...'
            }),
        }


class PaymentMethodForm(forms.Form):
    """Form for payment method setup"""
    
    payment_method = forms.ChoiceField(
        choices=settings.MANTRA_SETTINGS['PAYMENT_METHODS'],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    qr_code = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text='Upload QR code image for payment'
    )