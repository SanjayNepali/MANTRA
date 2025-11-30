# apps/fans/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
import uuid

class FanProfile(models.Model):
    """Extended profile for fan users"""

    FAN_LEVELS = (
        ('casual', 'Casual Fan'),
        ('dedicated', 'Dedicated Fan'),
        ('super', 'Super Fan'),
        ('ultimate', 'Ultimate Fan'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fan_profile'
    )

    # Fan Level & Status
    fan_level = models.CharField(max_length=20, choices=FAN_LEVELS, default='casual')
    fan_since = models.DateField(default=timezone.now)
    is_verified_fan = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Preferences
    favorite_categories = models.JSONField(default=list)
    favorite_celebrities = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='top_fans',
        blank=True,
        limit_choices_to={'user_type': 'celebrity'}
    )
    interests = models.TextField(blank=True)  # Keeping as TextField to avoid migration issues
    interests_list = models.JSONField(default=list, blank=True)  # New JSON field for interests
    favorite_genres = models.JSONField(default=list, blank=True)
    preferred_content_types = models.JSONField(default=list, blank=True)

    # Activity tracking
    last_celebrity_followed = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recent_fan_followers'
    )

    # Streak Tracking (NEW - Gamification)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    # Activity Metrics
    engagement_score = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    loyalty_score = models.IntegerField(default=0)
    loyalty_points = models.IntegerField(default=0)
    total_interactions = models.IntegerField(default=0)

    # Statistics
    total_celebrities_followed = models.IntegerField(default=0)
    total_fanclubs_joined = models.IntegerField(default=0)
    total_events_attended = models.IntegerField(default=0)
    total_merchandise_bought = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Collection
    collected_items = models.IntegerField(default=0)
    merchandise_purchased = models.IntegerField(default=0)
    events_attended = models.IntegerField(default=0)

    # Achievements & Badges
    badges = models.JSONField(default=list, blank=True)
    achievements_unlocked = models.IntegerField(default=0)

    # Notification Preferences
    notification_preferences = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-engagement_score', '-user__points']
        indexes = [
            models.Index(fields=['fan_level']),
            models.Index(fields=['engagement_score']),
            models.Index(fields=['current_streak']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_fan_level_display()}"

    def update_statistics(self):
        """Update fan statistics"""
        from apps.accounts.models import UserFollowing
        from apps.fanclubs.models import FanClubMembership

        self.total_celebrities_followed = UserFollowing.objects.filter(
            follower=self.user,
            following__user_type='celebrity'
        ).count()

        self.total_fanclubs_joined = FanClubMembership.objects.filter(
            user=self.user
        ).count()

        self.save()

    def calculate_engagement_score(self):
        """Calculate fan engagement score"""
        from apps.posts.models import Like, Comment

        # Get engagement metrics
        likes = Like.objects.filter(user=self.user).count()
        comments = Comment.objects.filter(author=self.user).count()

        # Calculate weighted score
        score = min(100, (
            (likes * 0.2) +
            (comments * 0.3) +
            (self.total_fanclubs_joined * 10) +
            (self.events_attended * 5) +
            (float(self.total_spent) / 100) +
            (self.current_streak * 2)
        ))

        self.engagement_score = round(score, 2)
        self.save(update_fields=['engagement_score'])
        return score

    def update_fan_level(self):
        """Update fan level based on engagement"""
        if self.engagement_score >= 80:
            self.fan_level = 'ultimate'
        elif self.engagement_score >= 60:
            self.fan_level = 'super'
        elif self.engagement_score >= 30:
            self.fan_level = 'dedicated'
        else:
            self.fan_level = 'casual'

        self.save(update_fields=['fan_level'])

    def update_streak(self):
        """Update daily activity streak"""
        today = timezone.now().date()

        if self.last_activity_date:
            days_diff = (today - self.last_activity_date).days

            if days_diff == 0:
                # Already active today
                return self.current_streak
            elif days_diff == 1:
                # Consecutive day - increment streak
                self.current_streak += 1
                if self.current_streak > self.longest_streak:
                    self.longest_streak = self.current_streak
            else:
                # Streak broken
                self.current_streak = 1
        else:
            # First activity
            self.current_streak = 1
            self.longest_streak = 1

        self.last_activity_date = today
        self.save(update_fields=['current_streak', 'longest_streak', 'last_activity_date'])
        return self.current_streak


class FanActivity(models.Model):
    """Track fan activities for recommendations"""

    ACTIVITY_TYPES = (
        ('view', 'Viewed'),
        ('like', 'Liked'),
        ('comment', 'Commented'),
        ('share', 'Shared'),
        ('follow', 'Followed'),
        ('unfollow', 'Unfollowed'),
        ('join_club', 'Joined Club'),
        ('leave_club', 'Left Club'),
        ('purchase', 'Purchased'),
        ('attend_event', 'Attended Event'),
        ('subscription', 'Subscribed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fan_activities'
    )

    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)

    # Related objects (generic relation pattern)
    target_type = models.CharField(max_length=50, default='unknown')  # 'post', 'celebrity', 'event', etc.
    target_id = models.UUIDField(null=True, blank=True)
    target_data = models.JSONField(default=dict, blank=True)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fan_activity_targets'
    )

    # Metadata
    duration = models.IntegerField(null=True, blank=True)  # For view duration in seconds
    device_type = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['fan', '-created_at']),
            models.Index(fields=['activity_type', 'target_type']),
        ]
        verbose_name = 'Fan Activity'
        verbose_name_plural = 'Fan Activities'

    def __str__(self):
        return f"{self.fan.username} - {self.get_activity_type_display()}"


