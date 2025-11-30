# apps/fans/admin.py

from django.contrib import admin
from .models import (
    FanProfile, FanActivity, FanRecommendation, FanBadge, FanBadgeEarned,
    FanCollection, FanReward, FanRewardClaim, FanWishlist, FanSubscriptionHistory
)

@admin.register(FanProfile)
class FanProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'fan_level', 'engagement_score', 'current_streak',
                   'total_celebrities_followed', 'loyalty_points', 'created_at']
    list_filter = ['fan_level', 'is_verified_fan', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['total_celebrities_followed', 'total_fanclubs_joined',
                      'total_events_attended', 'total_merchandise_bought',
                      'engagement_score', 'longest_streak']
    filter_horizontal = ['favorite_celebrities']

    fieldsets = (
        ('User Info', {
            'fields': ('user', 'fan_level', 'fan_since', 'is_verified_fan')
        }),
        ('Preferences', {
            'fields': ('favorite_categories', 'favorite_celebrities', 'interests',
                      'favorite_genres', 'preferred_content_types')
        }),
        ('Streak & Engagement', {
            'fields': ('current_streak', 'longest_streak', 'last_activity_date',
                      'engagement_score')
        }),
        ('Metrics', {
            'fields': ('loyalty_score', 'loyalty_points', 'total_interactions')
        }),
        ('Statistics', {
            'fields': ('total_celebrities_followed', 'total_fanclubs_joined',
                      'total_events_attended', 'total_merchandise_bought', 'total_spent',
                      'collected_items', 'merchandise_purchased', 'events_attended')
        }),
        ('Achievements', {
            'fields': ('badges', 'achievements_unlocked')
        }),
    )


@admin.register(FanActivity)
class FanActivityAdmin(admin.ModelAdmin):
    list_display = ['fan', 'activity_type', 'target_type', 'target_user', 'duration', 'created_at']
    list_filter = ['activity_type', 'target_type', 'device_type', 'created_at']
    search_fields = ['fan__username', 'description', 'location']
    date_hierarchy = 'created_at'
    readonly_fields = ['id', 'created_at']


@admin.register(FanRecommendation)
class FanRecommendationAdmin(admin.ModelAdmin):
    list_display = ['fan', 'recommended_celebrity', 'recommendation_score',
                   'is_viewed', 'is_followed', 'created_at']
    list_filter = ['is_viewed', 'is_followed', 'created_at']
    search_fields = ['fan__username', 'recommended_celebrity__username']
    readonly_fields = ['created_at']


@admin.register(FanBadge)
class FanBadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'badge_type', 'points_value', 'is_rare', 'is_active', 'created_at']
    list_filter = ['badge_type', 'is_rare', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-points_value', 'name']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'badge_type', 'icon', 'color')
        }),
        ('Requirements', {
            'fields': ('requirement_type', 'requirement_value', 'requirement_description')
        }),
        ('Rewards', {
            'fields': ('points_value', 'is_rare')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(FanBadgeEarned)
class FanBadgeEarnedAdmin(admin.ModelAdmin):
    list_display = ['fan', 'badge', 'progress', 'earned_at']
    list_filter = ['badge', 'earned_at']
    search_fields = ['fan__username', 'badge__name']
    date_hierarchy = 'earned_at'
    readonly_fields = ['earned_at']


@admin.register(FanCollection)
class FanCollectionAdmin(admin.ModelAdmin):
    list_display = ['fan', 'item_name', 'item_type', 'rarity', 'is_showcased',
                   'celebrity', 'acquired_date']
    list_filter = ['item_type', 'rarity', 'is_showcased', 'is_tradeable', 'acquired_date']
    search_fields = ['fan__username', 'item_name', 'celebrity__username']
    date_hierarchy = 'acquired_date'
    readonly_fields = ['id', 'created_at']

    fieldsets = (
        ('Item Info', {
            'fields': ('fan', 'item_name', 'item_type', 'description')
        }),
        ('Source', {
            'fields': ('celebrity', 'acquisition_method', 'acquired_date')
        }),
        ('Media', {
            'fields': ('image', 'file_url')
        }),
        ('Properties', {
            'fields': ('rarity', 'estimated_value', 'is_tradeable')
        }),
        ('Display', {
            'fields': ('is_showcased', 'display_order')
        }),
    )


@admin.register(FanReward)
class FanRewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'reward_type', 'points_required', 'quantity_available',
                   'quantity_claimed', 'is_active', 'celebrity_specific']
    list_filter = ['reward_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['quantity_claimed']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'reward_type', 'reward_value')
        }),
        ('Requirements', {
            'fields': ('points_required', 'min_fan_level', 'celebrity_specific')
        }),
        ('Availability', {
            'fields': ('is_active', 'quantity_available', 'quantity_claimed',
                      'valid_from', 'valid_until')
        }),
    )


@admin.register(FanRewardClaim)
class FanRewardClaimAdmin(admin.ModelAdmin):
    list_display = ['fan', 'reward', 'points_spent', 'redemption_code',
                   'is_used', 'claimed_at', 'expires_at']
    list_filter = ['is_used', 'claimed_at']
    search_fields = ['fan__username', 'reward__name', 'redemption_code']
    date_hierarchy = 'claimed_at'
    readonly_fields = ['claimed_at']


@admin.register(FanWishlist)
class FanWishlistAdmin(admin.ModelAdmin):
    list_display = ['fan', 'item_name', 'item_type', 'priority',
                   'notify_on_discount', 'added_at']
    list_filter = ['item_type', 'priority', 'notify_on_discount', 'added_at']
    search_fields = ['fan__username', 'item_name']
    date_hierarchy = 'added_at'
    readonly_fields = ['id', 'added_at', 'updated_at']

    fieldsets = (
        ('Item Info', {
            'fields': ('fan', 'item_type', 'item_id', 'item_name', 'item_data')
        }),
        ('Preferences', {
            'fields': ('priority', 'notes')
        }),
        ('Notifications', {
            'fields': ('notify_on_discount', 'notify_on_availability')
        }),
    )


@admin.register(FanSubscriptionHistory)
class FanSubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['fan', 'celebrity', 'action', 'subscription_type',
                   'amount', 'action_date']
    list_filter = ['action', 'subscription_type', 'action_date']
    search_fields = ['fan__username', 'celebrity__username', 'transaction_id']
    date_hierarchy = 'action_date'
    readonly_fields = ['id', 'created_at']

    fieldsets = (
        ('Parties', {
            'fields': ('fan', 'celebrity')
        }),
        ('Action Details', {
            'fields': ('action', 'subscription_type', 'action_date')
        }),
        ('Financial', {
            'fields': ('amount', 'payment_method', 'transaction_id')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Notes', {
            'fields': ('notes', 'reason')
        }),
    )