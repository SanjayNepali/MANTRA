# apps/fanclubs/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import (
    FanClub, FanClubMembership, FanClubPost, FanClubEvent,
    FanClubInvitation, FanClubAnnouncement
)

@admin.register(FanClub)
class FanClubAdmin(admin.ModelAdmin):
    list_display = ['name', 'celebrity', 'club_type', 'visibility', 'members_count',
                   'active_members_count', 'is_paid', 'rank', 'is_active', 'created_at']
    list_filter = ['club_type', 'visibility', 'is_active', 'is_private', 'is_paid', 'created_at']
    search_fields = ['name', 'celebrity__username', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['members_count', 'posts_count', 'active_members_count',
                      'total_engagement', 'rank', 'total_points', 'created_at', 'updated_at']
    filter_horizontal = []
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('celebrity', 'name', 'slug', 'description', 'welcome_message', 'rules')
        }),
        ('Type & Visibility', {
            'fields': ('club_type', 'visibility', 'is_private', 'is_active')
        }),
        ('Settings', {
            'fields': ('requires_approval', 'allow_member_posts', 'allow_member_invites', 'min_fan_level')
        }),
        ('Monetization', {
            'fields': ('is_paid', 'membership_fee')
        }),
        ('Media', {
            'fields': ('cover_image', 'icon', 'banner_image')
        }),
        ('Statistics', {
            'fields': ('members_count', 'active_members_count', 'posts_count', 'total_engagement'),
            'classes': ('collapse',)
        }),
        ('Ranking & Achievements', {
            'fields': ('rank', 'total_points', 'badges', 'achievements'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('tags', 'featured_members'),
            'classes': ('collapse',)
        }),
        ('Rename History', {
            'fields': ('last_renamed', 'rename_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_clubs', 'deactivate_clubs']

    def activate_clubs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} club(s) activated successfully.')
    activate_clubs.short_description = 'Activate selected clubs'

    def deactivate_clubs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} club(s) deactivated successfully.')
    deactivate_clubs.short_description = 'Deactivate selected clubs'


@admin.register(FanClubMembership)
class FanClubMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'fanclub', 'role', 'tier', 'status', 'contribution_points',
                   'current_streak', 'joined_at']
    list_filter = ['role', 'tier', 'status', 'joined_at']
    search_fields = ['user__username', 'fanclub__name']
    readonly_fields = ['posts_count', 'comments_count', 'likes_given', 'events_attended',
                      'current_streak', 'longest_streak', 'joined_at']
    date_hierarchy = 'joined_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'fanclub', 'status', 'role', 'tier')
        }),
        ('Activity & Engagement', {
            'fields': ('contribution_points', 'posts_count', 'comments_count',
                      'likes_given', 'events_attended', 'last_active')
        }),
        ('Streak Tracking', {
            'fields': ('current_streak', 'longest_streak')
        }),
        ('Achievements', {
            'fields': ('badges_earned', 'achievements'),
            'classes': ('collapse',)
        }),
        ('Customization', {
            'fields': ('custom_title', 'profile_color'),
            'classes': ('collapse',)
        }),
        ('Ban Info', {
            'fields': ('banned_at', 'ban_reason', 'ban_expires_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['promote_to_moderator', 'demote_to_member', 'ban_members', 'unban_members']

    def promote_to_moderator(self, request, queryset):
        updated = queryset.update(role='moderator')
        self.message_user(request, f'{updated} member(s) promoted to moderator.')
    promote_to_moderator.short_description = 'Promote to Moderator'

    def demote_to_member(self, request, queryset):
        updated = queryset.update(role='member')
        self.message_user(request, f'{updated} member(s) demoted to member.')
    demote_to_member.short_description = 'Demote to Member'

    def ban_members(self, request, queryset):
        queryset.update(status='banned', banned_at=timezone.now())
        self.message_user(request, f'{queryset.count()} member(s) banned.')
    ban_members.short_description = 'Ban selected members'

    def unban_members(self, request, queryset):
        queryset.update(status='active', banned_at=None, ban_reason='', ban_expires_at=None)
        self.message_user(request, f'{queryset.count()} member(s) unbanned.')
    unban_members.short_description = 'Unban selected members'


@admin.register(FanClubPost)
class FanClubPostAdmin(admin.ModelAdmin):
    list_display = ['fanclub', 'author', 'post_type', 'content_preview', 'is_announcement',
                   'is_pinned', 'is_approved', 'likes_count', 'comments_count', 'created_at']
    list_filter = ['post_type', 'is_announcement', 'is_pinned', 'is_active', 'is_reported',
                  'is_approved', 'created_at']
    search_fields = ['author__username', 'content', 'fanclub__name']
    readonly_fields = ['likes_count', 'comments_count', 'shares_count', 'views_count',
                      'created_at', 'updated_at', 'edited_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('fanclub', 'author', 'post_type')
        }),
        ('Content', {
            'fields': ('content', 'image', 'video', 'attachments')
        }),
        ('Poll Settings', {
            'fields': ('poll_options', 'poll_votes', 'poll_ends_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_pinned', 'is_announcement', 'is_active', 'is_reported', 'is_approved')
        }),
        ('Moderation', {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('Engagement', {
            'fields': ('likes_count', 'comments_count', 'shares_count', 'views_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['pin_posts', 'unpin_posts', 'approve_posts', 'mark_as_announcement']

    def content_preview(self, obj):
        return obj.content[:50]
    content_preview.short_description = 'Content'

    def pin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated} post(s) pinned.')
    pin_posts.short_description = 'Pin selected posts'

    def unpin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'{updated} post(s) unpinned.')
    unpin_posts.short_description = 'Unpin selected posts'

    def approve_posts(self, request, queryset):
        queryset.update(is_approved=True, approved_by=request.user, approved_at=timezone.now())
        self.message_user(request, f'{queryset.count()} post(s) approved.')
    approve_posts.short_description = 'Approve selected posts'

    def mark_as_announcement(self, request, queryset):
        updated = queryset.update(is_announcement=True, post_type='announcement')
        self.message_user(request, f'{updated} post(s) marked as announcement.')
    mark_as_announcement.short_description = 'Mark as Announcement'


@admin.register(FanClubEvent)
class FanClubEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'fanclub', 'event_type', 'status', 'event_date', 'is_online',
                   'participants_count', 'max_participants', 'is_featured', 'created_at']
    list_filter = ['event_type', 'status', 'is_online', 'is_active', 'is_cancelled',
                  'is_featured', 'created_at']
    search_fields = ['title', 'description', 'fanclub__name', 'location']
    readonly_fields = ['participants_count', 'created_at', 'updated_at']
    date_hierarchy = 'event_date'

    fieldsets = (
        ('Basic Info', {
            'fields': ('fanclub', 'title', 'description', 'event_type', 'created_by')
        }),
        ('Date & Time', {
            'fields': ('event_date', 'end_date')
        }),
        ('Location', {
            'fields': ('is_online', 'location', 'address', 'meeting_link')
        }),
        ('Media', {
            'fields': ('cover_image', 'thumbnail')
        }),
        ('Participation', {
            'fields': ('max_participants', 'participants_count', 'min_tier', 'requires_approval')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'is_cancelled', 'cancellation_reason', 'is_featured')
        }),
        ('Reminders', {
            'fields': ('reminder_sent', 'reminder_sent_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('tags', 'custom_fields'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_featured', 'cancel_events', 'mark_as_completed']

    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} event(s) marked as featured.')
    mark_as_featured.short_description = 'Mark as Featured'

    def cancel_events(self, request, queryset):
        queryset.update(is_cancelled=True, status='cancelled')
        self.message_user(request, f'{queryset.count()} event(s) cancelled.')
    cancel_events.short_description = 'Cancel selected events'

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} event(s) marked as completed.')
    mark_as_completed.short_description = 'Mark as Completed'


@admin.register(FanClubInvitation)
class FanClubInvitationAdmin(admin.ModelAdmin):
    list_display = ['invited_user', 'fanclub', 'invited_by', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at']
    search_fields = ['invited_user__username', 'invited_by__username', 'fanclub__name']
    readonly_fields = ['created_at', 'responded_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('fanclub', 'invited_by', 'invited_user')
        }),
        ('Status', {
            'fields': ('status', 'message')
        }),
        ('Dates', {
            'fields': ('expires_at', 'created_at', 'responded_at')
        }),
    )

    actions = ['mark_as_expired']

    def mark_as_expired(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='expired')
        self.message_user(request, f'{updated} invitation(s) marked as expired.')
    mark_as_expired.short_description = 'Mark as Expired'


@admin.register(FanClubAnnouncement)
class FanClubAnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'fanclub', 'priority', 'is_active', 'is_pinned',
                   'send_notification', 'created_by', 'created_at']
    list_filter = ['priority', 'is_active', 'is_pinned', 'send_notification', 'created_at']
    search_fields = ['title', 'content', 'fanclub__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('fanclub', 'created_by', 'title', 'content', 'priority')
        }),
        ('Targeting', {
            'fields': ('target_tiers', 'target_roles')
        }),
        ('Media & Action', {
            'fields': ('image', 'action_url', 'action_text')
        }),
        ('Status', {
            'fields': ('is_active', 'is_pinned', 'send_notification')
        }),
        ('Scheduling', {
            'fields': ('published_at', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_announcements', 'deactivate_announcements', 'pin_announcements']

    def activate_announcements(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} announcement(s) activated.')
    activate_announcements.short_description = 'Activate selected announcements'

    def deactivate_announcements(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} announcement(s) deactivated.')
    deactivate_announcements.short_description = 'Deactivate selected announcements'

    def pin_announcements(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated} announcement(s) pinned.')
    pin_announcements.short_description = 'Pin selected announcements'