class FanRecommendation(models.Model):
    """Store personalized recommendations for fans"""
    
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    
    recommended_celebrity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommended_to_fans'
    )
    
    recommendation_score = models.FloatField()
    reason = models.CharField(max_length=200)
    
    # Interaction tracking
    is_viewed = models.BooleanField(default=False)
    is_followed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    followed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ('fan', 'recommended_celebrity')
        ordering = ['-recommendation_score', '-created_at']
        indexes = [
            models.Index(fields=['fan', 'is_viewed']),
            models.Index(fields=['-recommendation_score']),
        ]
    
    def __str__(self):
        return f"Recommend {self.recommended_celebrity.username} to {self.fan.username}"


class FanBadge(models.Model):
    """Badges that fans can earn"""

    BADGE_TYPES = (
        ('achievement', 'Achievement'),
        ('milestone', 'Milestone'),
        ('special', 'Special Event'),
        ('loyalty', 'Loyalty'),
        ('collection', 'Collection'),
    )

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES)

    icon = models.CharField(max_length=50)  # Boxicon class
    color = models.CharField(max_length=20, default='pink')

    # Requirements
    requirement_type = models.CharField(max_length=50)
    requirement_value = models.IntegerField(default=1)
    requirement_description = models.TextField()

    # Points and Rewards
    points_value = models.IntegerField(default=10)
    is_rare = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-points_value', 'name']
        verbose_name = 'Fan Badge'
        verbose_name_plural = 'Fan Badges'

    def __str__(self):
        return self.name


class FanBadgeEarned(models.Model):
    """Track badges earned by fans"""

    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='earned_badges'
    )
    badge = models.ForeignKey(FanBadge, on_delete=models.CASCADE, related_name='earned_by')

    earned_at = models.DateTimeField(default=timezone.now)
    progress = models.IntegerField(default=100)  # Percentage

    class Meta:
        unique_together = ('fan', 'badge')
        ordering = ['-earned_at']
        verbose_name = 'Fan Badge Earned'
        verbose_name_plural = 'Fan Badges Earned'

    def __str__(self):
        return f"{self.fan.username} - {self.badge.name}"


class FanCollection(models.Model):
    """Fan's collection of digital items"""

    ITEM_TYPES = (
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('autograph', 'Digital Autograph'),
        ('badge', 'Special Badge'),
        ('nft', 'NFT'),
        ('memorabilia', 'Digital Memorabilia'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collection'
    )

    item_name = models.CharField(max_length=200)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    description = models.TextField(blank=True)

    # Source
    celebrity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fan_collectibles'
    )

    # Media
    image = models.ImageField(upload_to='collections/', blank=True, null=True)
    file_url = models.URLField(blank=True)

    # Value and Rarity
    rarity = models.CharField(max_length=20, default='common')
    estimated_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_tradeable = models.BooleanField(default=False)

    # Acquisition
    acquired_date = models.DateTimeField(default=timezone.now)
    acquisition_method = models.CharField(max_length=50)  # 'purchase', 'gift', 'achievement'

    # Display
    is_showcased = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['fan', 'item_type']),
            models.Index(fields=['is_showcased', 'display_order']),
        ]
        verbose_name = 'Fan Collection Item'
        verbose_name_plural = 'Fan Collection Items'

    def __str__(self):
        return f"{self.fan.username}'s {self.item_name}"


