# apps/notifications/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class Notification(models.Model):
    """Notification model"""
    
    NOTIFICATION_TYPES = (
        ('follow', 'New Follower'),
        ('like', 'Post Liked'),
        ('comment', 'New Comment'),
        ('message', 'New Message'),
        ('message_request', 'Message Request'),
        ('message_request_accepted', 'Message Request Accepted'),
        ('subscription', 'New Subscription'),
        ('event', 'Event Reminder'),
        ('fanclub', 'Fanclub Activity'),
        ('achievement', 'Achievement Unlocked'),
        ('system', 'System Notification'),
        ('warning', 'Warning'),
        ('promotion', 'Promotion'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sent_notifications'
    )
    
    # Notification content
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    message = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Target object (could be post, event, etc.)
    target_id = models.CharField(max_length=100, blank=True)
    target_url = models.CharField(max_length=255, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def get_icon(self):
        """Get icon for notification type"""
        icons = {
            'follow': 'bx bx-user-plus',
            'like': 'bx bx-heart',
            'comment': 'bx bx-comment',
            'message': 'bx bx-envelope',
            'message_request': 'bx bx-mail-send',
            'subscription': 'bx bx-star',
            'event': 'bx bx-calendar',
            'fanclub': 'bx bx-group',
            'achievement': 'bx bx-trophy',
            'system': 'bx bx-info-circle',
            'warning': 'bx bx-error',
            'promotion': 'bx bx-gift',
        }
        return icons.get(self.notification_type, 'bx bx-bell')
    
    def get_color(self):
        """Get color for notification type"""
        colors = {
            'follow': 'primary',
            'like': 'danger',
            'comment': 'info',
            'message': 'success',
            'subscription': 'warning',
            'warning': 'danger',
            'achievement': 'warning',
            'promotion': 'success',
        }
        return colors.get(self.notification_type, 'secondary')


class NotificationPreference(models.Model):
    """User notification preferences"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notifications
    email_follows = models.BooleanField(default=True)
    email_likes = models.BooleanField(default=True)
    email_comments = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    email_events = models.BooleanField(default=True)
    email_system = models.BooleanField(default=True)
    
    # Push notifications
    push_follows = models.BooleanField(default=True)
    push_likes = models.BooleanField(default=True)
    push_comments = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_events = models.BooleanField(default=True)
    push_system = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.username}"
    
    def should_send_email(self, notification_type):
        """Check if email should be sent for notification type"""
        mapping = {
            'follow': self.email_follows,
            'like': self.email_likes,
            'comment': self.email_comments,
            'message': self.email_messages,
            'event': self.email_events,
            'system': self.email_system,
        }
        return mapping.get(notification_type, True)
    
    def should_send_push(self, notification_type):
        """Check if push notification should be sent"""
        if self.quiet_hours_enabled:
            from datetime import datetime
            now = datetime.now().time()
            if self.quiet_hours_start <= now <= self.quiet_hours_end:
                return False
        
        mapping = {
            'follow': self.push_follows,
            'like': self.push_likes,
            'comment': self.push_comments,
            'message': self.push_messages,
            'event': self.push_events,
            'system': self.push_system,
        }
        return mapping.get(notification_type, True)


class SystemAnnouncement(models.Model):
    """System-wide announcements"""
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # Target audience
    target_user_type = models.CharField(max_length=20, blank=True, choices=[
        ('', 'All Users'),
        ('fan', 'Fans Only'),
        ('celebrity', 'Celebrities Only'),
    ])
    
    # Display settings
    is_active = models.BooleanField(default=True)
    show_until = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements'
    )
    
    class Meta:
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return self.title
    
    def is_visible(self):
        """Check if announcement should be visible"""
        if not self.is_active:
            return False
        if self.show_until and timezone.now() > self.show_until:
            return False
        return True