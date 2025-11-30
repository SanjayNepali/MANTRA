# apps/payments/views.py

import json
import hashlib
import base64
import qrcode
from io import BytesIO
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db import models
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from apps.accounts.models import User
from apps.payments.models import PaymentTransaction
from utils.decorators import ajax_required
from utils.helpers import generate_transaction_id, generate_esewa_qr


class ESewaPaymentView(LoginRequiredMixin, View):
    """Handle eSewa payment integration"""

    def get(self, request):
        """Render eSewa payment form or process mock payment"""
        from utils.helpers import generate_esewa_signature

        # Get parameters from query string or session
        payment_id = request.GET.get('payment_id')

        if payment_id:
            try:
                payment = PaymentTransaction.objects.get(id=payment_id, user=request.user)

                # Check if mock mode is enabled
                if getattr(settings, 'ESEWA_MOCK_MODE', False):
                    # Mock mode: simulate immediate successful payment
                    return self._process_mock_payment(request, payment)

                # Generate eSewa payment data
                payment_data = self._generate_esewa_data(payment)

                # Store payment data in session for verification
                request.session[f'payment_{payment.transaction_id}'] = {
                    'amount': str(payment.amount),
                    'payment_id': str(payment.id),
                    'type': payment.payment_type,
                    'reference_id': payment.related_object_id
                }

                # Generate signature for v2 API
                signature_message = f"total_amount={payment.amount},transaction_uuid={payment.transaction_id},product_code={settings.ESEWA_MERCHANT_CODE}"
                signature = generate_esewa_signature(signature_message, settings.ESEWA_SECRET_KEY)

                context = {
                    'esewa_url': settings.ESEWA_PAYMENT_URL,
                    'amount': str(payment.amount),
                    'transaction_id': payment.transaction_id,
                    'merchant_code': settings.ESEWA_MERCHANT_CODE,
                    'success_url': payment_data['success_url'],
                    'failure_url': payment_data['failure_url'],
                    'signature': signature,
                    'mock_mode': False
                }

                return render(request, 'payments/esewa_payment.html', context)
            except PaymentTransaction.DoesNotExist:
                messages.error(request, 'Payment not found.')
                return redirect('payment_history')

        messages.error(request, 'Invalid payment request.')
        return redirect('payment_history')

    def _process_mock_payment(self, request, payment):
        """Process payment in mock mode (for local testing)"""
        # Render a mock payment confirmation page
        context = {
            'payment': payment,
            'mock_mode': True
        }
        return render(request, 'payments/mock_payment.html', context)

    def post(self, request):
        """Initiate eSewa payment (AJAX/API)"""
        payment_type = request.POST.get('payment_type')
        amount = Decimal(request.POST.get('amount', 0))
        reference_id = request.POST.get('reference_id')

        if amount <= 0:
            return JsonResponse({'error': 'Invalid amount'}, status=400)

        # Generate unique transaction ID
        transaction_id = generate_transaction_id()

        # Create payment record
        payment = PaymentTransaction.objects.create(
            user=request.user,
            amount=amount,
            payment_method='esewa',
            transaction_id=transaction_id,
            payment_type=payment_type,
            related_object_id=reference_id,
            status='pending'
        )

        # Generate eSewa payment data
        payment_data = self._generate_esewa_data(payment)

        # Store payment data in session for verification
        request.session[f'payment_{transaction_id}'] = {
            'amount': str(amount),
            'payment_id': str(payment.id),
            'type': payment_type,
            'reference_id': reference_id
        }

        return JsonResponse({
            'success': True,
            'transaction_id': transaction_id,
            'payment_url': reverse('esewa_payment') + f'?payment_id={payment.id}',
            'payment_data': payment_data
        })

    def _generate_esewa_data(self, payment):
        """Generate eSewa payment parameters (v2 API)"""
        success_url = self.request.build_absolute_uri(
            reverse('esewa_success')
        )
        failure_url = self.request.build_absolute_uri(
            reverse('esewa_failure')
        )

        return {
            'amount': str(payment.amount),
            'tax_amount': '0',
            'total_amount': str(payment.amount),
            'transaction_uuid': payment.transaction_id,
            'product_code': getattr(settings, 'ESEWA_MERCHANT_CODE', 'EPAYTEST'),
            'product_service_charge': '0',
            'product_delivery_charge': '0',
            'success_url': success_url,
            'failure_url': failure_url
        }


class ESewaSuccessView(LoginRequiredMixin, View):
    """Handle eSewa payment success callback (v2 API - RC)"""

    def get(self, request):
        """Process successful payment - v2 API returns Base64 encoded data"""
        import base64
        import json
        import requests
        from utils.helpers import generate_esewa_signature

        # Get Base64 encoded data from query parameter
        encoded_data = request.GET.get('data')

        if not encoded_data:
            messages.error(request, 'Invalid payment response.')
            return redirect('payment_failed')

        try:
            # Decode Base64 response
            decoded_bytes = base64.b64decode(encoded_data)
            decoded_str = decoded_bytes.decode('utf-8')
            response_data = json.loads(decoded_str)

            # Extract response parameters
            transaction_code = response_data.get('transaction_code')
            status = response_data.get('status')
            total_amount = response_data.get('total_amount')
            transaction_uuid = response_data.get('transaction_uuid')
            product_code = response_data.get('product_code')
            signed_field_names = response_data.get('signed_field_names')
            received_signature = response_data.get('signature')

            # Verify signature
            if self._verify_signature(response_data, received_signature):
                # Get payment from session
                payment_data = request.session.get(f'payment_{transaction_uuid}')

                if payment_data and status == 'COMPLETE':
                    # Update payment status
                    payment = PaymentTransaction.objects.get(id=payment_data['payment_id'])
                    payment.status = 'completed'
                    payment.metadata = payment.metadata or {}
                    payment.metadata['esewa_transaction_code'] = transaction_code
                    payment.metadata['esewa_ref_id'] = transaction_code
                    payment.completed_at = timezone.now()
                    payment.save()

                    # Process payment based on type
                    self._process_payment(payment, payment_data)

                    # Clear session data
                    del request.session[f'payment_{transaction_uuid}']

                    messages.success(request, 'Payment successful!')
                    return redirect('payment_success', payment_id=payment.id)

        except Exception as e:
            print(f"Error processing eSewa callback: {e}")
            messages.error(request, 'Payment verification failed.')
            return redirect('payment_failed')

        messages.error(request, 'Payment verification failed.')
        return redirect('payment_failed')

    def _verify_signature(self, response_data, received_signature):
        """Verify payment signature with eSewa v2 API"""
        from utils.helpers import generate_esewa_signature

        try:
            # Build signature message from signed_field_names
            signed_fields = response_data.get('signed_field_names', '').split(',')
            message_parts = []

            for field in signed_fields:
                field = field.strip()
                if field in response_data:
                    message_parts.append(f"{field}={response_data[field]}")

            signature_message = ','.join(message_parts)

            # Generate signature
            expected_signature = generate_esewa_signature(
                signature_message,
                settings.ESEWA_SECRET_KEY
            )

            # Compare signatures
            return expected_signature == received_signature

        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def _process_payment(self, payment, payment_data):
        """Process payment based on type"""
        with transaction.atomic():
            if payment_data['type'] == 'subscription':
                self._process_subscription(payment, payment_data['reference_id'])
            elif payment_data['type'] == 'event':
                self._process_event_booking(payment, payment_data['reference_id'])
            elif payment_data['type'] == 'merchandise':
                self._process_order(payment, payment_data['reference_id'])
            elif payment_data['type'] == 'tip':
                self._process_tip(payment, payment_data['reference_id'])

    def _process_subscription(self, payment, subscription_id):
        """Process subscription payment"""
        try:
            from apps.celebrities.models import Subscription, CelebrityAnalytics
            from datetime import timedelta

            # Update subscription status
            subscription = Subscription.objects.get(id=subscription_id)
            subscription.status = 'active'
            subscription.save()

            celebrity_user = subscription.celebrity

            # Award points to subscriber
            if hasattr(payment.user, 'add_points'):
                payment.user.add_points(50, f'Subscribed to {celebrity_user.username}')

            # Add earnings to celebrity
            if hasattr(celebrity_user, 'celebrity_profile'):
                profile = celebrity_user.celebrity_profile
                if hasattr(profile, 'add_earnings'):
                    profile.add_earnings(
                        subscription.amount_paid,
                        f"New subscription from {payment.user.username}"
                    )

            # Update analytics
            today = timezone.now().date()
            analytics, created = CelebrityAnalytics.objects.get_or_create(
                celebrity=celebrity_user,
                date=today
            )
            analytics.new_followers += 1  # Track new subscriber as a follower
            analytics.total_followers = Subscription.objects.filter(
                celebrity=celebrity_user,
                status='active'
            ).count()
            analytics.subscription_revenue += float(subscription.amount_paid)
            analytics.total_revenue += float(subscription.amount_paid)
            analytics.save()

            # Send notification to celebrity
            from apps.notifications.models import Notification
            Notification.objects.create(
                user=celebrity_user,
                notification_type='subscription',
                title='New Subscriber!',
                message=f'{payment.user.username} subscribed to your exclusive content',
                target_url=f'/accounts/profile/{payment.user.username}/'
            )
        except Exception as e:
            print(f"Error processing subscription: {e}")

    def _process_event_booking(self, payment, booking_id):
        """Process event booking payment"""
        try:
            from apps.events.models import EventBooking
            booking = EventBooking.objects.get(id=booking_id)
            booking.payment_status = 'completed'
            booking.is_confirmed = True
            booking.save()

            # Update event stats
            event = booking.event
            event.current_attendees = event.bookings.filter(is_confirmed=True).count()
            event.save()

            # Award points
            payment.user.add_points(20, 'Event booking')

            # Send confirmation
            from utils.helpers import send_notification
            send_notification(
                payment.user,
                'event_confirmation',
                'Booking Confirmed!',
                f'Your booking for {event.title} has been confirmed',
                booking
            )
        except Exception as e:
            print(f"Error processing event booking: {e}")

    def _process_order(self, payment, order_id):
        """Process merchandise order payment"""
        try:
            from apps.merchandise.models import Order
            order = Order.objects.get(id=order_id)
            order.payment_status = 'paid'
            order.status = 'processing'
            order.paid_at = timezone.now()
            order.save()

            # Update stock
            for item in order.items.all():
                product = item.product
                product.stock -= item.quantity
                product.save()

            # Award points
            payment.user.add_points(15, 'Merchandise purchase')

            # Notify seller
            from utils.helpers import send_notification
            for item in order.items.all():
                send_notification(
                    item.product.seller,
                    'order',
                    'New Order!',
                    f'You have a new order for {item.product.name}',
                    order
                )
        except Exception as e:
            print(f"Error processing order: {e}")

    def _process_tip(self, payment, celebrity_id):
        """Process tip payment"""
        try:
            celebrity = User.objects.get(id=celebrity_id)

            # Calculate platform fee (10%)
            platform_fee = payment.amount * Decimal('0.1')
            celebrity_amount = payment.amount - platform_fee

            # Update celebrity earnings
            if hasattr(celebrity, 'celebrity_profile'):
                celebrity.celebrity_profile.total_earnings += celebrity_amount
                celebrity.celebrity_profile.save()

            # Send notification
            from utils.helpers import send_notification
            send_notification(
                celebrity,
                'tip',
                'You received a tip!',
                f'{payment.user.get_full_name()} sent you a tip of Rs. {payment.amount}',
                payment
            )
        except Exception as e:
            print(f"Error processing tip: {e}")


class ESewaFailureView(LoginRequiredMixin, View):
    """Handle eSewa payment failure"""

    def get(self, request):
        """Process failed payment - supports both v1 and v2 API"""
        # Try v2 API parameter first (transaction_uuid)
        transaction_uuid = request.GET.get('transaction_uuid')

        # Fallback to v1 API parameter (oid)
        if not transaction_uuid:
            transaction_uuid = request.GET.get('oid')

        # Log all query parameters for debugging
        print(f"Payment failure callback received. Query params: {dict(request.GET)}")

        # Get payment from session
        if transaction_uuid:
            payment_data = request.session.get(f'payment_{transaction_uuid}')

            if payment_data:
                try:
                    # Update payment status
                    payment = PaymentTransaction.objects.get(id=payment_data['payment_id'])
                    payment.status = 'failed'
                    payment.metadata = payment.metadata or {}
                    payment.metadata['failure_reason'] = 'User cancelled or payment failed'
                    payment.metadata['failure_params'] = dict(request.GET)
                    payment.save()

                    # Clear session data
                    del request.session[f'payment_{transaction_uuid}']

                    print(f"Payment {payment.id} marked as failed")
                except PaymentTransaction.DoesNotExist:
                    print(f"Payment transaction not found for ID: {payment_data.get('payment_id')}")
                except Exception as e:
                    print(f"Error updating failed payment: {e}")
            else:
                print(f"No payment session data found for transaction: {transaction_uuid}")
        else:
            print("No transaction ID found in failure callback")

        messages.error(request, 'Payment failed or was cancelled. Please try again.')
        return redirect('payment_failed')


