# apps/celebrities/models.py

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.text import slugify
import uuid

User = get_user_model()


class CelebrityCategory(models.Model):
    """Categories for celebrities (Actor, Singer, Athlete, etc.)"""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # Boxicon class (e.g., 'bx-movie', 'bx-music')

    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Celebrity Category'
        verbose_name_plural = 'Celebrity Categories'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'display_order']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CelebrityProfile(models.Model):
    """Extended profile for celebrities with customization features"""

    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='celebrity_profile')
    stage_name = models.CharField(max_length=100, blank=True)
    categories = models.JSONField(default=list, help_text="List of celebrity categories")

    # Verification
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_celebrities')
    verification_notes = models.TextField(blank=True, help_text="Notes from SubAdmin during verification")
    needs_resubmission = models.BooleanField(default=False)
    resubmission_requested_at = models.DateTimeField(null=True, blank=True)
    document_submitted_at = models.DateTimeField(null=True, blank=True)
    # Profile customization
    bio_extended = models.TextField(max_length=2000, blank=True)
    achievements = models.JSONField(default=list, help_text="List of achievements")
    social_links = models.JSONField(default=dict, help_text="Social media links")

    # Subscription customization
    subscription_tiers = models.JSONField(default=dict, help_text="Custom subscription tiers with pricing")
    subscription_description = models.TextField(max_length=1000, blank=True)
    subscription_benefits = models.JSONField(default=list, help_text="List of subscription benefits")
    default_subscription_price = models.DecimalField(max_digits=10, decimal_places=2, default=9.99)

    # Content settings
    allow_fan_posts = models.BooleanField(default=True)
    fan_post_approval_required = models.BooleanField(default=False)
    exclusive_content_enabled = models.BooleanField(default=True)
    exclusive_content_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # E-commerce settings
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.0,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    auto_approve_products = models.BooleanField(default=False)
    product_categories = models.JSONField(default=list, help_text="Allowed product categories")
    max_product_price = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    shipping_regions = models.JSONField(default=list, help_text="Regions where shipping is available")

    # Theme customization
    custom_theme = models.JSONField(default=dict, help_text="Custom theme colors and styles")
    profile_layout = models.CharField(max_length=50, default='default', choices=[
        ('default', 'Default'),
        ('grid', 'Grid Layout'),
        ('timeline', 'Timeline Layout'),
        ('magazine', 'Magazine Layout'),
    ])

    # Moderation settings
    moderation_level = models.CharField(max_length=20, choices=[
        ('low', 'Low - Basic filtering'),
        ('medium', 'Medium - Standard moderation'),
        ('high', 'High - Strict moderation'),
        ('custom', 'Custom rules'),
    ], default='medium')
    blocked_words = models.JSONField(default=list, help_text="Custom list of blocked words")
    auto_ban_threshold = models.IntegerField(default=5, help_text="Number of violations before auto-ban")

    # Fan interaction settings
    allow_direct_messages = models.BooleanField(default=True)
    dm_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Price for DM if > 0")
    allow_video_calls = models.BooleanField(default=False)
    video_call_price = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    allow_comments = models.BooleanField(default=True)
    comment_approval_required = models.BooleanField(default=False)

    # Analytics visibility
    show_follower_count = models.BooleanField(default=True)
    show_engagement_rate = models.BooleanField(default=True)
    show_trending_status = models.BooleanField(default=True)

    # Payment settings
    payment_methods = models.JSONField(default=list, help_text="Accepted payment methods")
    payout_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ], default='weekly')
    bank_account_details = models.JSONField(default=dict, help_text="Encrypted bank details")

    # Event settings
    event_booking_enabled = models.BooleanField(default=True)
    min_event_price = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    event_cancellation_policy = models.TextField(max_length=500, blank=True)

    # Statistics
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_subscribers = models.IntegerField(default=0)
    engagement_rate = models.FloatField(default=0)
    average_rating = models.FloatField(default=0)

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['verification_status']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Celebrity Profile: {self.user.username}"

    def get_subscription_tiers(self):
        """Get formatted subscription tiers"""
        default_tiers = {
            'basic': {
                'name': 'Basic Fan',
                'price': float(self.default_subscription_price),
                'benefits': ['Access to exclusive posts', 'Monthly newsletter']
            },
            'premium': {
                'name': 'Premium Fan',
                'price': float(self.default_subscription_price) * 2,
                'benefits': ['All Basic benefits', 'Weekly live streams', 'Priority messaging']
            },
            'vip': {
                'name': 'VIP Fan',
                'price': float(self.default_subscription_price) * 5,
                'benefits': ['All Premium benefits', 'Monthly video call', 'Exclusive merchandise']
            }
        }

        # Merge with custom tiers
        return {**default_tiers, **self.subscription_tiers}

    def get_theme_colors(self):
        """Get theme colors with defaults"""
        default_theme = {
            'primary': '#9caf88',  # Sage green
            'secondary': '#d4a5a5',  # Pink
            'accent': '#8b7355',  # Brown
            'background': '#f8f9fa',
            'text': '#333333'
        }

        return {**default_theme, **self.custom_theme}

    def update_statistics(self):
        """Update celebrity statistics"""
        from apps.fanclubs.models import FanClubMembership
        from apps.posts.models import Post

        # Update subscriber count
        self.total_subscribers = FanClubMembership.objects.filter(
            fanclub__celebrity=self.user,
            is_active=True
        ).count()

        # Calculate engagement rate
        recent_posts = Post.objects.filter(
            author=self.user,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        )

        if recent_posts.exists():
            total_engagement = sum(
                post.likes_count + post.comments_count + post.shares_count
                for post in recent_posts
            )
            total_views = sum(post.views_count for post in recent_posts)

            if total_views > 0:
                self.engagement_rate = (total_engagement / total_views) * 100

        self.save()


