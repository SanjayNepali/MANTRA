# apps/notifications/forms.py

from django import forms
from .models import NotificationPreference

class NotificationPreferenceForm(forms.ModelForm):
    """Form for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        exclude = ['user']
        widgets = {
            'email_follows': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_likes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_comments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_messages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_events': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_system': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_follows': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_likes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_comments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_messages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_events': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_system': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'quiet_hours_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'quiet_hours_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'quiet_hours_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }