# apps/fanclubs/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
import uuid

class FanClub(models.Model):
    """Fan club model for celebrities"""

    CLUB_TYPES = (
        ('default', 'Default'),
        ('exclusive', 'Exclusive'),
        ('premium', 'Premium'),
        ('vip', 'VIP'),
    )

    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
        ('hidden', 'Hidden'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    celebrity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fanclubs'
    )

    # Group chat conversation
    group_chat = models.OneToOneField(
        'messaging.Conversation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fanclub'
    )

    # Club info
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(max_length=1000)
    welcome_message = models.TextField(max_length=500, blank=True)
    rules = models.TextField(blank=True)
    club_type = models.CharField(max_length=20, choices=CLUB_TYPES, default='default')

    # Club settings
    is_active = models.BooleanField(default=True)
    is_private = models.BooleanField(default=False)
    is_official = models.BooleanField(default=False)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    requires_approval = models.BooleanField(default=False)
    allow_member_posts = models.BooleanField(default=True)
    allow_member_invites = models.BooleanField(default=True)
    min_fan_level = models.CharField(max_length=20, blank=True)  # Minimum fan level to join

    # Monetization
    is_paid = models.BooleanField(default=False)
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Club images
    cover_image = models.ImageField(upload_to='fanclubs/covers/', null=True, blank=True)
    icon = models.ImageField(upload_to='fanclubs/icons/', null=True, blank=True)
    banner_image = models.ImageField(upload_to='fanclubs/banners/', null=True, blank=True)

    # Statistics
    members_count = models.IntegerField(default=0)
    posts_count = models.IntegerField(default=0)
    active_members_count = models.IntegerField(default=0)
    total_engagement = models.IntegerField(default=0)

    # Ranking & Achievements
    rank = models.IntegerField(default=0)  # Global fanclub ranking
    total_points = models.IntegerField(default=0)
    badges = models.JSONField(default=list, blank=True)
    achievements = models.JSONField(default=dict, blank=True)

    # Rename tracking
    last_renamed = models.DateTimeField(null=True, blank=True)
    rename_count = models.IntegerField(default=0)

    # Additional metadata
    tags = models.JSONField(default=list, blank=True)
    featured_members = models.JSONField(default=list, blank=True)  # List of featured member UUIDs

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-members_count', '-created_at']
        indexes = [
            models.Index(fields=['celebrity', 'club_type']),
            models.Index(fields=['slug']),
            models.Index(fields=['celebrity', 'is_official']),  # Added index
        ]
        constraints = [  # Added constraints block
            models.UniqueConstraint(
                fields=['celebrity', 'is_official'],
                condition=models.Q(is_official=True),
                name='unique_official_fanclub_per_celebrity'
            )
        ]
    
    def __str__(self):
        return f"{self.name} - {self.celebrity.username}"

    def get_image_url(self):
        """Return fanclub image URL (icon, cover_image, or placeholder)"""
        if self.icon:
            return self.icon.url
        elif self.cover_image:
            return self.cover_image.url
        return '/static/images/placeholderclub.png'
    
    def can_post(self, user):
        """Check if user can post in this fanclub"""
        if self.is_official:
            # Only celebrity can post in official fanclub
            return user == self.celebrity
        else:
            # In non-official fanclubs, check allow_member_posts setting
            if user == self.celebrity:
                return True
            if self.allow_member_posts:
                # Check if user is a member
                from .models import FanClubMembership  # Import here to avoid circular import
                return FanClubMembership.objects.filter(
                    fanclub=self,
                    user=user,
                    status='active'
                ).exists()
            return False
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.celebrity.username}")

        is_new = self._state.adding
        
        # Validate: Only one official fanclub per celebrity
        if self.is_official and is_new:
            existing = FanClub.objects.filter(
                celebrity=self.celebrity,
                is_official=True
            ).exclude(pk=self.pk).first()
            
            if existing:
                raise ValueError(f"Official fanclub already exists for {self.celebrity.username}")
        
        super().save(*args, **kwargs)

        # Create group chat conversation for new fan clubs
        if is_new and not self.group_chat:
            from apps.messaging.models import Conversation
            conversation = Conversation.objects.create(
                title=self.name,
                is_group=True,
                group_admin=self.celebrity,
                group_image=self.icon,
                is_fanclub=True,
                fanclub_celebrity=self.celebrity
            )
            conversation.participants.add(self.celebrity)
            self.group_chat = conversation
            super().save(update_fields=['group_chat'])
    
    def can_rename(self):
        """Check if fanclub can be renamed (once per month)"""
        if not self.last_renamed:
            return True
        
        from datetime import timedelta
        one_month_ago = timezone.now() - timedelta(days=30)
        return self.last_renamed < one_month_ago
    
    def rename(self, new_name):
        """Rename the fanclub"""
        if not self.can_rename():
            return False
        
        self.name = new_name
        self.slug = slugify(f"{new_name}-{self.celebrity.username}")
        self.last_renamed = timezone.now()
        self.rename_count += 1
        self.save()
        return True
    
    def add_member(self, user):
        """Add member to fanclub"""
        from .models import FanClubMembership  # Import here to avoid circular import
        
        membership, created = FanClubMembership.objects.get_or_create(
            user=user,
            fanclub=self,
            defaults={'status': 'active'}
        )

        if created:
            self.members_count += 1
            self.save(update_fields=['members_count'])

            # Add user to group chat
            if self.group_chat:
                self.group_chat.participants.add(user)

        return membership
    
    def remove_member(self, user):
        """Remove member from fanclub"""
        from .models import FanClubMembership  # Import here to avoid circular import
        
        try:
            membership = FanClubMembership.objects.get(user=user, fanclub=self)
            membership.delete()

            self.members_count = max(0, self.members_count - 1)
            self.save(update_fields=['members_count'])

            # Remove user from group chat
            if self.group_chat and user != self.celebrity:
                self.group_chat.participants.remove(user)

            return True
        except FanClubMembership.DoesNotExist:
            return False
class FanClubMembership(models.Model):
    """Membership model for fanclubs"""

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('banned', 'Banned'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    )

    ROLE_CHOICES = (
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
        ('co_owner', 'Co-Owner'),
    )

    TIER_CHOICES = (
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fanclub_memberships'
    )
    fanclub = models.ForeignKey(
        FanClub,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    # Membership details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='bronze')

    # Activity & Engagement
    contribution_points = models.IntegerField(default=0)
    posts_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    likes_given = models.IntegerField(default=0)
    events_attended = models.IntegerField(default=0)
    last_active = models.DateTimeField(null=True, blank=True)

    # Streak tracking
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)

    # Achievements
    badges_earned = models.JSONField(default=list, blank=True)
    achievements = models.JSONField(default=dict, blank=True)

    # Customization
    custom_title = models.CharField(max_length=100, blank=True)
    profile_color = models.CharField(max_length=7, blank=True)  # Hex color code

    # Timestamps
    joined_at = models.DateTimeField(default=timezone.now)
    banned_at = models.DateTimeField(null=True, blank=True)
    ban_reason = models.TextField(blank=True)
    ban_expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'fanclub')
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['fanclub', 'status']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.fanclub.name}"
    
    def ban(self, reason=''):
        """Ban member from fanclub"""
        self.status = 'banned'
        self.banned_at = timezone.now()
        self.ban_reason = reason
        self.save()
    
    def unban(self):
        """Unban member"""
        self.status = 'active'
        self.banned_at = None
        self.ban_reason = ''
        self.save()
    
    def promote(self, new_role):
        """Promote member to new role"""
        if new_role in ['moderator', 'admin']:
            self.role = new_role
            self.save()