class CelebrityKYC(models.Model):
    """KYC verification documents for celebrities"""

    DOCUMENT_TYPES = (
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('national_id', 'National ID'),
        ('voter_id', 'Voter ID'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )

    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=50)
    document_front = models.ImageField(upload_to='kyc/documents/')
    document_back = models.ImageField(upload_to='kyc/documents/', null=True, blank=True)

    # Additional documents
    selfie_with_document = models.ImageField(upload_to='kyc/selfies/')
    proof_of_profession = models.FileField(upload_to='kyc/profession/', null=True, blank=True)

    # Verification details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reviewed_kycs')
    review_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Document validity
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    # Metadata
    submitted_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['celebrity', 'document_type', 'document_number']

    def __str__(self):
        return f"KYC: {self.celebrity.username} - {self.document_type}"

    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False


class CelebrityBankAccount(models.Model):
    """Bank account details for celebrity payouts"""

    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    account_holder_name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)

    # eSewa details
    esewa_id = models.CharField(max_length=20, blank=True)
    esewa_verified = models.BooleanField(default=False)

    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.celebrity.username} - {self.bank_name}"

    def save(self, *args, **kwargs):
        # Ensure only one primary account
        if self.is_primary:
            CelebrityBankAccount.objects.filter(
                celebrity=self.celebrity,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)

        super().save(*args, **kwargs)


class CelebrityAnalytics(models.Model):
    """Daily analytics for celebrity accounts"""

    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(default=timezone.now)

    # Follower metrics
    new_followers = models.IntegerField(default=0)
    lost_followers = models.IntegerField(default=0)
    total_followers = models.IntegerField(default=0)

    # Engagement metrics
    post_views = models.IntegerField(default=0)
    post_likes = models.IntegerField(default=0)
    post_comments = models.IntegerField(default=0)
    post_shares = models.IntegerField(default=0)
    profile_visits = models.IntegerField(default=0)

    # Revenue metrics
    subscription_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    merchandise_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    event_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tips_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Content metrics
    posts_created = models.IntegerField(default=0)
    exclusive_posts = models.IntegerField(default=0)
    events_created = models.IntegerField(default=0)
    products_added = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']
        unique_together = ['celebrity', 'date']
        indexes = [
            models.Index(fields=['celebrity', '-date']),
        ]

    def __str__(self):
        return f"{self.celebrity.username} - {self.date}"

    def calculate_totals(self):
        """Calculate total revenue"""
        self.total_revenue = (
            self.subscription_revenue +
            self.merchandise_revenue +
            self.event_revenue +
            self.tips_revenue
        )
        self.save()


