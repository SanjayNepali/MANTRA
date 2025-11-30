# apps/payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Payment processing
    path('process/', views.process_payment, name='process_payment'),
    path('history/', views.payment_history, name='payment_history'),
    path('methods/', views.payment_methods, name='payment_methods'),

    # eSewa integration
    path('esewa/initiate/', views.ESewaPaymentView.as_view(), name='esewa_payment'),
    path('esewa/success/', views.ESewaSuccessView.as_view(), name='esewa_success'),
    path('esewa/failure/', views.ESewaFailureView.as_view(), name='esewa_failure'),

    # Mock payment (for testing)
    path('mock/process/', views.mock_payment_process, name='mock_payment_process'),

    # QR code generation
    path('generate-qr/', views.GenerateQRView.as_view(), name='generate_qr'),

    # Success/Failure pages
    path('success/<uuid:payment_id>/', views.payment_success, name='payment_success'),
    path('failed/', views.payment_failed, name='payment_failed'),

    # Status check
    path('status/<str:transaction_id>/', views.check_payment_status, name='check_payment_status'),

    # Celebrity earnings
    path('earnings/', views.earnings_dashboard, name='earnings_dashboard'),
    path('earnings/', views.earnings_dashboard, name='celebrity_earnings'),  # Alias for navbar
    path('withdrawal/', views.request_withdrawal, name='request_withdrawal'),
]