# apps/celebrities/urls.py - Updated version

from django.urls import path
from apps.accounts.views import profile_view
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.CelebrityDashboardView.as_view(), name='celebrity_dashboard'),

    # Feed
    path('feed/', views.celebrity_feed, name='celebrity_feed'),

    # Celebrity listings (careful with order - specific before general)
    path('', views.CelebrityListView.as_view(), name='celebrity_list'),
    path('profile/<str:username>/', views.CelebrityProfileView.as_view(), name='celebrity_profile_detail'),
    
    # Profile management
    path('profile/setup/', views.celebrity_profile_setup, name='celebrity_profile_setup'),
    
    # KYC
    path('kyc/upload/', views.kyc_upload, name='celebrity_kyc_upload'),
    path('kyc/resubmit/', views.kyc_resubmit, name='celebrity_kyc_resubmit'),
    
    # Subscription
    path('subscription/settings/', views.subscription_settings, name='subscription_settings'),
    path('subscribe/<str:username>/', views.subscribe_to_celebrity, name='subscribe_to_celebrity'),
    path('subscriptions/my/', views.my_subscriptions, name='my_subscriptions'),
    path('subscription/cancel/<int:subscription_id>/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/renew/<int:celebrity_id>/', views.renew_subscription, name='renew_subscription'),
    path('subscription/toggle-auto-renew/<int:subscription_id>/', views.toggle_auto_renew, name='toggle_auto_renew'),

    # Payment
    path('payment/methods/', views.payment_methods, name='payment_methods'),
    
    # Celebrity management features (these are the missing URLs from your sidebar)
    path('posts/', views.celebrity_posts, name='celebrity_posts'),
    path('events/', views.celebrity_events, name='celebrity_events'),
    path('merchandise/', views.celebrity_merchandise, name='celebrity_merchandise'),
    path('fanclubs/', views.celebrity_fanclubs, name='celebrity_fanclubs'),
    path('analytics/', views.celebrity_analytics, name='celebrity_analytics'),
    path('settings/', views.celebrity_settings, name='celebrity_settings'),
    
    # Achievements
    path('achievements/view/', views.celebrity_achievements, name='celebrity_achievements'),
]