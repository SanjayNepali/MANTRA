# apps/merchandise/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
import uuid
from decimal import Decimal, ROUND_HALF_UP
class MerchandiseCategory(models.Model):
    """Category for merchandise"""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Merchandise Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Merchandise(models.Model):
    """Merchandise model"""

    STATUS_CHOICES = (
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    celebrity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='merchandise'
    )
    category = models.ForeignKey(
        MerchandiseCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True)
    description = models.TextField()

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.IntegerField(default=0)
    subscriber_discount = models.IntegerField(default=10)

    stock_quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    primary_image = models.ImageField(upload_to='merchandise/')
    gallery_images = models.JSONField(default=list)
    specifications = models.JSONField(default=dict)

    is_featured = models.BooleanField(default=False)
    is_exclusive = models.BooleanField(default=False)

    total_sold = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['celebrity', 'status']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return f"{self.name} - {self.celebrity.username}"

    def save(self, *args, **kwargs):
        """Safe save: prevent F() comparison errors"""
        from django.db.models.expressions import Expression

        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.celebrity.username}")

        # Avoid comparing F() or CombinedExpression types
        if not isinstance(self.stock_quantity, Expression):
            if self.stock_quantity == 0:
                self.status = 'out_of_stock'
            elif self.stock_quantity > 0 and self.status == 'out_of_stock':
                self.status = 'available'

        super().save(*args, **kwargs)


class MerchandiseOrder(models.Model):
    """Order model for merchandise"""
    
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='merchandise_orders'
    )
    
    # Order details
    order_number = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Shipping
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    contact_number = models.CharField(max_length=20)
    
    # Payment
    payment_method = models.CharField(max_length=20)
    payment_status = models.CharField(max_length=20, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Status
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    tracking_number = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.username}"
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        prefix = 'ORD'
        number = f"{prefix}{timezone.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
        while MerchandiseOrder.objects.filter(order_number=number).exists():
            number = f"{prefix}{timezone.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
        return number
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Order item model"""
    
    order = models.ForeignKey(
        MerchandiseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    merchandise = models.ForeignKey(
        Merchandise,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ('order', 'merchandise')
    
    def __str__(self):
        return f"{self.quantity}x {self.merchandise.name}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price
        super().save(*args, **kwargs)

