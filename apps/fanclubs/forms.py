# apps/fanclubs/forms.py

from django import forms
from .models import FanClub, FanClubPost, FanClubEvent

class FanClubCreateForm(forms.ModelForm):
    """Form for creating fanclub"""
    
    class Meta:
        model = FanClub
        fields = ['name', 'description', 'club_type', 'is_private', 
                 'requires_approval', 'cover_image', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Fanclub name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your fanclub...'
            }),
            'club_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_approval': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'icon': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }


class FanClubPostForm(forms.ModelForm):
    """Form for posting in fanclub"""
    
    class Meta:
        model = FanClubPost
        fields = ['content', 'image', 'is_announcement']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share with the fanclub...'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_announcement': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class FanClubEventForm(forms.ModelForm):
    """Form for creating fanclub events"""
    
    class Meta:
        model = FanClubEvent
        fields = ['title', 'description', 'event_date', 'location', 
                 'is_online', 'meeting_link', 'max_participants']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'event_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'is_online': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control'}),
        }