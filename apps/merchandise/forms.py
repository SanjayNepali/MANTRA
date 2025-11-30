# apps/merchandise/forms.py

from django import forms
from .models import Merchandise, MerchandiseOrder, MerchandiseCategory

class MerchandiseCreateForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=MerchandiseCategory.objects.all(),
        empty_label="Select a category",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    class Meta:
        model = Merchandise
        fields = ['name', 'description', 'category', 'price', 'discount_percentage',
                 'subscriber_discount', 'stock_quantity', 'primary_image',
                 'is_exclusive', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your product...'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'value': '0'}),
            'subscriber_discount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'value': '10'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'value': '1'}),
            'primary_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_exclusive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class OrderForm(forms.ModelForm):
    class Meta:
        model = MerchandiseOrder
        fields = ['shipping_address', 'shipping_city', 'shipping_country',
                 'shipping_postal_code', 'contact_number', 'payment_method']
        widgets = {
            'shipping_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }