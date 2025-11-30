# apps/celebrities/admin.py

from django.contrib import admin
from .models import (
    CelebrityCategory, CelebrityProfile, Subscription, KYCDocument,
    CelebrityEarning, CelebrityAnalytics, CelebrityAchievement, CelebrityContent
)

@admin.register(CelebrityProfile)
class CelebrityProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'stage_name', 'verification_status',
                   'default_subscription_price', 'total_earnings', 'created_at']
    list_filter = ['verification_status', 'created_at']
    search_fields = ['user__username', 'stage_name']
    readonly_fields = ['total_earnings', 'engagement_rate', 'total_subscribers']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['subscriber', 'celebrity', 'status', 'amount_paid', 
                   'start_date', 'end_date']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['subscriber__username', 'celebrity__user__username']
    date_hierarchy = 'created_at'


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ['celebrity', 'document_type', 'is_verified', 'uploaded_at']
    list_filter = ['document_type', 'is_verified']
    search_fields = ['celebrity__user__username']


@admin.register(CelebrityEarning)
class CelebrityEarningAdmin(admin.ModelAdmin):
    list_display = ['celebrity', 'amount', 'source_type', 'created_at']
    list_filter = ['source_type', 'created_at']
    search_fields = ['celebrity__user__username', 'description']
    date_hierarchy = 'created_at'


@admin.register(CelebrityAnalytics)
class CelebrityAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['celebrity', 'date', 'profile_visits', 'new_followers', 'total_revenue']
    list_filter = ['date']
    search_fields = ['celebrity__username']
    date_hierarchy = 'date'


@admin.register(CelebrityAchievement)
class CelebrityAchievementAdmin(admin.ModelAdmin):
    list_display = ['celebrity', 'title', 'achievement_type', 'threshold', 'is_unlocked']
    list_filter = ['achievement_type', 'is_unlocked']
    search_fields = ['celebrity__user__username', 'title']


@admin.register(CelebrityCategory)
class CelebrityCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Display', {
            'fields': ('is_active', 'display_order')
        }),
    )


@admin.register(CelebrityContent)
class CelebrityContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'celebrity', 'content_type', 'access_level', 'is_published',
                   'is_featured', 'views_count', 'likes_count', 'created_at']
    list_filter = ['content_type', 'access_level', 'is_published', 'is_featured', 'created_at']
    search_fields = ['title', 'description', 'celebrity__user__username']
    readonly_fields = ['views_count', 'likes_count', 'comments_count', 'shares_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('celebrity', 'title', 'description', 'content_type', 'access_level')
        }),
        ('Content', {
            'fields': ('content_file', 'thumbnail', 'external_url', 'duration', 'article_content')
        }),
        ('Monetization', {
            'fields': ('is_paid', 'price', 'is_free_preview', 'preview_duration')
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured', 'published_at', 'scheduled_for')
        }),
        ('Engagement', {
            'fields': ('views_count', 'likes_count', 'comments_count', 'shares_count'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('tags',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['publish_content', 'unpublish_content', 'feature_content', 'unfeature_content']

    def publish_content(self, request, queryset):
        updated = 0
        for content in queryset:
            if not content.is_published:
                content.publish()
                updated += 1
        self.message_user(request, f'{updated} content(s) published successfully.')
    publish_content.short_description = 'Publish selected content'

    def unpublish_content(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} content(s) unpublished successfully.')
    unpublish_content.short_description = 'Unpublish selected content'

    def feature_content(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} content(s) featured successfully.')
    feature_content.short_description = 'Feature selected content'

    def unfeature_content(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} content(s) unfeatured successfully.')
    unfeature_content.short_description = 'Unfeature selected content'