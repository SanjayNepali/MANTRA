# apps/admin_dashboard/models.py
"""
Admin Dashboard Models for MANTRA Platform
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import json


class AdminDashboardSettings(models.Model):
    """Settings for admin dashboard"""
    
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_settings'
    )
    
    # Dashboard preferences
    default_date_range = models.IntegerField(default=30)
    auto_refresh = models.BooleanField(default=True)
    refresh_interval = models.IntegerField(default=300)  # seconds
    
    # Alert preferences
    critical_alert_threshold = models.IntegerField(default=10)
    email_critical_alerts = models.BooleanField(default=True)
    sms_critical_alerts = models.BooleanField(default=False)
    
    # Report settings
    auto_generate_reports = models.BooleanField(default=True)
    report_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly')
        ],
        default='weekly'
    )
    
    # Analytics preferences
    show_ai_insights = models.BooleanField(default=True)
    show_predictions = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Admin Dashboard Settings'
        verbose_name_plural = 'Admin Dashboard Settings'
    
    def __str__(self):
        return f"Settings for {self.admin_user.username}"


class SystemConfiguration(models.Model):
    """System-wide configuration managed by admin"""
    
    # Platform settings
    platform_name = models.CharField(max_length=100, default='MANTRA')
    platform_tagline = models.CharField(max_length=200, default='Connect with your favorite celebrities')
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    # User limits
    max_posts_per_day = models.IntegerField(default=10)
    max_messages_per_day = models.IntegerField(default=100)
    max_file_upload_size = models.IntegerField(default=10)  # MB
    
    # Moderation thresholds
    auto_ban_threshold = models.IntegerField(default=5)  # warnings before auto-ban
    toxicity_threshold = models.FloatField(default=0.7)
    spam_threshold = models.FloatField(default=0.6)
    
    # Financial settings
    platform_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    minimum_withdrawal = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    
    # AI settings
    enable_ai_moderation = models.BooleanField(default=True)
    enable_recommendations = models.BooleanField(default=True)
    enable_sentiment_analysis = models.BooleanField(default=True)
    
    # Regional settings
    available_regions = models.JSONField(default=list)
    supported_languages = models.JSONField(default=list)
    
    # Points system
    points_config = models.JSONField(default=dict)
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configuration'
    
    def __str__(self):
        return f"{self.platform_name} Configuration"
    
    def save(self, *args, **kwargs):
        # Ensure only one configuration exists
        if not self.pk and SystemConfiguration.objects.exists():
            raise ValidationError('Only one system configuration can exist')
        super().save(*args, **kwargs)


class AdminAuditLog(models.Model):
    """Audit log for admin actions"""
    
    ACTION_TYPES = (
        ('user_ban', 'User Ban'),
        ('user_unban', 'User Unban'),
        ('user_verify', 'User Verification'),
        ('content_delete', 'Content Deletion'),
        ('subadmin_create', 'SubAdmin Created'),
        ('subadmin_delete', 'SubAdmin Deleted'),
        ('config_change', 'Configuration Change'),
        ('data_export', 'Data Export'),
        ('system_restart', 'System Restart'),
        ('emergency_action', 'Emergency Action'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_audit_logs'
    )
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    
    # Target information
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_actions_received'
    )
    target_object_type = models.CharField(max_length=50, blank=True)
    target_object_id = models.CharField(max_length=100, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin_user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.get_action_type_display()} - {self.created_at}"


class SystemAlert(models.Model):
    """System-wide alerts for admin attention"""
    
    ALERT_LEVELS = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('emergency', 'Emergency'),
    )
    
    ALERT_CATEGORIES = (
        ('security', 'Security'),
        ('performance', 'Performance'),
        ('content', 'Content'),
        ('financial', 'Financial'),
        ('user', 'User Activity'),
        ('system', 'System'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    level = models.CharField(max_length=20, choices=ALERT_LEVELS)
    category = models.CharField(max_length=20, choices=ALERT_CATEGORIES)
    
    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_system_alerts'
    )
    resolution_notes = models.TextField(blank=True)
    
    # Metadata
    affected_users = models.IntegerField(default=0)
    affected_regions = models.JSONField(default=list)
    additional_data = models.JSONField(default=dict)
    
    # Auto-resolve settings
    auto_resolve = models.BooleanField(default=False)
    auto_resolve_hours = models.IntegerField(default=24)
    
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-level', '-created_at']
        indexes = [
            models.Index(fields=['level', 'is_resolved', '-created_at']),
            models.Index(fields=['category', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"
    
    def check_auto_resolve(self):
        """Check if alert should be auto-resolved"""
        if self.auto_resolve and not self.is_resolved:
            hours_passed = (timezone.now() - self.created_at).total_seconds() / 3600
            if hours_passed >= self.auto_resolve_hours:
                self.is_resolved = True
                self.resolution_notes = 'Auto-resolved after timeout'
                self.resolved_at = timezone.now()
                self.save()
                return True
        return False


class DataExportRequest(models.Model):
    """Track data export requests"""
    
    EXPORT_TYPES = (
        ('users', 'User Data'),
        ('content', 'Content Data'),
        ('analytics', 'Analytics Data'),
        ('financial', 'Financial Data'),
        ('full', 'Full System Export'),
    )
    
    EXPORT_FORMATS = (
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('excel', 'Excel'),
        ('sql', 'SQL Dump'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='data_export_requests'
    )
    
    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES)
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    
    # Filters
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_url = models.URLField(blank=True)
    file_size = models.BigIntegerField(default=0)  # bytes
    
    # Security
    encrypted = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    download_count = models.IntegerField(default=0)
    
    # Metadata
    error_message = models.TextField(blank=True)
    processing_time = models.FloatField(default=0)  # seconds
    
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requested_by', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_export_type_display()} - {self.requested_by.username} - {self.created_at}"