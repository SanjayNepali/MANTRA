# apps/posts/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import (
    Post, Like, Comment, CommentLike, Share, PostReport,
    PostSave, PostMention, PostBookmark
)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'title_preview', 'post_type', 'visibility', 'likes_count',
                   'comments_count', 'views_count', 'is_featured', 'is_active',
                   'is_scheduled', 'created_at']
    list_filter = ['post_type', 'visibility', 'is_exclusive', 'is_featured', 'is_active',
                  'is_reported', 'is_scheduled', 'created_at']
    search_fields = ['author__username', 'title', 'content', 'location']
    readonly_fields = ['likes_count', 'comments_count', 'shares_count', 'views_count',
                      'saves_count', 'created_at', 'updated_at', 'edited_at', 'published_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Author', {
            'fields': ('author',)
        }),
        ('Content', {
            'fields': ('title', 'content', 'post_type')
        }),
        ('Media', {
            'fields': ('image', 'video', 'thumbnail', 'media_files', 'attachments')
        }),
        ('Visibility & Settings', {
            'fields': ('visibility', 'is_exclusive', 'is_featured', 'allow_comments',
                      'allow_sharing')
        }),
        ('Poll Settings', {
            'fields': ('poll_options', 'poll_votes', 'poll_ends_at', 'allow_multiple_votes'),
            'classes': ('collapse',)
        }),
        ('Location', {
            'fields': ('location', 'coordinates'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_pinned', 'is_reported', 'is_edited', 'is_scheduled')
        }),
        ('Engagement', {
            'fields': ('likes_count', 'comments_count', 'shares_count', 'views_count', 'saves_count'),
            'classes': ('collapse',)
        }),
        ('Tags & Mentions', {
            'fields': ('tags', 'mentioned_users'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('scheduled_for', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['feature_posts', 'unfeature_posts', 'pin_posts', 'unpin_posts', 'deactivate_posts']

    def title_preview(self, obj):
        return obj.title[:50] if obj.title else obj.content[:50]
    title_preview.short_description = 'Title/Content'

    def feature_posts(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} post(s) featured.')
    feature_posts.short_description = 'Feature selected posts'

    def unfeature_posts(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} post(s) unfeatured.')
    unfeature_posts.short_description = 'Unfeature selected posts'

    def pin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated} post(s) pinned.')
    pin_posts.short_description = 'Pin selected posts'

    def unpin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'{updated} post(s) unpinned.')
    unpin_posts.short_description = 'Unpin selected posts'

    def deactivate_posts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} post(s) deactivated.')
    deactivate_posts.short_description = 'Deactivate selected posts'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'post__content']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'content_preview', 'parent', 'likes_count',
                   'replies_count', 'is_pinned', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_reported', 'is_pinned', 'is_edited', 'created_at']
    search_fields = ['author__username', 'content', 'post__content']
    readonly_fields = ['likes_count', 'replies_count', 'created_at', 'updated_at', 'edited_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('post', 'author', 'parent')
        }),
        ('Content', {
            'fields': ('content', 'image', 'gif_url')
        }),
        ('Status', {
            'fields': ('is_active', 'is_reported', 'is_edited', 'is_pinned')
        }),
        ('Engagement', {
            'fields': ('likes_count', 'replies_count'),
            'classes': ('collapse',)
        }),
        ('Mentions', {
            'fields': ('mentioned_users',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['pin_comments', 'unpin_comments', 'deactivate_comments']

    def content_preview(self, obj):
        return obj.content[:50]
    content_preview.short_description = 'Content'

    def pin_comments(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated} comment(s) pinned.')
    pin_comments.short_description = 'Pin selected comments'

    def unpin_comments(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'{updated} comment(s) unpinned.')
    unpin_comments.short_description = 'Unpin selected comments'

    def deactivate_comments(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} comment(s) deactivated.')
    deactivate_comments.short_description = 'Deactivate selected comments'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'comment', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'comment__content']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'text_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'text', 'post__content']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']

    def text_preview(self, obj):
        return obj.text[:50] if obj.text else '-'
    text_preview.short_description = 'Share Text'


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ['post_preview', 'reported_by', 'reason', 'is_reviewed',
                   'action_taken', 'reviewed_by', 'created_at']
    list_filter = ['reason', 'is_reviewed', 'action_taken', 'created_at']
    search_fields = ['post__content', 'reported_by__username', 'description']
    readonly_fields = ['created_at', 'reviewed_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Report Info', {
            'fields': ('post', 'reported_by', 'reason', 'description', 'additional_context')
        }),
        ('Review', {
            'fields': ('is_reviewed', 'reviewed_by', 'action_taken', 'action_notes', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_reviewed', 'mark_content_removed', 'mark_no_action']

    def post_preview(self, obj):
        return obj.post.content[:30] if obj.post else '-'
    post_preview.short_description = 'Post'

    def mark_as_reviewed(self, request, queryset):
        queryset.update(is_reviewed=True, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f'{queryset.count()} report(s) marked as reviewed.')
    mark_as_reviewed.short_description = 'Mark as reviewed'

    def mark_content_removed(self, request, queryset):
        queryset.update(
            is_reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            action_taken='content_removed'
        )
        self.message_user(request, f'{queryset.count()} report(s) marked as content removed.')
    mark_content_removed.short_description = 'Mark as content removed'

    def mark_no_action(self, request, queryset):
        queryset.update(
            is_reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            action_taken='no_action'
        )
        self.message_user(request, f'{queryset.count()} report(s) marked as no action.')
    mark_no_action.short_description = 'Mark as no action'


@admin.register(PostSave)
class PostSaveAdmin(admin.ModelAdmin):
    list_display = ['user', 'post_preview', 'collection_name', 'created_at']
    list_filter = ['collection_name', 'created_at']
    search_fields = ['user__username', 'post__content', 'notes']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'post')
        }),
        ('Organization', {
            'fields': ('collection_name', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def post_preview(self, obj):
        return obj.post.content[:30] if obj.post else '-'
    post_preview.short_description = 'Post'


@admin.register(PostMention)
class PostMentionAdmin(admin.ModelAdmin):
    list_display = ['mentioned_user', 'mentioned_by', 'post', 'is_seen',
                   'is_notified', 'created_at']
    list_filter = ['is_seen', 'is_notified', 'created_at']
    search_fields = ['mentioned_user__username', 'mentioned_by__username']
    readonly_fields = ['created_at', 'seen_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Mention Info', {
            'fields': ('post', 'mentioned_user', 'mentioned_by')
        }),
        ('Notification', {
            'fields': ('is_notified', 'is_seen', 'seen_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    actions = ['mark_as_seen']

    def mark_as_seen(self, request, queryset):
        queryset.update(is_seen=True, seen_at=timezone.now())
        self.message_user(request, f'{queryset.count()} mention(s) marked as seen.')
    mark_as_seen.short_description = 'Mark as seen'


@admin.register(PostBookmark)
class PostBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'post_preview', 'collection_type', 'collection_name',
                   'is_favorite', 'reminder_date', 'created_at']
    list_filter = ['collection_type', 'is_favorite', 'reminder_sent', 'created_at']
    search_fields = ['user__username', 'post__content', 'collection_name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'post')
        }),
        ('Collection', {
            'fields': ('collection_type', 'collection_name', 'tags', 'notes')
        }),
        ('Organization', {
            'fields': ('is_favorite', 'reminder_date', 'reminder_sent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    actions = ['mark_as_favorite', 'clear_reminders']

    def post_preview(self, obj):
        return obj.post.content[:30] if obj.post else '-'
    post_preview.short_description = 'Post'

    def mark_as_favorite(self, request, queryset):
        updated = queryset.update(is_favorite=True)
        self.message_user(request, f'{updated} bookmark(s) marked as favorite.')
    mark_as_favorite.short_description = 'Mark as favorite'

    def clear_reminders(self, request, queryset):
        updated = queryset.update(reminder_date=None, reminder_sent=False)
        self.message_user(request, f'{updated} bookmark reminder(s) cleared.')
    clear_reminders.short_description = 'Clear reminders'