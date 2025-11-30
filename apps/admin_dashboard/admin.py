# apps/admin_dashboard/admin.py
"""
Admin interface for Admin Dashboard models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    AdminDashboardSettings,
    SystemConfiguration,
    AdminAuditLog,
    SystemAlert,
    DataExportRequest,
)


@admin.register(AdminDashboardSettings)
class AdminDashboardSettingsAdmin(admin.ModelAdmin):
    list_display = ['admin_user', 'default_date_range', 'auto_refresh',
                   'email_critical_alerts', 'created_at']
    list_filter = ['auto_refresh', 'email_critical_alerts', 'report_frequency']
    search_fields = ['admin_user__username', 'admin_user__email']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User', {
            'fields': ('admin_user',)
        }),
        ('Dashboard Preferences', {
            'fields': ('default_date_range', 'auto_refresh', 'refresh_interval')
        }),
        ('Alert Preferences', {
            'fields': ('critical_alert_threshold', 'email_critical_alerts', 'sms_critical_alerts')
        }),
        ('Report Settings', {
            'fields': ('auto_generate_reports', 'report_frequency')
        }),
        ('Analytics Preferences', {
            'fields': ('show_ai_insights', 'show_predictions')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ['platform_name', 'maintenance_mode', 'enable_ai_moderation',
                   'platform_fee_percentage', 'updated_at']
    list_filter = ['maintenance_mode', 'enable_ai_moderation', 'enable_recommendations']
    search_fields = ['platform_name', 'platform_tagline']
    readonly_fields = ['updated_at']

    fieldsets = (
        ('Platform Settings', {
            'fields': ('platform_name', 'platform_tagline', 'maintenance_mode', 'maintenance_message')
        }),
        ('User Limits', {
            'fields': ('max_posts_per_day', 'max_messages_per_day', 'max_file_upload_size')
        }),
        ('Moderation Thresholds', {
            'fields': ('auto_ban_threshold', 'toxicity_threshold', 'spam_threshold')
        }),
        ('Financial Settings', {
            'fields': ('platform_fee_percentage', 'minimum_withdrawal')
        }),
        ('AI Settings', {
            'fields': ('enable_ai_moderation', 'enable_recommendations', 'enable_sentiment_analysis')
        }),
        ('Regional Settings', {
            'fields': ('available_regions', 'supported_languages'),
            'classes': ('collapse',)
        }),
        ('Points System', {
            'fields': ('points_config',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Only allow one system configuration
        return not SystemConfiguration.objects.exists()


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ['admin_user', 'action_type', 'target_user', 'description_short',
                   'ip_address', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['admin_user__username', 'description', 'target_user__username']
    readonly_fields = ['id', 'created_at', 'ip_address', 'user_agent']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Action Details', {
            'fields': ('admin_user', 'action_type', 'description')
        }),
        ('Target', {
            'fields': ('target_user', 'target_object_type', 'target_object_id')
        }),
        ('Additional Data', {
            'fields': ('metadata', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def description_short(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    description_short.short_description = 'Description'

    def has_add_permission(self, request):
        # Audit logs should only be created programmatically
        return False

    def has_change_permission(self, request, obj=None):
        # Audit logs should not be editable
        return False


@admin.register(SystemAlert)
class SystemAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'level_badge', 'category', 'affected_users',
                   'is_resolved', 'created_at']
    list_filter = ['level', 'category', 'is_resolved', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['id', 'created_at', 'resolved_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Alert Details', {
            'fields': ('title', 'message', 'level', 'category')
        }),
        ('Impact', {
            'fields': ('affected_users', 'affected_regions', 'additional_data')
        }),
        ('Resolution', {
            'fields': ('is_resolved', 'resolved_by', 'resolution_notes', 'resolved_at')
        }),
        ('Auto-Resolve Settings', {
            'fields': ('auto_resolve', 'auto_resolve_hours'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_resolved', 'escalate_to_critical']

    def level_badge(self, obj):
        colors = {
            'emergency': '#DC3545',
            'critical': '#FD7E14',
            'warning': '#FFC107',
            'info': '#17A2B8'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold; text-transform: uppercase;">{}</span>',
            colors.get(obj.level, '#6C757D'),
            obj.get_level_display()
        )
    level_badge.short_description = 'Level'

    def mark_resolved(self, request, queryset):
        queryset.update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{queryset.count()} alerts marked as resolved.')
    mark_resolved.short_description = 'Mark selected alerts as resolved'

    def escalate_to_critical(self, request, queryset):
        queryset.update(level='critical')
        self.message_user(request, f'{queryset.count()} alerts escalated to critical.')
    escalate_to_critical.short_description = 'Escalate to critical level'


@admin.register(DataExportRequest)
class DataExportRequestAdmin(admin.ModelAdmin):
    list_display = ['requested_by', 'export_type', 'export_format', 'status_badge',
                   'file_size_display', 'created_at']
    list_filter = ['export_type', 'export_format', 'status', 'encrypted', 'created_at']
    search_fields = ['requested_by__username']
    readonly_fields = ['id', 'created_at', 'completed_at', 'file_size', 'download_count']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Request Details', {
            'fields': ('requested_by', 'export_type', 'export_format')
        }),
        ('Filters', {
            'fields': ('date_from', 'date_to', 'filters'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'file_url', 'file_size', 'processing_time')
        }),
        ('Security', {
            'fields': ('encrypted', 'expires_at', 'download_count')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
    )

    def status_badge(self, obj):
        colors = {
            'completed': '#28A745',
            'processing': '#17A2B8',
            'pending': '#FFC107',
            'failed': '#DC3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6C757D'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def file_size_display(self, obj):
        if obj.file_size == 0:
            return '-'

        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'
    file_size_display.short_description = 'File Size'

    def has_change_permission(self, request, obj=None):
        # Export requests should not be editable after creation
        if obj and obj.status in ['completed', 'failed']:
            return False
        return True