class FanReward(models.Model):
    """Loyalty rewards for fans"""

    name = models.CharField(max_length=100)
    description = models.TextField()
    points_required = models.IntegerField(default=100)

    # Reward Details
    reward_type = models.CharField(max_length=50)  # 'discount', 'exclusive_content', 'merchandise'
    reward_value = models.JSONField(default=dict)

    # Availability
    is_active = models.BooleanField(default=True)
    quantity_available = models.IntegerField(default=-1)  # -1 for unlimited
    quantity_claimed = models.IntegerField(default=0)

    # Restrictions
    celebrity_specific = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fan_rewards'
    )
    min_fan_level = models.CharField(max_length=20, blank=True)

    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['points_required', 'name']
        verbose_name = 'Fan Reward'
        verbose_name_plural = 'Fan Rewards'

    def __str__(self):
        return f"{self.name} ({self.points_required} points)"

    def is_available(self):
        """Check if reward is currently available"""
        if not self.is_active:
            return False
        if self.quantity_available != -1 and self.quantity_claimed >= self.quantity_available:
            return False
        if self.valid_until and self.valid_until < timezone.now():
            return False
        return True


class FanRewardClaim(models.Model):
    """Track reward claims by fans"""

    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reward_claims'
    )
    reward = models.ForeignKey(FanReward, on_delete=models.CASCADE, related_name='claims')

    points_spent = models.IntegerField()

    # Status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    # Redemption Code
    redemption_code = models.CharField(max_length=20, unique=True)

    claimed_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-claimed_at']
        verbose_name = 'Fan Reward Claim'
        verbose_name_plural = 'Fan Reward Claims'

    def __str__(self):
        return f"{self.fan.username} - {self.reward.name}"


class FanWishlist(models.Model):
    """Track items fans want to purchase or attend"""

    ITEM_TYPES = (
        ('event', 'Event'),
        ('merchandise', 'Merchandise'),
        ('content', 'Premium Content'),
        ('subscription', 'Subscription'),
    )

    PRIORITY_LEVELS = (
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist'
    )

    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    item_id = models.UUIDField()
    item_name = models.CharField(max_length=200)
    item_data = models.JSONField(default=dict, blank=True)

    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    notes = models.TextField(blank=True)

    # Notifications
    notify_on_discount = models.BooleanField(default=True)
    notify_on_availability = models.BooleanField(default=True)

    added_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['fan', 'item_type']),
            models.Index(fields=['priority', '-added_at']),
        ]
        verbose_name = 'Fan Wishlist Item'
        verbose_name_plural = 'Fan Wishlist Items'

    def __str__(self):
        return f"{self.fan.username}'s wishlist - {self.item_name}"


class FanSubscriptionHistory(models.Model):
    """Track fan subscription lifecycle"""

    SUBSCRIPTION_ACTIONS = (
        ('subscribed', 'Subscribed'),
        ('renewed', 'Renewed'),
        ('upgraded', 'Upgraded'),
        ('downgraded', 'Downgraded'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )

    SUBSCRIPTION_TYPES = (
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('vip', 'VIP'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_history'
    )
    celebrity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fan_subscription_history'
    )

    action = models.CharField(max_length=20, choices=SUBSCRIPTION_ACTIONS)
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES)

    # Financial
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    # Dates
    action_date = models.DateTimeField(default=timezone.now)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    # Metadata
    notes = models.TextField(blank=True)
    reason = models.CharField(max_length=200, blank=True)  # For cancellations

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['fan', '-created_at']),
            models.Index(fields=['celebrity', 'action']),
            models.Index(fields=['action', '-created_at']),
        ]
        verbose_name = 'Fan Subscription History'
        verbose_name_plural = 'Fan Subscription Histories'

    def __str__(self):
        return f"{self.fan.username} - {self.get_action_display()} - {self.celebrity.username}"