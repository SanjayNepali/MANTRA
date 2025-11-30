# apps/subadmin/urls.py
"""
URL Configuration for SubAdmin Management
"""

from django.urls import path
from . import views

urlpatterns = [
    # Main Dashboard
    path('dashboard/', views.subadmin_dashboard, name='subadmin_dashboard'),
    
    # Report Management
    path('reports/', views.reports_management, name='subadmin_reports'),
    path('reports/<uuid:report_id>/review/', views.review_report, name='subadmin_review_report'),
    
    # KYC Verification
    path('kyc/', views.kyc_verification, name='subadmin_kyc'),
    path('kyc/<int:celebrity_id>/verify/', views.verify_celebrity, name='subadmin_verify_celebrity'),
    
    # User Management
    path('users/', views.user_management, name='subadmin_users'),
    path('users/<int:user_id>/profile/', views.user_profile_view, name='subadmin_user_profile'),

    # Analytics & Reports
    path('analytics/', views.regional_analytics, name='subadmin_analytics'),
    path('activity-reports/', views.activity_reports, name='subadmin_activity_reports'),
    
    # Quick Actions (AJAX)
    path('quick-action/', views.quick_action, name='subadmin_quick_action'),

    # Content Moderation Queue
    path('moderation/', views.moderation_queue, name='moderation_queue'),
    path('moderation/<uuid:alert_id>/review/', views.review_alert, name='review_alert'),

    # Activity Report Submission
    path('submit-report/', views.submit_activity_report, name='submit_activity_report'),

    # Comment Report Review
    path('comment-reports/<uuid:report_id>/review/', views.review_comment_report, name='review_comment_report'),
]