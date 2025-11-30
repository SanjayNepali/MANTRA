# apps/celebrities/urls.py

from django.urls import path
from apps.accounts.views import profile_view
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.CelebrityDashboardView.as_view(), name='celebrity_dashboard'),

    # Feed
    path('feed/', views.celebrity_feed, name='celebrity_feed'),

    # Celebrity listings
    path('<str:username>/', profile_view, name='celebrity_profile'),
    path('', views.CelebrityListView.as_view(), name='celebrity_list'),
    path('<str:username>/', views.CelebrityDetailView.as_view(), name='celebrity_detail'),
    
    # Profile management
    path('profile/setup/', views.celebrity_profile_setup, name='celebrity_profile_setup'),
    path('kyc/upload/', views.kyc_upload, name='celebrity_kyc_upload'),
    path('kyc/submit/', views.kyc_upload, name='celebrity_kyc_submit'),  # Alias for upload
    
    # Subscription
    path('subscription/settings/', views.subscription_settings, name='subscription_settings'),
    path('subscribe/<str:username>/', views.subscribe_to_celebrity, name='subscribe_to_celebrity'),
    path('subscriptions/my/', views.my_subscriptions, name='my_subscriptions'),
    path('subscription/cancel/<int:subscription_id>/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/renew/<int:celebrity_id>/', views.renew_subscription, name='renew_subscription'),
    path('subscription/toggle-auto-renew/<int:subscription_id>/', views.toggle_auto_renew, name='toggle_auto_renew'),

    # Payment
    path('payment/methods/', views.payment_methods, name='payment_methods'),
    
    path('kyc/upload/', views.kyc_upload, name='celebrity_kyc_upload'),
    path('kyc/resubmit/', views.kyc_resubmit, name='celebrity_kyc_resubmit'),
    
    # Analytics
    path('analytics/view/', views.celebrity_analytics, name='celebrity_analytics'),
    path('achievements/view/', views.celebrity_achievements, name='celebrity_achievements'),
    path('profile/<str:username>/', views.CelebrityProfileView.as_view(), name='celebrity_profile'),
]