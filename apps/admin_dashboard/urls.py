# apps/admin_dashboard/urls.py
"""
Admin Dashboard URL Configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    # Main Dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),
    
    # SubAdmin Management
    path('subadmins/', views.manage_subadmins, name='admin_manage_subadmins'),
    path('subadmins/create/', views.create_subadmin, name='admin_create_subadmin'),
    path('subadmins/<uuid:subadmin_id>/edit/', views.edit_subadmin, name='admin_edit_subadmin'),
    path('subadmins/<uuid:subadmin_id>/delete/', views.delete_subadmin, name='admin_delete_subadmin'),
    path('subadmins/<uuid:subadmin_id>/performance/', views.subadmin_performance, name='admin_subadmin_performance'),
    path('subadmins/<uuid:subadmin_id>/toggle/', views.toggle_subadmin_status, name='admin_toggle_subadmin'),
    path('subadmins/<int:subadmin_id>/toggle/', views.toggle_subadmin_status, name='toggle_subadmin_status'),
    # Activity Reports
    path('reports/', views.review_activity_reports, name='review_activity_reports'),
    path('reports/<uuid:report_id>/', views.review_single_report, name='review_single_report'),
    
    # User Management
    path('users/', views.user_management, name='admin_user_management'),
    path('users/<uuid:user_id>/action/', views.user_action, name='admin_user_action'),
    path('users/<uuid:user_id>/details/', views.user_details, name='admin_user_details'),

    # KYC Management
    path('kyc/', views.kyc_list, name='admin_kyc_list'),
    path('kyc/<int:celebrity_id>/verify/', views.verify_celebrity_kyc, name='admin_verify_celebrity_kyc'),
    
    # System Analytics
    path('analytics/', views.system_analytics, name='admin_system_analytics'),
    path('analytics/export/', views.export_analytics, name='admin_export_analytics'),
    
    # System Configuration
    path('config/', views.system_configuration, name='admin_system_config'),
    path('config/save/', views.save_configuration, name='admin_save_config'),
    
    # Alerts
    path('alerts/', views.system_alerts, name='admin_system_alerts'),
    path('alerts/<uuid:alert_id>/', views.alert_detail, name='admin_alert_detail'),
    path('alerts/<uuid:alert_id>/resolve/', views.resolve_alert, name='admin_resolve_alert'),
    
    # Data Management
    path('export/', views.export_data, name='admin_export_data'),
    path('export/status/<uuid:export_id>/', views.export_status, name='admin_export_status'),
    path('backup/', views.system_backup, name='admin_system_backup'),
    
    # Audit Logs
    path('audit/', views.audit_logs, name='admin_audit_logs'),
    
    # Emergency Actions
    path('emergency/', views.emergency_actions, name='admin_emergency_actions'),
    path('emergency/maintenance/', views.toggle_maintenance, name='admin_toggle_maintenance'),
    
    # API Endpoints
    path('api/stats/', views.api_dashboard_stats, name='admin_api_stats'),
    path('api/alerts/', views.api_system_alerts, name='admin_api_alerts'),
    path('api/health/', views.api_system_health, name='admin_api_health'),
]