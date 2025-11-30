# apps/celebrities/serializers.py

from rest_framework import serializers
from django.conf import settings
from apps.accounts.serializers import UserSerializer
from .models import (
    CelebrityCategory, CelebrityProfile, Subscription, KYCDocument,
    CelebrityEarning, CelebrityAnalytics, CelebrityAchievement, CelebrityContent
)

class CelebrityProfileSerializer(serializers.ModelSerializer):
    """Serializer for celebrity profiles"""
    
    user = UserSerializer(read_only=True)
    subscribers_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    
    class Meta:
        model = CelebrityProfile
        fields = [
            'id', 'user', 'stage_name', 'category', 'bio_extended',
            'verification_status', 'subscription_fee', 'subscription_description',
            'subscribers_count', 'is_subscribed', 'total_earnings',
            'website', 'instagram', 'twitter', 'facebook', 'youtube', 'tiktok',
            'total_views', 'total_likes', 'engagement_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'verification_status', 'total_earnings', 'total_views',
            'total_likes', 'engagement_rate'
        ]
    
    def get_subscribers_count(self, obj):
        return obj.subscription_records.filter(status='active').count()
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                subscriber=request.user,
                celebrity=obj,
                status='active'
            ).exists()
        return False


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions"""
    
    subscriber = UserSerializer(read_only=True)
    celebrity_details = CelebrityProfileSerializer(source='celebrity', read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'subscriber', 'celebrity', 'celebrity_details',
            'start_date', 'end_date', 'status', 'amount_paid',
            'payment_method', 'auto_renew', 'created_at'
        ]
        read_only_fields = ['start_date', 'created_at']


class KYCDocumentSerializer(serializers.ModelSerializer):
    """Serializer for KYC documents"""
    
    class Meta:
        model = KYCDocument
        fields = [
            'id', 'document_type', 'document_file', 'document_number',
            'is_verified', 'uploaded_at', 'verified_at'
        ]
        read_only_fields = ['is_verified', 'verified_at']


class CelebrityEarningSerializer(serializers.ModelSerializer):
    """Serializer for celebrity earnings"""
    
    class Meta:
        model = CelebrityEarning
        fields = [
            'id', 'amount', 'description', 'source_type',
            'source_id', 'created_at'
        ]
        read_only_fields = '__all__'


class CelebrityAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for celebrity analytics"""
    
    class Meta:
        model = CelebrityAnalytics
        fields = '__all__'
        read_only_fields = '__all__'


class CelebrityAchievementSerializer(serializers.ModelSerializer):
    """Serializer for achievements"""

    class Meta:
        model = CelebrityAchievement
        fields = [
            'id', 'title', 'description', 'icon', 'achievement_type',
            'threshold', 'is_unlocked', 'unlocked_at', 'points_reward',
            'badge_color'
        ]


class CelebrityCategorySerializer(serializers.ModelSerializer):
    """Serializer for celebrity categories"""

    celebrities_count = serializers.SerializerMethodField()

    class Meta:
        model = CelebrityCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'is_active', 'display_order', 'celebrities_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def get_celebrities_count(self, obj):
        return obj.celebrity_profiles.filter(
            verification_status='approved'
        ).count()


class CelebrityContentSerializer(serializers.ModelSerializer):
    """Serializer for celebrity content"""

    celebrity_name = serializers.CharField(source='celebrity.user.username', read_only=True)
    celebrity_stage_name = serializers.CharField(source='celebrity.stage_name', read_only=True)
    can_access = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = CelebrityContent
        fields = [
            'id', 'celebrity', 'celebrity_name', 'celebrity_stage_name',
            'title', 'description', 'content_type', 'access_level',
            'content_file', 'thumbnail', 'external_url', 'duration',
            'article_content', 'views_count', 'likes_count',
            'comments_count', 'shares_count', 'is_paid', 'price',
            'is_free_preview', 'preview_duration', 'is_published',
            'is_featured', 'published_at', 'scheduled_for', 'tags',
            'can_access', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'views_count', 'likes_count', 'comments_count', 'shares_count',
            'published_at', 'created_at', 'updated_at'
        ]

    def get_can_access(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_access(request.user)
        return obj.access_level == 'free'

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # This would need a ContentLike model, placeholder for now
            return False
        return False


class CelebrityContentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for content lists"""

    celebrity_name = serializers.CharField(source='celebrity.user.username', read_only=True)

    class Meta:
        model = CelebrityContent
        fields = [
            'id', 'celebrity', 'celebrity_name', 'title', 'content_type',
            'access_level', 'thumbnail', 'duration', 'views_count',
            'likes_count', 'is_featured', 'published_at'
        ]