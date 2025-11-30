# apps/notifications/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import Notification, NotificationPreference, SystemAnnouncement

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'sender', 'notification_type', 'message_preview',
                   'is_read', 'created_at', 'read_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'sender__username', 'message', 'description']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Recipients & Sender', {
            'fields': ('recipient', 'sender')
        }),
        ('Notification Content', {
            'fields': ('notification_type', 'message', 'description')
        }),
        ('Target', {
            'fields': ('target_id', 'target_url'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    actions = ['mark_as_read', 'mark_as_unread', 'delete_selected_notifications']

    def message_preview(self, obj):
        return obj.message[:50] if obj.message else '-'
    message_preview.short_description = 'Message'

    def mark_as_read(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(is_read=False).update(is_read=True, read_at=now)
        self.message_user(request, f'{updated} notification(s) marked as read.')
    mark_as_read.short_description = 'Mark as Read'

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notification(s) marked as unread.')
    mark_as_unread.short_description = 'Mark as Unread'

    def delete_selected_notifications(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} notification(s) deleted.')
    delete_selected_notifications.short_description = 'Delete Selected Notifications'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_messages', 'email_events', 'push_messages',
                   'push_events', 'quiet_hours_enabled', 'updated_at']
    list_filter = ['quiet_hours_enabled', 'email_messages', 'push_messages', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Notifications', {
            'fields': ('email_follows', 'email_likes', 'email_comments',
                      'email_messages', 'email_events', 'email_system')
        }),
        ('Push Notifications', {
            'fields': ('push_follows', 'push_likes', 'push_comments',
                      'push_messages', 'push_events', 'push_system')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['enable_all_email', 'disable_all_email', 'enable_all_push', 'disable_all_push']

    def enable_all_email(self, request, queryset):
        updated = queryset.update(
            email_follows=True, email_likes=True, email_comments=True,
            email_messages=True, email_events=True, email_system=True
        )
        self.message_user(request, f'{updated} preference(s) updated - all email enabled.')
    enable_all_email.short_description = 'Enable All Email Notifications'

    def disable_all_email(self, request, queryset):
        updated = queryset.update(
            email_follows=False, email_likes=False, email_comments=False,
            email_messages=False, email_events=False, email_system=False
        )
        self.message_user(request, f'{updated} preference(s) updated - all email disabled.')
    disable_all_email.short_description = 'Disable All Email Notifications'

    def enable_all_push(self, request, queryset):
        updated = queryset.update(
            push_follows=True, push_likes=True, push_comments=True,
            push_messages=True, push_events=True, push_system=True
        )
        self.message_user(request, f'{updated} preference(s) updated - all push enabled.')
    enable_all_push.short_description = 'Enable All Push Notifications'

    def disable_all_push(self, request, queryset):
        updated = queryset.update(
            push_follows=False, push_likes=False, push_comments=False,
            push_messages=False, push_events=False, push_system=False
        )
        self.message_user(request, f'{updated} preference(s) updated - all push disabled.')
    disable_all_push.short_description = 'Disable All Push Notifications'


@admin.register(SystemAnnouncement)
class SystemAnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'target_user_type', 'is_active',
                   'show_until', 'created_by', 'created_at']
    list_filter = ['priority', 'target_user_type', 'is_active', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'created_by']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Announcement Content', {
            'fields': ('title', 'content', 'priority')
        }),
        ('Targeting', {
            'fields': ('target_user_type',)
        }),
        ('Display Settings', {
            'fields': ('is_active', 'show_until')
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_announcements', 'deactivate_announcements']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new announcement
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def activate_announcements(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} announcement(s) activated.')
    activate_announcements.short_description = 'Activate Announcements'

    def deactivate_announcements(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} announcement(s) deactivated.')
    deactivate_announcements.short_description = 'Deactivate Announcements'