class FanClubPost(models.Model):
    """Posts in fanclubs"""

    POST_TYPES = (
        ('regular', 'Regular'),
        ('announcement', 'Announcement'),
        ('poll', 'Poll'),
        ('event', 'Event'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fanclub = models.ForeignKey(
        FanClub,
        on_delete=models.CASCADE,
        related_name='fanclub_posts'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fanclub_posts'
    )

    # Content
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='regular')
    content = models.TextField(max_length=2000)
    image = models.ImageField(upload_to='fanclubs/posts/', null=True, blank=True)
    video = models.FileField(upload_to='fanclubs/videos/', null=True, blank=True)
    attachments = models.JSONField(default=list, blank=True)

    # For polls
    poll_options = models.JSONField(default=list, blank=True)
    poll_votes = models.JSONField(default=dict, blank=True)
    poll_ends_at = models.DateTimeField(null=True, blank=True)

    # Engagement
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)

    # Status
    is_pinned = models.BooleanField(default=False)
    is_announcement = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_reported = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)  # For moderated clubs

    # Moderation
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_fanclub_posts'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['fanclub', '-created_at']),
            models.Index(fields=['author']),
        ]
    
    def __str__(self):
        return f"Post in {self.fanclub.name} by {self.author.username}"


class FanClubEvent(models.Model):
    """Events organized by fanclubs"""

    EVENT_TYPES = (
        ('meetup', 'Meetup'),
        ('virtual', 'Virtual Event'),
        ('watch_party', 'Watch Party'),
        ('contest', 'Contest'),
        ('ama', 'AMA (Ask Me Anything)'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fanclub = models.ForeignKey(
        FanClub,
        on_delete=models.CASCADE,
        related_name='events'
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='meetup')

    # Event details
    event_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    is_online = models.BooleanField(default=False)
    meeting_link = models.URLField(blank=True)

    # Media
    cover_image = models.ImageField(upload_to='fanclubs/events/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='fanclubs/events/thumbnails/', null=True, blank=True)

    # Participation
    max_participants = models.IntegerField(null=True, blank=True)
    participants_count = models.IntegerField(default=0)
    min_tier = models.CharField(max_length=20, blank=True)  # Minimum membership tier
    requires_approval = models.BooleanField(default=False)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_active = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)

    # Reminders
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='organized_fanclub_events'
    )
    
    class Meta:
        ordering = ['event_date']
        indexes = [
            models.Index(fields=['fanclub', 'event_date']),
            models.Index(fields=['status', 'event_date']),
        ]

    def __str__(self):
        return f"{self.title} - {self.fanclub.name}"


class FanClubInvitation(models.Model):
    """Invitation model for fanclubs"""

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fanclub = models.ForeignKey(
        FanClub,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_fanclub_invitations'
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_fanclub_invitations'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(max_length=500, blank=True)
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('fanclub', 'invited_user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invited_user', 'status']),
            models.Index(fields=['fanclub', 'status']),
        ]

    def __str__(self):
        return f"Invitation to {self.fanclub.name} for {self.invited_user.username}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def accept(self):
        if self.status == 'pending' and not self.is_expired():
            self.status = 'accepted'
            self.responded_at = timezone.now()
            self.save()
            self.fanclub.add_member(self.invited_user)
            return True
        return False

    def decline(self):
        if self.status == 'pending':
            self.status = 'declined'
            self.responded_at = timezone.now()
            self.save()
            return True
        return False


class FanClubAnnouncement(models.Model):
    """Special announcements for fanclubs"""

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fanclub = models.ForeignKey(
        FanClub,
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_fanclub_announcements'
    )

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')

    # Targeting
    target_tiers = models.JSONField(default=list, blank=True)  # Which tiers to show to
    target_roles = models.JSONField(default=list, blank=True)  # Which roles to show to

    # Media
    image = models.ImageField(upload_to='fanclubs/announcements/', null=True, blank=True)
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    send_notification = models.BooleanField(default=True)

    # Scheduling
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-priority', '-created_at']
        indexes = [
            models.Index(fields=['fanclub', '-created_at']),
            models.Index(fields=['is_active', 'is_pinned']),
        ]

    def __str__(self):
        return f"Announcement: {self.title} - {self.fanclub.name}"

    def is_visible(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.published_at and self.published_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True