class CelebritySettings(models.Model):
    """Advanced settings for celebrity accounts"""

    celebrity = models.OneToOneField(User, on_delete=models.CASCADE, related_name='celebrity_settings')

    # Content automation
    auto_publish_schedule = models.JSONField(default=dict, help_text="Schedule for auto-publishing content")
    draft_reminders = models.BooleanField(default=True)
    content_calendar_enabled = models.BooleanField(default=True)

    # Fan engagement automation
    auto_thank_new_subscribers = models.BooleanField(default=True)
    welcome_message_template = models.TextField(max_length=500, blank=True)
    birthday_greetings_enabled = models.BooleanField(default=True)

    # Analytics preferences
    weekly_analytics_email = models.BooleanField(default=True)
    monthly_revenue_report = models.BooleanField(default=True)
    competitor_analysis = models.BooleanField(default=False)

    # Advanced features
    ai_content_suggestions = models.BooleanField(default=True)
    ai_response_assistant = models.BooleanField(default=False)
    sentiment_monitoring = models.BooleanField(default=True)

    # Integration settings
    third_party_integrations = models.JSONField(default=dict)
    api_access_enabled = models.BooleanField(default=False)
    api_key = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Celebrity Settings'
        verbose_name_plural = 'Celebrity Settings'

    def __str__(self):
        return f"Settings: {self.celebrity.username}"


class Subscription(models.Model):
    """Fan subscriptions to celebrities"""

    SUBSCRIPTION_STATUS = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
    )

    subscriber = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='celebrity_subscriptions')

    tier = models.CharField(max_length=50, default='basic')
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='pending')

    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='esewa')
    transaction_id = models.CharField(max_length=100, blank=True)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscriber', 'status']),
            models.Index(fields=['celebrity', 'status']),
        ]

    def __str__(self):
        return f"{self.subscriber.username} -> {self.celebrity.username}"

    def is_active(self):
        return self.status == 'active' and self.end_date > timezone.now()


class KYCDocument(models.Model):
    """KYC verification documents - alias for CelebrityKYC"""

    DOCUMENT_TYPES = (
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('national_id', 'National ID'),
        ('voter_id', 'Voter ID'),
        ('proof_of_address', 'Proof of Address'),
        ('professional_certificate', 'Professional Certificate'),
        ('other', 'Other'),
    )

    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_docs')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=100, blank=True)
    document_file = models.FileField(upload_to='kyc/')
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.celebrity.username} - {self.document_type}"

class CelebrityEarning(models.Model):
    """Track earnings for celebrities"""

    SOURCE_TYPES = (
        ('subscription', 'Subscription'),
        ('merchandise', 'Merchandise'),
        ('event', 'Event'),
        ('tip', 'Tip'),
        ('message', 'Paid Message'),
        ('content', 'Premium Content'),
    )

    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earnings')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    description = models.TextField(blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['celebrity', '-created_at']),
        ]

    def __str__(self):
        return f"{self.celebrity.username} - Rs. {self.amount}"


class CelebrityAchievement(models.Model):
    """Achievements and milestones for celebrities"""

    ACHIEVEMENT_TYPES = (
        ('followers', 'Follower Milestone'),
        ('earnings', 'Earnings Milestone'),
        ('posts', 'Content Milestone'),
        ('engagement', 'Engagement Milestone'),
        ('special', 'Special Achievement'),
    )

    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=100)
    description = models.TextField()
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    threshold = models.IntegerField(help_text="Threshold value to unlock")
    icon = models.CharField(max_length=50, blank=True)
    is_unlocked = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    points_reward = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['is_unlocked', '-unlocked_at']

    def __str__(self):
        return f"{self.celebrity.username} - {self.title}"


class CelebrityContent(models.Model):
    """Premium content created by celebrities"""

    CONTENT_TYPES = (
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('image', 'Image'),
        ('article', 'Article'),
        ('live', 'Live Stream'),
    )

    ACCESS_LEVELS = (
        ('public', 'Public'),
        ('subscribers', 'Subscribers Only'),
        ('premium', 'Premium Tier'),
        ('vip', 'VIP Only'),
    )

    celebrity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='premium_content')
    title = models.CharField(max_length=200)
    description = models.TextField()
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='subscribers')

    content_file = models.FileField(upload_to='celebrity_content/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='content_thumbnails/', null=True, blank=True)
    external_url = models.URLField(blank=True)
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")
    article_content = models.TextField(blank=True)

    is_paid = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_free_preview = models.BooleanField(default=False)
    preview_duration = models.IntegerField(null=True, blank=True)

    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)

    views_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)

    tags = models.JSONField(default=list)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['celebrity', '-created_at']),
            models.Index(fields=['is_published', '-published_at']),
        ]

    def __str__(self):
        return f"{self.celebrity.username} - {self.title}"

    def publish(self):
        """Publish the content"""
        self.is_published = True
        self.published_at = timezone.now()
        self.save()
