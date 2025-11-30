# apps/reports/admin.py

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Report, ModerationAction

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'reported_by', 'target_user', 'report_type', 'reason',
                   'status', 'created_at', 'reviewed_by']
    list_filter = ['status', 'report_type', 'reason', 'created_at']
    search_fields = ['reported_by__username', 'target_user__username', 'description']
    readonly_fields = ['created_at', 'reviewed_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Report Info', {
            'fields': ('reported_by', 'report_type', 'reason', 'description')
        }),
        ('Target', {
            'fields': ('target_user', 'target_object_id')
        }),
        ('Evidence', {
            'fields': ('screenshot', 'additional_info'),
            'classes': ('collapse',)
        }),
        ('Status & Review', {
            'fields': ('status', 'reviewed_by', 'review_notes', 'action_taken')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_reviewing', 'mark_as_resolved', 'mark_as_dismissed']

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def mark_as_reviewing(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(status='reviewing', reviewed_by=request.user, reviewed_at=now)
        self.message_user(request, f'{updated} report(s) marked as under review.')
    mark_as_reviewing.short_description = 'Mark as Reviewing'

    def mark_as_resolved(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(status='resolved', reviewed_at=now)
        self.message_user(request, f'{updated} report(s) marked as resolved.')
    mark_as_resolved.short_description = 'Mark as Resolved'

    def mark_as_dismissed(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(status='dismissed', reviewed_at=now)
        self.message_user(request, f'{updated} report(s) dismissed.')
    mark_as_dismissed.short_description = 'Dismiss Reports'


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'target_user', 'performed_by', 'duration_days',
                   'expires_at', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['target_user__username', 'performed_by__username', 'reason']
    readonly_fields = ['created_at', 'expires_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Action Info', {
            'fields': ('performed_by', 'action_type', 'target_user')
        }),
        ('Related Report', {
            'fields': ('report',),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': ('reason', 'duration_days')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['extend_duration']

    def extend_duration(self, request, queryset):
        """Extend suspension duration by 7 days"""
        from datetime import timedelta
        for action in queryset:
            if action.expires_at:
                action.expires_at = action.expires_at + timedelta(days=7)
                action.duration_days = (action.duration_days or 0) + 7
                action.save()
        self.message_user(request, f'{queryset.count()} action(s) extended by 7 days.')
    extend_duration.short_description = 'Extend Duration by 7 Days'