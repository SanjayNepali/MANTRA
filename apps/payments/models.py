# apps/payments/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import hashlib
import hmac

class PaymentTransaction(models.Model):
    """Payment transaction model"""
    
    PAYMENT_TYPES = (
        ('subscription', 'Subscription'),
        ('event', 'Event Booking'),
        ('merchandise', 'Merchandise'),
        ('donation', 'Donation'),
    )
    
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    payment_method = models.CharField(max_length=20)
    
    # Transaction info
    transaction_id = models.CharField(max_length=100, unique=True)
    reference_id = models.CharField(max_length=100, blank=True)  # External reference
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Related object
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.CharField(max_length=100, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - {self.user.username} - ${self.amount}"
    
    def generate_transaction_id(self):
        """Generate unique transaction ID"""
        timestamp = str(timezone.now().timestamp())
        user_id = str(self.user.id)
        data = f"{timestamp}{user_id}{self.amount}"
        return hashlib.sha256(data.encode()).hexdigest()[:20].upper()
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
    
    def complete_payment(self):
        """Mark payment as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Process based on payment type
        self.process_payment()
    
    def process_payment(self):
        """Process payment based on type"""
        if self.payment_type == 'subscription':
            self.process_subscription_payment()
        elif self.payment_type == 'event':
            self.process_event_payment()
        elif self.payment_type == 'merchandise':
            self.process_merchandise_payment()
    
    def process_subscription_payment(self):
        """Process subscription payment"""
        from apps.celebrities.models import Subscription
        try:
            subscription = Subscription.objects.get(id=self.related_object_id)
            subscription.payment_status = 'completed'
            subscription.save()
        except Subscription.DoesNotExist:
            pass
    
    def process_event_payment(self):
        """Process event booking payment"""
        from apps.events.models import EventBooking
        try:
            booking = EventBooking.objects.get(id=self.related_object_id)
            booking.confirm_booking()
        except EventBooking.DoesNotExist:
            pass
    
    def process_merchandise_payment(self):
        """Process merchandise order payment"""
        from apps.merchandise.models import MerchandiseOrder
        try:
            order = MerchandiseOrder.objects.get(id=self.related_object_id)
            order.payment_status = 'completed'
            order.order_status = 'processing'
            order.save()
        except MerchandiseOrder.DoesNotExist:
            pass


class PaymentMethod(models.Model):
    """User payment methods"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    method_type = models.CharField(max_length=20)
    account_number = models.CharField(max_length=100)
    account_name = models.CharField(max_length=200)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.method_type}"


class PaymentDispute(models.Model):
    """Payment dispute/issue tracking"""
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    
    reason = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    resolution = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Dispute for {self.transaction.transaction_id}"
class PaymentSimulation(models.Model):
    """Simulated payment transaction"""
    
    PAYMENT_TYPES = (
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
    )
    
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='payments')
    celebrity = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='received_payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    qr_code_scanned = models.BooleanField(default=False)
    
    payment_for = models.CharField(max_length=50)  # 'merchandise', 'event', 'subscription'
    reference_id = models.CharField(max_length=100)  # ID of the item being paid for
    
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def simulate_payment(self):
        """Simulate payment completion"""
        import random
        import string
        from datetime import timedelta
        
        # Simulate processing time
        self.payment_status = 'processing'
        self.save()
        
        # 90% success rate
        success = random.random() > 0.1
        
        if success:
            self.payment_status = 'success'
            self.transaction_id = 'SIM' + ''.join(random.choices(string.digits, k=10))
            self.completed_at = timezone.now() + timedelta(seconds=random.randint(1, 5))
            self.qr_code_scanned = True
        else:
            self.payment_status = 'failed'
            self.completed_at = timezone.now()
        
        self.save()
        return success