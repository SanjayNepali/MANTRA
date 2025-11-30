# apps/accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, UserFollowing, UserBlock, PointsHistory,
    LoginHistory, UserPreferences, SubAdminProfile, PasswordResetToken
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'user_type', 'points', 'rank', 'is_verified', 'verification_status', 'is_banned', 'created_at')
    list_filter = ('user_type', 'is_verified', 'verification_status', 'is_banned', 'is_active', 'is_online', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)
    readonly_fields = ('total_posts', 'total_followers', 'total_following', 'last_seen')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('MANTRA Info', {
            'fields': ('user_type', 'points', 'rank', 'bio', 'profile_picture', 'cover_image', 'date_of_birth', 'website')
        }),
        ('Verification & Status', {
            'fields': ('is_verified', 'verification_status', 'verification_badge')
        }),
        ('Ban & Restrictions', {
            'fields': ('is_banned', 'ban_reason', 'banned_at', 'banned_until', 'warnings_count')
        }),
        ('Activity Tracking', {
            'fields': ('last_seen', 'last_active', 'is_online', 'total_posts', 'total_followers', 'total_following')
        }),
        ('Location', {
            'fields': ('country', 'city', 'language')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('MANTRA Info', {
            'fields': ('user_type', 'email')
        }),
    )


@admin.register(UserFollowing)
class UserFollowingAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'is_close_friend', 'notifications_enabled', 'created_at')
    list_filter = ('is_close_friend', 'notifications_enabled', 'created_at')
    search_fields = ('follower__username', 'following__username')
    date_hierarchy = 'created_at'


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__username', 'blocked__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


@admin.register(PointsHistory)
class PointsHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'reason', 'balance_after', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'reason')
    date_hierarchy = 'created_at'


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'location', 'device_type', 'is_successful', 'login_time', 'logout_time')
    list_filter = ('is_successful', 'device_type', 'login_time')
    search_fields = ('user__username', 'ip_address', 'location')
    date_hierarchy = 'login_time'
    readonly_fields = ('login_time',)


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'language', 'who_can_message', 'who_can_see_posts', 'email_notifications', 'push_notifications')
    list_filter = ('theme', 'who_can_message', 'who_can_see_posts', 'email_notifications', 'push_notifications')
    search_fields = ('user__username',)
    fieldsets = (
        ('Display Settings', {
            'fields': ('theme', 'language', 'user_timezone')
        }),
        ('Content Preferences', {
            'fields': ('show_mature_content', 'show_adult_content', 'autoplay_videos', 'high_quality_media')
        }),
        ('Notification Settings', {
            'fields': ('email_notifications', 'push_notifications', 'notify_new_follower',
                      'notify_new_message', 'notify_new_comment', 'notify_new_like',
                      'notify_mentions', 'notify_celebrity_post', 'notify_event_reminder')
        }),
        ('Privacy Settings', {
            'fields': ('who_can_message', 'who_can_see_posts', 'who_can_see_followers', 'who_can_tag')
        }),
    )


@admin.register(SubAdminProfile)
class SubAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'region', 'assigned_by', 'kyc_handled', 'reports_resolved', 'users_banned')
    list_filter = ('region',)
    search_fields = ('user__username', 'region')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'created_at', 'expires_at', 'is_valid')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__username', 'token')
    readonly_fields = ('created_at', 'used_at')
    date_hierarchy = 'created_at'

    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'