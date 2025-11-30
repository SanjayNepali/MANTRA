# apps/reports/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class Report(models.Model):
    """General report model"""
    
    REPORT_TYPES = (
        ('user', 'User Report'),
        ('post', 'Post Report'),
        ('comment', 'Comment Report'),
        ('message', 'Message Report'),
        ('event', 'Event Report'),
        ('merchandise', 'Merchandise Report'),
    )
    
    REPORT_REASONS = (
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('hate_speech', 'Hate Speech'),
        ('violence', 'Violence'),
        ('nudity', 'Nudity/Sexual Content'),
        ('false_info', 'False Information'),
        ('copyright', 'Copyright Violation'),
        ('scam', 'Scam/Fraud'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('reviewing', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reporter
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    
    # Report details
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField()
    
    # Target
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports_received'
    )
    target_object_id = models.CharField(max_length=100, blank=True)
    
    # Evidence
    screenshot = models.ImageField(upload_to='reports/screenshots/', null=True, blank=True)
    additional_info = models.JSONField(default=dict)
    
    # Review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_reviewed'
    )
    review_notes = models.TextField(blank=True)
    action_taken = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['report_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.get_reason_display()}"

    def get_target_region(self):
        """
        Determine the regional assignment for this report based on the target user's location.
        This is used to route reports to the correct regional SubAdmin.
        """
        from apps.accounts.constants import get_region_for_user

        if self.target_user:
            return get_region_for_user(self.target_user.country, self.target_user.city)

        # If no target_user, try to get the author from the reported content
        if self.report_type == 'post' and self.target_object_id:
            try:
                from apps.posts.models import Post
                post = Post.objects.get(id=self.target_object_id)
                return get_region_for_user(post.author.country, post.author.city)
            except:
                pass

        elif self.report_type == 'event' and self.target_object_id:
            try:
                from apps.events.models import Event
                event = Event.objects.get(id=self.target_object_id)
                return get_region_for_user(event.organizer.country, event.organizer.city)
            except:
                pass

        elif self.report_type == 'merchandise' and self.target_object_id:
            try:
                from apps.merchandise.models import Merchandise
                merch = Merchandise.objects.get(id=self.target_object_id)
                return get_region_for_user(merch.seller.country, merch.seller.city)
            except:
                pass

        # Default to International if unable to determine
        return 'International'


class ModerationAction(models.Model):
    """Track moderation actions taken"""
    
    ACTION_TYPES = (
        ('warning', 'Warning Issued'),
        ('content_removed', 'Content Removed'),
        ('temporary_ban', 'Temporary Ban'),
        ('permanent_ban', 'Permanent Ban'),
        ('account_suspended', 'Account Suspended'),
        ('restriction', 'Feature Restriction'),
    )
    
    # Action details
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moderation_actions'
    )
    
    # Related report
    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions'
    )
    
    # Action info
    reason = models.TextField()
    duration_days = models.IntegerField(null=True, blank=True)  # For temporary bans
    
    # Moderator
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='moderation_actions_performed'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_type_display()} - {self.target_user.username}"
    
    def execute_action(self):
        """Execute the moderation action"""
        if self.action_type == 'warning':
            self.send_warning()
        elif self.action_type == 'temporary_ban':
            self.apply_temporary_ban()
        elif self.action_type == 'permanent_ban':
            self.apply_permanent_ban()
    
    def send_warning(self):
        """Send warning to user"""
        from apps.notifications.utils import send_notification
        send_notification(
            self.target_user,
            notification_type='warning',
            message='You have received a warning',
            description=self.reason
        )
    
    def apply_temporary_ban(self):
        """Apply temporary ban"""
        if self.duration_days:
            from datetime import timedelta
            self.target_user.ban_user(self.reason, self.duration_days)
            self.expires_at = timezone.now() + timedelta(days=self.duration_days)
            self.save()
    
    def apply_permanent_ban(self):
        """Apply permanent ban"""
        self.target_user.ban_user(self.reason)