@login_required
def process_payment(request):
    """Process a payment request"""
    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '')

        try:
            # Create payment transaction
            transaction_id = generate_transaction_id()
            payment = PaymentTransaction.objects.create(
                user=request.user,
                transaction_id=transaction_id,
                payment_type=payment_type,
                amount=Decimal(amount),
                description=description,
                status='pending'
            )

            # Redirect to appropriate payment gateway
            if payment_type == 'esewa':
                return redirect('esewa_payment', payment_id=payment.id)
            elif payment_type == 'khalti':
                return redirect('khalti_payment', payment_id=payment.id)
            else:
                messages.error(request, 'Invalid payment method selected.')
                return redirect('payment_history')

        except Exception as e:
            messages.error(request, f'Payment processing failed: {str(e)}')
            return redirect('payment_history')

    return redirect('payment_history')


@login_required
def payment_history(request):
    """View payment history"""
    transactions = PaymentTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(transactions, 20)
    page = request.GET.get('page')
    transactions_page = paginator.get_page(page)

    # Calculate totals
    total_spent = PaymentTransaction.objects.filter(
        user=request.user,
        status='completed'
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    # Group by type
    spending_by_type = PaymentTransaction.objects.filter(
        user=request.user,
        status='completed'
    ).values('payment_type').annotate(
        total=models.Sum('amount')
    ).order_by('-total')

    context = {
        'transactions': transactions_page,
        'total_spent': total_spent,
        'spending_by_type': spending_by_type
    }

    return render(request, 'payments/history.html', context)


@login_required
def payment_methods(request):
    """Manage payment methods"""
    if request.method == 'POST':
        esewa_id = request.POST.get('esewa_id')

        # Validate eSewa ID
        if not esewa_id or not esewa_id.startswith('98'):
            messages.error(request, 'Invalid eSewa ID. Must start with 98.')
            return redirect('payment_methods')

        # Save eSewa ID to user profile
        request.user.profile.esewa_id = esewa_id
        request.user.profile.save()

        messages.success(request, 'eSewa account connected successfully')
        return redirect('payment_methods')

    context = {
        'esewa_id': getattr(request.user.profile, 'esewa_id', ''),
        'esewa_connected': bool(getattr(request.user.profile, 'esewa_id', None))
    }

    return render(request, 'payments/payment_methods.html', context)


class GenerateQRView(LoginRequiredMixin, View):
    """Generate payment QR code"""

    @ajax_required
    def post(self, request):
        """Generate QR code for payment"""
        amount = request.POST.get('amount')
        payment_type = request.POST.get('type')

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError('Invalid amount')
        except:
            return JsonResponse({'error': 'Invalid amount'}, status=400)

        # Generate transaction ID
        transaction_id = generate_transaction_id()

        # Create payment data
        payment_data = {
            'amt': str(amount),
            'pid': transaction_id,
            'scd': getattr(settings, 'ESEWA_MERCHANT_CODE', 'EPAYTEST'),
            'type': payment_type
        }

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # eSewa payment string
        qr_data = f"esewa://?amt={amount}&pid={transaction_id}&scd={payment_data['scd']}"
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        img_str = base64.b64encode(buffer.getvalue()).decode()

        return JsonResponse({
            'success': True,
            'qr_code': f"data:image/png;base64,{img_str}",
            'transaction_id': transaction_id,
            'payment_data': payment_data
        })


@login_required
def earnings_dashboard(request):
    """Celebrity earnings dashboard"""
    if request.user.user_type != 'celebrity':
        messages.error(request, 'This page is only for celebrities')
        return redirect('dashboard')

    # Get earnings data
    from datetime import timedelta

    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Calculate earnings
    def calculate_earnings(start_date, end_date):
        return PaymentTransaction.objects.filter(
            metadata__celebrity_id=str(request.user.id),
            status='completed',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or 0

    earnings = {
        'today': calculate_earnings(today, today),
        'week': calculate_earnings(week_ago, today),
        'month': calculate_earnings(month_ago, today),
        'total': request.user.celebrity_profile.total_earnings if hasattr(request.user, 'celebrity_profile') else 0
    }

    # Get pending payouts
    pending_payouts = PaymentTransaction.objects.filter(
        metadata__celebrity_id=str(request.user.id),
        status='completed',
        metadata__withdrawn=False
    ).aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    # Get transaction history
    transactions = PaymentTransaction.objects.filter(
        metadata__celebrity_id=str(request.user.id)
    ).order_by('-created_at')[:10]

    # Get revenue breakdown
    revenue_breakdown = PaymentTransaction.objects.filter(
        metadata__celebrity_id=str(request.user.id),
        status='completed'
    ).values('payment_type').annotate(
        total=models.Sum('amount'),
        count=models.Count('id')
    ).order_by('-total')

    context = {
        'earnings': earnings,
        'pending_payouts': pending_payouts,
        'transactions': transactions,
        'revenue_breakdown': revenue_breakdown,
        'bank_accounts': request.user.bank_accounts.all() if hasattr(request.user, 'bank_accounts') else []
    }

    return render(request, 'payments/earnings.html', context)


@login_required
def request_withdrawal(request):
    """Handle earnings withdrawal request"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if request.user.user_type != 'celebrity':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    amount = Decimal(request.POST.get('amount', 0))
    bank_account_id = request.POST.get('bank_account_id')

    # Get available balance
    available_balance = PaymentTransaction.objects.filter(
        metadata__celebrity_id=str(request.user.id),
        status='completed',
        metadata__withdrawn=False
    ).aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    # Validate amount
    if amount > available_balance:
        return JsonResponse({'error': 'Insufficient balance'}, status=400)

    if amount < 100:  # Minimum withdrawal
        return JsonResponse({'error': 'Minimum withdrawal is Rs. 100'}, status=400)

    # Create withdrawal request
    withdrawal = PaymentTransaction.objects.create(
        user=request.user,
        amount=amount,
        payment_method='esewa',
        payment_type='withdrawal',
        status='pending',
        metadata={
            'bank_account_id': bank_account_id,
            'requested_at': timezone.now().isoformat(),
            'type': 'withdrawal'
        }
    )

    messages.success(request, 'Withdrawal request submitted successfully')
    return JsonResponse({
        'success': True,
        'withdrawal_id': str(withdrawal.id)
    })


@login_required
def payment_success(request, payment_id):
    """Payment success page"""
    payment = get_object_or_404(PaymentTransaction, id=payment_id, user=request.user)

    context = {
        'payment': payment
    }

    return render(request, 'payments/success.html', context)


@login_required
def payment_failed(request):
    """Payment failed page"""
    return render(request, 'payments/failed.html')


@login_required
def mock_payment_process(request):
    """Process mock payment (for testing only)"""
    if not getattr(settings, 'ESEWA_MOCK_MODE', False):
        messages.error(request, 'Mock payments are disabled.')
        return redirect('payment_history')

    payment_id = request.GET.get('payment_id')
    status = request.GET.get('status', 'success')

    try:
        payment = PaymentTransaction.objects.get(id=payment_id, user=request.user)

        if status == 'success':
            # Simulate successful payment
            payment.status = 'completed'
            payment.metadata = payment.metadata or {}
            payment.metadata['mock_payment'] = True
            payment.metadata['mock_ref_id'] = f'MOCK-{payment.transaction_id}'
            payment.completed_at = timezone.now()
            payment.save()

            # Get payment data from session
            payment_data = request.session.get(f'payment_{payment.transaction_id}')

            if payment_data:
                # Process payment based on type
                success_view = ESewaSuccessView()
                success_view._process_payment(payment, payment_data)

                # Clear session
                del request.session[f'payment_{payment.transaction_id}']

            messages.success(request, 'Mock payment processed successfully!')
            return redirect('payment_success', payment_id=payment.id)
        else:
            # Simulate failed payment
            payment.status = 'failed'
            payment.metadata = payment.metadata or {}
            payment.metadata['mock_payment'] = True
            payment.metadata['failure_reason'] = 'Mock payment cancelled'
            payment.save()

            # Clear session
            if f'payment_{payment.transaction_id}' in request.session:
                del request.session[f'payment_{payment.transaction_id}']

            messages.error(request, 'Mock payment cancelled.')
            return redirect('payment_failed')

    except PaymentTransaction.DoesNotExist:
        messages.error(request, 'Payment not found.')
        return redirect('payment_history')


@login_required
def check_payment_status(request, transaction_id):
    """
    Check payment status with eSewa v2 API
    Used when payment response is not received within timeout period
    """
    import requests

    try:
        # Get payment transaction
        payment = PaymentTransaction.objects.get(
            transaction_id=transaction_id,
            user=request.user
        )

        # Build status check URL
        status_url = f"{settings.ESEWA_STATUS_URL}?product_code={settings.ESEWA_MERCHANT_CODE}&total_amount={payment.amount}&transaction_uuid={transaction_id}"

        # Make API call to eSewa
        response = requests.get(status_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            ref_id = data.get('ref_id')

            # Update payment based on status
            if status == 'COMPLETE':
                payment.status = 'completed'
                payment.metadata = payment.metadata or {}
                payment.metadata['esewa_ref_id'] = ref_id
                payment.completed_at = timezone.now()
                payment.save()

                # Process the payment
                payment_data = request.session.get(f'payment_{transaction_id}')
                if payment_data:
                    success_view = ESewaSuccessView()
                    success_view._process_payment(payment, payment_data)
                    del request.session[f'payment_{transaction_id}']

                return JsonResponse({
                    'success': True,
                    'status': 'completed',
                    'message': 'Payment completed successfully'
                })

            elif status in ['PENDING', 'AMBIGUOUS']:
                return JsonResponse({
                    'success': False,
                    'status': 'pending',
                    'message': 'Payment is still processing'
                })

            elif status in ['NOT_FOUND', 'CANCELED', 'FULL_REFUND', 'PARTIAL_REFUND']:
                payment.status = 'failed'
                payment.save()

                return JsonResponse({
                    'success': False,
                    'status': 'failed',
                    'message': f'Payment {status.lower()}'
                })

        return JsonResponse({
            'success': False,
            'status': 'error',
            'message': 'Unable to check payment status'
        }, status=500)

    except PaymentTransaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'status': 'error',
            'message': 'Payment transaction not found'
        }, status=404)
    except Exception as e:
        print(f"Error checking payment status: {e}")
        return JsonResponse({
            'success': False,
            'status': 'error',
            'message': str(e)
        }, status=500)
