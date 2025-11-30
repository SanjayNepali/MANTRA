# apps/posts/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
import uuid

class Post(models.Model):
    """Post model for user content"""

    POST_TYPES = (
        ('regular', 'Regular'),
        ('exclusive', 'Exclusive'),
        ('announcement', 'Announcement'),
        ('poll', 'Poll'),
        ('question', 'Question'),
        ('celebration', 'Celebration'),
        ('merch', 'Merchandise'),
        ('event', 'Event'),
    )

    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('followers', 'Followers Only'),
        ('subscribers', 'Subscribers Only'),
        ('private', 'Private'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )

    # Content
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(max_length=5000)
    image = models.ImageField(upload_to='posts/', null=True, blank=True)
    video = models.FileField(upload_to='posts/videos/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='posts/thumbnails/', null=True, blank=True)

    # Multiple media support
    media_files = models.JSONField(default=list, blank=True)  # Array of media URLs
    attachments = models.JSONField(default=list, blank=True)  # Documents, files

    # Post settings
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='regular')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    is_exclusive = models.BooleanField(default=False)  # For subscribers only
    is_pinned = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    allow_comments = models.BooleanField(default=True)
    allow_sharing = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    # Related content for special post types
    related_merchandise_id = models.UUIDField(null=True, blank=True, help_text="Reference to Merchandise if post_type='merch'")
    related_event_id = models.UUIDField(null=True, blank=True, help_text="Reference to Event if post_type='event'")
    merch_category = models.CharField(max_length=50, blank=True, help_text="Merch category for filtering merch feed")

    # Poll settings
    poll_options = models.JSONField(default=list, blank=True)
    poll_votes = models.JSONField(default=dict, blank=True)
    poll_ends_at = models.DateTimeField(null=True, blank=True)
    allow_multiple_votes = models.BooleanField(default=False)

    # Location
    location = models.CharField(max_length=200, blank=True)
    coordinates = models.JSONField(default=dict, blank=True)  # lat, lng

    # Engagement
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    saves_count = models.IntegerField(default=0)

    # Status
    is_active = models.BooleanField(default=True)
    is_reported = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_scheduled = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Tags & Mentions
    tags = models.JSONField(default=list, blank=True)
    mentioned_users = models.JSONField(default=list, blank=True)  # List of user IDs

    # Sentiment Analysis
    sentiment_score = models.FloatField(default=0.0, help_text="Sentiment score from -1 (negative) to 1 (positive)")
    sentiment_label = models.CharField(
        max_length=20,
        choices=[('positive', 'Positive'), ('negative', 'Negative'), ('neutral', 'Neutral')],
        default='neutral'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['post_type']),
        ]
    
    def __str__(self):
        return f"{self.author.username} - {self.content[:50]}"

    def clean(self):
        """Validate post data"""
        from django.core.exceptions import ValidationError
        errors = {}

        # Validate poll posts have poll_options
        if self.post_type == 'poll':
            if not self.poll_options or len(self.poll_options) < 2:
                errors['poll_options'] = 'Poll posts must have at least 2 options'

        # Validate scheduled_for is in the future
        if self.is_scheduled and self.scheduled_for:
            if self.scheduled_for <= timezone.now():
                errors['scheduled_for'] = 'Scheduled time must be in the future'

        # Validate exclusive posts only for celebrities
        if self.is_exclusive and hasattr(self.author, 'user_type'):
            if self.author.user_type != 'celebrity':
                errors['is_exclusive'] = 'Only celebrities can create exclusive posts'

        # Validate content length
        if not self.content or len(self.content.strip()) == 0:
            errors['content'] = 'Post content cannot be empty'

        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self):
        """Get absolute URL for this post"""
        from django.urls import reverse
        return reverse('post_detail', kwargs={'pk': str(self.id)})

    def can_view(self, user):
        """Check if user can view this post"""
        if not self.is_active:
            return False
        
        if self.is_exclusive:
            if not user.is_authenticated:
                return False
            
            if self.author == user:
                return True
            
            # Check if user is subscribed (for celebrity exclusive posts)
            if self.author.user_type == 'celebrity':
                from apps.celebrities.models import Subscription
                try:
                    subscription = Subscription.objects.get(
                        subscriber=user,
                        celebrity=self.author.celebrity_profile
                    )
                    return subscription.is_active()
                except Subscription.DoesNotExist:
                    return False
        
        return True
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])


