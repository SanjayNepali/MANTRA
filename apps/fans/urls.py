# apps/fans/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.FanDashboardView.as_view(), name='fan_dashboard'),

    # Discover
    path('discover/', views.discover_celebrities, name='discover_celebrities'),
    path('follow-suggestions/', views.celebrity_follow_suggestions, name='celebrity_follow_suggestions'),

    # Feed
    path('feed/', views.fan_feed, name='fan_feed'),
    
    # Subscriptions
    path('subscriptions/', views.my_subscriptions, name='my_subscriptions'),
    
    # Activities
    path('activities/', views.fan_activities, name='fan_activities'),
    
    # AJAX endpoints
    path('ajax/follow/', views.follow_celebrity_ajax, name='follow_celebrity_ajax'),

    path('refresh-recommendations/', views.refresh_recommendations, name='refresh_recommendations'),
]