# apps/accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
import uuid

class User(AbstractUser):
    """Custom User model for MANTRA system"""
    
    USER_TYPES = (
        ('fan', 'Fan'),
        ('celebrity', 'Celebrity'),
        ('admin', 'Admin'),
        ('subadmin', 'Sub-Admin'),
    )

    VERIFICATION_STATUS = (
        ('unverified', 'Unverified'),
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='fan')
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True
    )

    # Profile fields
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='profiles/covers/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    website = models.URLField(blank=True)
    social_links = models.JSONField(default=dict, blank=True)

    # Location and preferences
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=50, default='en')

    # Add category field for celebrities
    category = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Celebrity category/genre"
    )

    # Points and ranking system
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    rank = models.CharField(max_length=50, blank=True)

    # Verification & Status
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='unverified'
    )
    verification_badge = models.BooleanField(default=False)

    # Account status
    is_active = models.BooleanField(default=True)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True)
    banned_at = models.DateTimeField(null=True, blank=True)
    banned_until = models.DateTimeField(null=True, blank=True)
    warnings_count = models.IntegerField(default=0)

    # Activity tracking
    last_seen = models.DateTimeField(default=timezone.now)
    last_active = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    total_posts = models.IntegerField(default=0)
    total_followers = models.IntegerField(default=0)
    total_following = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Privacy settings
    is_private = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_type', 'is_active']),
            models.Index(fields=['points']),
            models.Index(fields=['email']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

    def get_full_name(self):
        """Return user's full name or username"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def save(self, *args, **kwargs):
        """Override save to ensure superusers are always admin type"""
        # If user is superuser, ensure they are admin type
        if self.is_superuser:
            self.user_type = 'admin'
        super().save(*args, **kwargs)

    @property
    def is_celebrity(self):
        """Check if user is a celebrity"""
        return self.user_type == 'celebrity'

    @property
    def is_fan(self):
        """Check if user is a fan"""
        return self.user_type == 'fan'

    @property
    def is_admin_user(self):
        """Check if user is admin or sub-admin (superusers are always admins)"""
        return self.is_superuser or self.user_type in ['admin', 'subadmin']

    def get_profile_picture_url(self):
        """Return profile picture URL or default avatar"""
        if self.profile_picture:
            return self.profile_picture.url
        return '/static/images/default-avatar.png'

    def update_rank(self):
        """Update user rank based on points"""
        from django.conf import settings
        
        if self.user_type == 'fan':
            ranks = settings.MANTRA_SETTINGS['FAN_RANKS']
        elif self.user_type == 'celebrity':
            ranks = settings.MANTRA_SETTINGS['CELEBRITY_RANKS']
        else:
            return
        
        for rank_code, rank_name, min_points in reversed(ranks):
            if self.points >= min_points:
                self.rank = rank_name
                break
        
        self.save(update_fields=['rank'])
    
    def add_points(self, points, reason=""):
        """Add points to user account"""
        self.points += points
        self.save(update_fields=['points'])
        
        # Create points history
        PointsHistory.objects.create(
            user=self,
            points=points,
            reason=reason,
            balance_after=self.points
        )
        
        # Update rank
        self.update_rank()
    
    def deduct_points(self, points, reason=""):
        """Deduct points from user account"""
        if self.points >= points:
            self.points -= points
            self.save(update_fields=['points'])
            
            # Create points history
            PointsHistory.objects.create(
                user=self,
                points=-points,
                reason=reason,
                balance_after=self.points
            )
            
            # Update rank
            self.update_rank()
            return True
        return False
    
    def ban_user(self, reason, duration_days=None):
        """Ban user account"""
        self.is_banned = True
        self.ban_reason = reason
        self.banned_at = timezone.now()

        if duration_days:
            from datetime import timedelta
            self.banned_until = timezone.now() + timedelta(days=duration_days)

        self.save()
    
    def unban_user(self):
        """Unban user account"""
        self.is_banned = False
        self.ban_reason = ""
        self.banned_at = None
        self.banned_until = None
        self.save()
    
    def check_ban_status(self):
        """Check and update ban status"""
        if self.is_banned and self.banned_until:
            if timezone.now() > self.banned_until:
                self.unban_user()
                return False
        return self.is_banned

    @classmethod
    def create_superuser(cls, username, email, password, **extra_fields):
        """Override create_superuser to ensure user_type is admin"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return cls._create_user(username, email, password, **extra_fields)


class PointsHistory(models.Model):
    """Track points transactions for users"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points_history')
    points = models.IntegerField()  # Positive for earned, negative for deducted
    reason = models.CharField(max_length=200)
    balance_after = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        action = "earned" if self.points > 0 else "lost"
        return f"{self.user.username} {action} {abs(self.points)} points"


class LoginHistory(models.Model):
    """Track user login history"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)

    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)

    is_successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class UserFollowing(models.Model):
    """Handle following relationships between users"""

    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')

    # Additional fields
    is_close_friend = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['follower', 'following']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

    def save(self, *args, **kwargs):
        # Prevent users from following themselves
        if self.follower == self.following:
            raise ValueError("Users cannot follow themselves")
        super().save(*args, **kwargs)


class UserBlock(models.Model):
    """Block relationships between users"""

    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocking'
    )
    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by'
    )
    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['blocker', 'blocked']),
        ]

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"


class UserPreferences(models.Model):
    """Store user preferences and settings"""

    PRIVACY_CHOICES = (
        ('public', 'Public'),
        ('followers', 'Followers Only'),
        ('nobody', 'Nobody'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')

    # Display preferences
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', 'Light'),
        ('dark', 'Dark'),
    ])
    language = models.CharField(max_length=10, default='en')
    user_timezone = models.CharField(max_length=50, default='UTC')

    # Content preferences
    show_mature_content = models.BooleanField(default=False)
    show_adult_content = models.BooleanField(default=False)
    autoplay_videos = models.BooleanField(default=True)
    high_quality_media = models.BooleanField(default=False)

    # Notification settings
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    notify_new_follower = models.BooleanField(default=True)
    notify_new_message = models.BooleanField(default=True)
    notify_new_comment = models.BooleanField(default=True)
    notify_new_like = models.BooleanField(default=True)
    notify_mentions = models.BooleanField(default=True)
    notify_celebrity_post = models.BooleanField(default=True)
    notify_event_reminder = models.BooleanField(default=True)

    # Privacy settings
    who_can_message = models.CharField(max_length=20, default='followers', choices=PRIVACY_CHOICES)
    who_can_see_posts = models.CharField(max_length=20, default='public', choices=PRIVACY_CHOICES)
    who_can_see_followers = models.CharField(max_length=20, default='public', choices=PRIVACY_CHOICES)
    who_can_tag = models.CharField(max_length=20, default='followers', choices=PRIVACY_CHOICES)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"


class SubAdminProfile(models.Model):
    """Extended profile for sub-admins"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subadmin_profile')
    region = models.CharField(max_length=100)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='assigned_subadmins'
    )
    responsibilities = models.TextField()

    assigned_areas = models.JSONField(default=list, help_text="List of areas this subadmin manages")

    # Performance metrics
    kyc_handled = models.IntegerField(default=0)
    reports_resolved = models.IntegerField(default=0)
    users_banned = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['region']

    def __str__(self):
        return f"SubAdmin: {self.user.username} - {self.region}"


class PasswordResetToken(models.Model):
    """Custom password reset tokens"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Reset token for {self.user.username}"

    def is_valid(self):
        """Check if token is still valid"""
        return not self.is_used and self.expires_at > timezone.now()