class Like(models.Model):
    """Like model for posts"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} likes {self.post.id}"


class Comment(models.Model):
    """Comment model for posts"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    # Content
    content = models.TextField(max_length=1000)
    image = models.ImageField(upload_to='comments/', null=True, blank=True)
    gif_url = models.URLField(blank=True)

    # Reply to comment
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    # Engagement
    likes_count = models.IntegerField(default=0)
    replies_count = models.IntegerField(default=0)

    # Status
    is_active = models.BooleanField(default=True)
    is_reported = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)  # Pinned by author
    is_blocked = models.BooleanField(default=False, help_text="Blocked due to high toxicity")

    # Mentions
    mentioned_users = models.JSONField(default=list, blank=True)

    # AI Sentiment Analysis
    toxicity_score = models.FloatField(default=0.0, help_text="Toxicity score 0-1")
    spam_score = models.FloatField(default=0.0, help_text="Spam score 0-1")
    sentiment_score = models.FloatField(default=0.0, help_text="Sentiment score from -1 (negative) to 1 (positive)")
    sentiment_label = models.CharField(
        max_length=20,
        choices=[('positive', 'Positive'), ('negative', 'Negative'), ('neutral', 'Neutral')],
        default='neutral'
    )
    ai_flagged = models.BooleanField(default=False, help_text="Flagged by AI for review")
    ai_flag_reason = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
            models.Index(fields=['author']),
        ]
    
    def __str__(self):
        return f"{self.author.username} on {self.post.id}: {self.content[:30]}"


class CommentLike(models.Model):
    """Like model for comments"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_likes'
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'comment')
    
    def __str__(self):
        return f"{self.user.username} likes comment {self.comment.id}"


class Share(models.Model):
    """Share/Repost model"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shares'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='shares'
    )
    
    # Share text (optional)
    text = models.TextField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} shared {self.post.id}"


class PostReport(models.Model):
    """Report model for posts"""

    REPORT_REASONS = (
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('hate_speech', 'Hate Speech'),
        ('violence', 'Violence'),
        ('nudity', 'Nudity'),
        ('false_info', 'False Information'),
        ('copyright', 'Copyright Violation'),
        ('self_harm', 'Self-Harm'),
        ('scam', 'Scam'),
        ('other', 'Other'),
    )

    ACTION_CHOICES = (
        ('no_action', 'No Action Taken'),
        ('warned', 'User Warned'),
        ('content_removed', 'Content Removed'),
        ('user_suspended', 'User Suspended'),
        ('user_banned', 'User Banned'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_reports'
    )

    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(blank=True)
    additional_context = models.JSONField(default=dict, blank=True)

    # Status
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_post_reports'
    )
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES, blank=True)
    action_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('post', 'reported_by')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_reviewed', '-created_at']),
        ]

    def __str__(self):
        return f"Report: {self.post.id} by {self.reported_by.username}"


class CommentReport(models.Model):
    """Report model for comments"""

    REPORT_REASONS = (
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('hate_speech', 'Hate Speech'),
        ('violence', 'Violence'),
        ('nudity', 'Nudity'),
        ('false_info', 'False Information'),
        ('offensive', 'Offensive Language'),
        ('self_harm', 'Self-Harm'),
        ('scam', 'Scam'),
        ('other', 'Other'),
    )

    ACTION_CHOICES = (
        ('no_action', 'No Action Taken'),
        ('warned', 'User Warned'),
        ('comment_removed', 'Comment Removed'),
        ('user_suspended', 'User Suspended'),
        ('user_banned', 'User Banned'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_reports_made'
    )

    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(blank=True)
    additional_context = models.JSONField(default=dict, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_comment_reports'
    )
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES, blank=True)
    action_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('comment', 'reported_by')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reviewed_by']),
        ]

    def __str__(self):
        return f"Report: Comment {self.comment.id} by {self.reported_by.username}"


class PostSave(models.Model):
    """Model for users saving posts"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_posts'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='saves'
    )

    # Organization
    collection_name = models.CharField(max_length=100, blank=True)
    notes = models.TextField(max_length=500, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'collection_name']),
        ]

    def __str__(self):
        return f"{self.user.username} saved {self.post.id}"


class PostMention(models.Model):
    """Model for tracking mentions in posts"""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='mentions'
    )
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_mentions'
    )
    mentioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mentions_made'
    )

    # Notification tracking
    is_notified = models.BooleanField(default=False)
    is_seen = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('post', 'mentioned_user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mentioned_user', '-created_at']),
            models.Index(fields=['mentioned_user', 'is_seen']),
        ]

    def __str__(self):
        return f"{self.mentioned_by.username} mentioned {self.mentioned_user.username} in post {self.post.id}"


class PostBookmark(models.Model):
    """Advanced bookmarking with collections"""

    COLLECTION_TYPES = (
        ('general', 'General'),
        ('favorites', 'Favorites'),
        ('read_later', 'Read Later'),
        ('inspiration', 'Inspiration'),
        ('custom', 'Custom'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmarks'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='bookmarks'
    )

    # Collection details
    collection_type = models.CharField(max_length=20, choices=COLLECTION_TYPES, default='general')
    collection_name = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    # Organization
    is_favorite = models.BooleanField(default=False)
    reminder_date = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'post', 'collection_name')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'collection_type']),
            models.Index(fields=['user', 'is_favorite']),
        ]

    def __str__(self):
        return f"{self.user.username} bookmarked {self.post.id}"
    
class PostView(models.Model):
    """Tracks which users viewed which posts"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_views"
    )
    post = models.ForeignKey(
        "Post",
        on_delete=models.CASCADE,
        related_name="views"
    )
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "post")
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["post", "-viewed_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} viewed post {self.post.id} on {self.viewed_at}"