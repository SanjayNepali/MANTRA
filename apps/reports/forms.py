# apps/reports/forms.py

from django import forms
from .models import Report

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['report_type', 'reason', 'description', 'target_object_id', 'screenshot']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'screenshot': forms.FileInput(attrs={'class': 'form-control'}),
        }