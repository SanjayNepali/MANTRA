# apps/payments/utils.py

"""
Payment utilities for MANTRA
Handles payment processing, QR codes, bill generation, and revenue tracking
"""

import random
import string
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum


def simulate_payment(transaction):
    """Simulate payment processing"""
    # In real implementation, integrate with eSewa/Khalti API
    # For now, simulate with 90% success rate

    success = random.random() > 0.1

    if success:
        # Generate fake reference ID
        transaction.reference_id = f"REF{random.randint(100000, 999999)}"
        transaction.save()

    return success

def validate_payment_signature(data, signature):
    """Validate payment webhook signature"""
    # In real implementation, validate with payment provider's signature
    return True


def generate_bill_number():
    """Generate unique bill number"""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"MANTRA-{timestamp}-{random_suffix}"


def calculate_payment_breakdown(amount, payment_type='merchandise'):
    """
    Calculate payment breakdown including celebrity share and platform fee

    Platform fee structure:
    - Merchandise: 10%
    - Events: 15%
    - Subscriptions: 20%
    """
    amount = Decimal(str(amount))

    fee_structure = {
        'merchandise': Decimal('0.10'),
        'event': Decimal('0.15'),
        'subscription': Decimal('0.20'),
    }

    platform_fee_percentage = fee_structure.get(payment_type, Decimal('0.10'))
    platform_fee = amount * platform_fee_percentage
    celebrity_share = amount - platform_fee

    return {
        'total_amount': amount,
        'platform_fee': platform_fee,
        'celebrity_share': celebrity_share,
        'fee_percentage': float(platform_fee_percentage * 100)
    }


def get_qr_code_for_payment(celebrity, payment_method='esewa'):
    """Get QR code image URL for payment"""
    try:
        celebrity_profile = celebrity.celebrity_profile

        if payment_method == 'esewa' and celebrity_profile.esewa_qr_code:
            return celebrity_profile.esewa_qr_code.url
        elif payment_method == 'khalti' and celebrity_profile.khalti_qr_code:
            return celebrity_profile.khalti_qr_code.url

        return None
    except:
        return None


def get_payment_info(celebrity, payment_method='esewa'):
    """Get payment information and QR code for celebrity"""
    try:
        celebrity_profile = celebrity.celebrity_profile

        info = {
            'qr_code': get_qr_code_for_payment(celebrity, payment_method),
            'payment_id': None,
            'instructions': ''
        }

        if payment_method == 'esewa':
            info['payment_id'] = celebrity_profile.esewa_id
            info['instructions'] = f"Scan QR code or send to eSewa ID: {celebrity_profile.esewa_id}"
        elif payment_method == 'khalti':
            info['payment_id'] = celebrity_profile.khalti_id
            info['instructions'] = f"Scan QR code or send to Khalti ID: {celebrity_profile.khalti_id}"

        return info
    except:
        return {'qr_code': None, 'payment_id': None, 'instructions': 'Payment info not available'}


def update_celebrity_revenue(payment):
    """Update celebrity's revenue tracking after payment"""
    try:
        celebrity_profile = payment.celebrity.celebrity_profile
        celebrity_profile.total_revenue += payment.celebrity_share

        if payment.payment_type == 'merchandise':
            celebrity_profile.merchandise_revenue += payment.celebrity_share
        elif payment.payment_type == 'event':
            celebrity_profile.event_revenue += payment.celebrity_share
        elif payment.payment_type == 'subscription':
            celebrity_profile.subscription_revenue += payment.celebrity_share

        celebrity_profile.save()
    except Exception as e:
        print(f"Error updating revenue: {e}")


def get_celebrity_revenue_stats(celebrity):
    """Get comprehensive revenue statistics for celebrity"""
    from apps.payments.models import Payment

    payments = Payment.objects.filter(celebrity=celebrity, status='completed')

    total_revenue = payments.aggregate(total=Sum('celebrity_share'))['total'] or Decimal('0')
    merchandise_revenue = payments.filter(payment_type='merchandise').aggregate(
        total=Sum('celebrity_share'))['total'] or Decimal('0')
    event_revenue = payments.filter(payment_type='event').aggregate(
        total=Sum('celebrity_share'))['total'] or Decimal('0')
    subscription_revenue = payments.filter(payment_type='subscription').aggregate(
        total=Sum('celebrity_share'))['total'] or Decimal('0')

    return {
        'total_revenue': total_revenue,
        'merchandise_revenue': merchandise_revenue,
        'event_revenue': event_revenue,
        'subscription_revenue': subscription_revenue,
        'total_transactions': payments.count(),
    }