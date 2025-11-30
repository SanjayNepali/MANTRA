# apps/events/forms.py

from django import forms
from django.conf import settings
from django.utils import timezone
from .models import Event, EventBooking


class EventCreateForm(forms.ModelForm):
    """Form for creating new events"""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'venue', 'address', 
            'city', 'country', 'is_online', 'online_link', 'start_datetime',
            'duration_hours', 'total_tickets', 'ticket_price', 
            'early_bird_price', 'early_bird_deadline', 'cover_image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event Title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe your event...'
            }),
            'event_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Venue Name'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'is_online': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'online_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'duration_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.5',
                'step': '0.5'
            }),
            'total_tickets': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'ticket_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'early_bird_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'early_bird_deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields optional
        self.fields['online_link'].required = False
        self.fields['early_bird_price'].required = False
        self.fields['early_bird_deadline'].required = False
        
        # Set input formats for datetime fields
        self.fields['start_datetime'].input_formats = ['%Y-%m-%dT%H:%M']
        if 'early_bird_deadline' in self.fields:
            self.fields['early_bird_deadline'].input_formats = ['%Y-%m-%dT%H:%M']
    
    def clean_start_datetime(self):
        start_datetime = self.cleaned_data.get('start_datetime')
        if start_datetime and start_datetime <= timezone.now():
            raise forms.ValidationError('Event date must be in the future.')
        return start_datetime
    
    def clean_early_bird_deadline(self):
        early_bird_deadline = self.cleaned_data.get('early_bird_deadline')
        start_datetime = self.cleaned_data.get('start_datetime')
        
        if early_bird_deadline:
            if early_bird_deadline <= timezone.now():
                raise forms.ValidationError('Early bird deadline must be in the future.')
            if start_datetime and early_bird_deadline >= start_datetime:
                raise forms.ValidationError('Early bird deadline must be before event start date.')
        
        return early_bird_deadline
    
    def clean(self):
        cleaned_data = super().clean()
        early_bird_price = cleaned_data.get('early_bird_price')
        ticket_price = cleaned_data.get('ticket_price')
        
        if early_bird_price and ticket_price:
            if early_bird_price >= ticket_price:
                raise forms.ValidationError({
                    'early_bird_price': 'Early bird price must be less than regular ticket price.'
                })
        
        return cleaned_data


class EventEditForm(forms.ModelForm):
    """Form for editing existing events"""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'venue', 'address', 
            'city', 'country', 'is_online', 'online_link', 'start_datetime',
            'duration_hours', 'total_tickets', 'ticket_price', 
            'early_bird_price', 'early_bird_deadline', 'cover_image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event Title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe your event...'
            }),
            'event_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Venue Name'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'is_online': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'online_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'duration_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.5',
                'step': '0.5'
            }),
            'total_tickets': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'ticket_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'early_bird_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'early_bird_deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields optional
        self.fields['online_link'].required = False
        self.fields['early_bird_price'].required = False
        self.fields['early_bird_deadline'].required = False
        self.fields['cover_image'].required = False
        
        # Set input formats for datetime fields
        self.fields['start_datetime'].input_formats = ['%Y-%m-%dT%H:%M']
        if 'early_bird_deadline' in self.fields:
            self.fields['early_bird_deadline'].input_formats = ['%Y-%m-%dT%H:%M']
        
        # If event has already started, don't allow changing certain fields
        if self.instance and self.instance.pk:
            if hasattr(self.instance, 'start_datetime'):
                if self.instance.start_datetime <= timezone.now():
                    # Event has started, make some fields read-only
                    self.fields['start_datetime'].disabled = True
                    self.fields['total_tickets'].disabled = True
    
    def clean_start_datetime(self):
        start_datetime = self.cleaned_data.get('start_datetime')
        
        # If editing, allow past dates only if event hasn't changed
        if self.instance and self.instance.pk:
            if self.instance.start_datetime <= timezone.now():
                # Event has already started, keep original date
                return self.instance.start_datetime
        
        if start_datetime and start_datetime <= timezone.now():
            raise forms.ValidationError('Event date must be in the future.')
        
        return start_datetime


class EventBookingForm(forms.Form):
    """Form for booking event tickets"""
    
    ticket_quantity = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        label='Number of Tickets',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '10'
        })
    )
    
    payment_method = forms.ChoiceField(
        label='Payment Method',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Get payment methods from settings
        try:
            payment_methods = settings.MANTRA_SETTINGS.get('PAYMENT_METHODS', [
                ('online', 'Online Payment'),
                ('esewa', 'eSewa'),
                ('khalti', 'Khalti'),
            ])
            self.fields['payment_method'].choices = payment_methods
        except AttributeError:
            self.fields['payment_method'].choices = [
                ('online', 'Online Payment'),
                ('esewa', 'eSewa'),
                ('khalti', 'Khalti'),
            ]
        
        # If event is provided, adjust max quantity based on available tickets
        if event and hasattr(event, 'available_tickets'):
            max_tickets = min(10, event.available_tickets)
            self.fields['ticket_quantity'].max_value = max_tickets
            self.fields['ticket_quantity'].widget.attrs['max'] = str(max_tickets)
    
    def clean_ticket_quantity(self):
        quantity = self.cleaned_data.get('ticket_quantity')
        if quantity < 1:
            raise forms.ValidationError('You must book at least 1 ticket.')
        if quantity > 10:
            raise forms.ValidationError('You cannot book more than 10 tickets at once.')
        return quantity


class EventCancelForm(forms.Form):
    """Form for canceling an event"""
    
    cancellation_reason = forms.CharField(
        label='Reason for Cancellation',
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Please provide a reason for canceling this event...'
        })
    )
    
    notify_attendees = forms.BooleanField(
        label='Notify all attendees via email',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_cancellation_reason(self):
        reason = self.cleaned_data.get('cancellation_reason', '').strip()
        if len(reason) < 10:
            raise forms.ValidationError('Please provide a detailed reason (at least 10 characters).')
        return reason