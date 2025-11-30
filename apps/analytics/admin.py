# apps/analytics/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import PlatformAnalytics, UserEngagementMetrics

@admin.register(PlatformAnalytics)
class PlatformAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_users', 'new_users', 'active_users',
                   'total_posts', 'revenue_display', 'created_at']
    list_filter = ['date', 'created_at']
    search_fields = ['date']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'

    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('User Metrics', {
            'fields': ('total_users', 'new_users', 'active_users')
        }),
        ('Content Metrics', {
            'fields': ('total_posts', 'total_comments', 'total_likes')
        }),
        ('Revenue Metrics', {
            'fields': ('total_revenue', 'subscription_revenue', 'event_revenue', 'merchandise_revenue')
        }),
        ('Engagement Metrics', {
            'fields': ('average_session_duration', 'page_views'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def revenue_display(self, obj):
        return f"${obj.total_revenue:,.2f}"
    revenue_display.short_description = 'Total Revenue'

    def has_add_permission(self, request):
        """Prevent manual addition - should be generated automatically"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of analytics data"""
        return request.user.is_superuser


@admin.register(UserEngagementMetrics)
class UserEngagementMetricsAdmin(admin.ModelAdmin):
    list_display = ['user', 'engagement_score_badge', 'influence_score_badge',
                   'followers_count', 'total_posts', 'total_likes_received', 'last_calculated']
    list_filter = ['last_calculated']
    search_fields = ['user__username']
    readonly_fields = ['last_calculated']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Activity Metrics', {
            'fields': ('total_posts', 'total_comments', 'total_likes_given', 'total_likes_received')
        }),
        ('Engagement Scores', {
            'fields': ('engagement_score', 'influence_score')
        }),
        ('Time Metrics', {
            'fields': ('total_time_spent', 'average_session_duration'),
            'classes': ('collapse',)
        }),
        ('Network Metrics', {
            'fields': ('followers_count', 'following_count', 'mutual_connections')
        }),
        ('Timestamps', {
            'fields': ('last_calculated',),
            'classes': ('collapse',)
        }),
    )

    actions = ['recalculate_scores']

    def engagement_score_badge(self, obj):
        score = obj.engagement_score
        if score >= 75:
            color = '#28a745'  # Green - Excellent
        elif score >= 50:
            color = '#ffc107'  # Yellow - Good
        elif score >= 25:
            color = '#fd7e14'  # Orange - Average
        else:
            color = '#dc3545'  # Red - Low

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{:.1f}</span>',
            color, score
        )
    engagement_score_badge.short_description = 'Engagement'

    def influence_score_badge(self, obj):
        score = obj.influence_score
        if score >= 75:
            color = '#28a745'
            label = 'High'
        elif score >= 50:
            color = '#ffc107'
            label = 'Medium'
        elif score >= 25:
            color = '#fd7e14'
            label = 'Low'
        else:
            color = '#6c757d'
            label = 'Minimal'

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{} ({:.1f})</span>',
            color, label, score
        )
    influence_score_badge.short_description = 'Influence'

    def recalculate_scores(self, request, queryset):
        """Recalculate engagement and influence scores"""
        for metrics in queryset:
            metrics.calculate_engagement_score()
            metrics.calculate_influence_score()
        self.message_user(request, f'{queryset.count()} user metric(s) recalculated.')
    recalculate_scores.short_description = 'Recalculate Scores'