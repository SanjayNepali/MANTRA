# apps/messaging/forms.py

from django import forms
from .models import Message, MessageRequest

class MessageForm(forms.ModelForm):
    """Form for sending messages"""
    
    class Meta:
        model = Message
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Type your message...',
                'maxlength': 1000
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf'
            })
        }


class MessageRequestForm(forms.ModelForm):
    """Form for sending message request"""
    
    class Meta:
        model = MessageRequest
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Introduce yourself and explain why you want to connect...',
                'maxlength': 500
            })
        }