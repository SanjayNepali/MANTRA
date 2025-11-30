# apps/subadmin/admin.py
"""
Admin interface for SubAdmin management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    SubAdminActivityReport,
    RegionalAlert,
    ModeratedContent,
    SubAdminPerformance,
)
# Note: KYCDocument is already registered in apps.celebrities.admin


@admin.register(SubAdminActivityReport)
class SubAdminActivityReportAdmin(admin.ModelAdmin):
    list_display = ['region', 'subadmin', 'period_display', 'reports_resolved', 
                   'kyc_processed', 'status', 'submitted_at']
    list_filter = ['region', 'submitted_at', 'reviewed_at']
    search_fields = ['subadmin__username', 'region']
    readonly_fields = ['id', 'submitted_at']
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Report Information', {
            'fields': ('subadmin', 'region', 'period_start', 'period_end')
        }),
        ('Metrics', {
            'fields': ('reports_resolved', 'kyc_processed', 'warnings_issued',
                      'suspensions_issued', 'bans_issued')
        }),
        ('Sentiment Analysis', {
            'fields': ('avg_toxicity_score', 'avg_spam_score'),
            'classes': ('collapse',)
        }),
        ('Review', {
            'fields': ('reviewed_by', 'review_notes', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def period_display(self, obj):
        return f"{obj.period_start} to {obj.period_end}"
    period_display.short_description = 'Report Period'
    
    def status(self, obj):
        if obj.reviewed_at:
            return format_html(
                '<span style="color: green;">✓ Reviewed</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Pending</span>'
        )
    status.short_description = 'Status'


@admin.register(RegionalAlert)
class RegionalAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'region', 'alert_type', 'priority_badge', 
                   'is_resolved', 'created_at']
    list_filter = ['priority', 'alert_type', 'is_resolved', 'region']
    search_fields = ['title', 'description', 'region']
    readonly_fields = ['id', 'created_at', 'resolved_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Details', {
            'fields': ('title', 'description', 'alert_type', 'priority', 'region')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'affected_users')
        }),
        ('Resolution', {
            'fields': ('is_resolved', 'resolved_by', 'resolution_notes', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_resolved', 'escalate_priority']
    
    def priority_badge(self, obj):
        colors = {
            'critical': '#DC3545',
            'high': '#FD7E14',
            'medium': '#FFC107',
            'low': '#28A745'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.priority, '#6C757D'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def mark_resolved(self, request, queryset):
        queryset.update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{queryset.count()} alerts marked as resolved.')
    mark_resolved.short_description = 'Mark selected alerts as resolved'
    
    def escalate_priority(self, request, queryset):
        for alert in queryset:
            if alert.priority == 'low':
                alert.priority = 'medium'
            elif alert.priority == 'medium':
                alert.priority = 'high'
            elif alert.priority == 'high':
                alert.priority = 'critical'
            alert.save()
        self.message_user(request, f'{queryset.count()} alerts escalated.')
    escalate_priority.short_description = 'Escalate priority'


@admin.register(ModeratedContent)
class ModeratedContentAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'content_author', 'moderated_by', 
                   'moderation_action', 'severity_badge', 'moderated_at']
    list_filter = ['content_type', 'moderation_action', 'severity', 'moderated_at']
    search_fields = ['content_id', 'original_content', 'reason']
    readonly_fields = ['id', 'moderated_at']
    date_hierarchy = 'moderated_at'
    
    fieldsets = (
        ('Content', {
            'fields': ('content_type', 'content_id', 'original_content', 'content_author')
        }),
        ('Moderation', {
            'fields': ('moderated_by', 'moderation_action', 'reason')
        }),
        ('Analysis Scores', {
            'fields': ('sentiment_score', 'toxicity_score', 'spam_score', 'severity'),
            'classes': ('collapse',)
        }),
    )
    
    def severity_badge(self, obj):
        colors = {
            'high': '#DC3545',
            'medium': '#FFC107',
            'low': '#28A745'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.severity, '#6C757D'),
            obj.severity.upper()
        )
    severity_badge.short_description = 'Severity'


@admin.register(SubAdminPerformance)
class SubAdminPerformanceAdmin(admin.ModelAdmin):
    list_display = ['subadmin', 'reports_handled_today', 'kyc_verified_today',
                   'accuracy_rate_display', 'avg_response_time_display', 'last_calculated']
    list_filter = ['last_calculated']
    search_fields = ['subadmin__username']
    readonly_fields = ['last_calculated']
    
    fieldsets = (
        ('SubAdmin', {
            'fields': ('subadmin',)
        }),
        ('Daily Metrics', {
            'fields': ('reports_handled_today', 'kyc_verified_today', 'avg_response_time')
        }),
        ('Weekly Metrics', {
            'fields': ('reports_handled_week', 'kyc_verified_week', 'false_positive_rate')
        }),
        ('Monthly Metrics', {
            'fields': ('reports_handled_month', 'kyc_verified_month', 'user_satisfaction_score')
        }),
        ('Overall Metrics', {
            'fields': ('total_reports_handled', 'total_kyc_verified', 
                      'total_warnings_issued', 'total_bans_issued')
        }),
        ('Quality Metrics', {
            'fields': ('accuracy_rate', 'appeal_overturn_rate')
        }),
    )
    
    actions = ['recalculate_metrics']
    
    def accuracy_rate_display(self, obj):
        return f"{obj.accuracy_rate:.1f}%"
    accuracy_rate_display.short_description = 'Accuracy'
    
    def avg_response_time_display(self, obj):
        if obj.avg_response_time < 1:
            return f"{int(obj.avg_response_time * 60)} min"
        return f"{obj.avg_response_time:.1f} hrs"
    avg_response_time_display.short_description = 'Avg Response'
    
    def recalculate_metrics(self, request, queryset):
        for performance in queryset:
            performance.calculate_metrics()
        self.message_user(request, f'Recalculated metrics for {queryset.count()} SubAdmins.')
    recalculate_metrics.short_description = 'Recalculate metrics'


# KYCDocument admin is already registered in apps.celebrities.admin