# apps/messaging/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
import uuid

class Conversation(models.Model):
    """Conversation between two or more users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations'
    )

    # Conversation metadata
    title = models.CharField(max_length=100, blank=True)  # For group chats
    is_group = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Group chat settings
    group_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_conversations'
    )
    group_image = models.ImageField(upload_to='conversations/', blank=True, null=True)

    # Fanclub settings (for fanclub group chats)
    is_fanclub = models.BooleanField(default=False)
    fanclub_celebrity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fanclub_conversations',
        help_text="Celebrity who owns this fanclub - only they can post"
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at', '-updated_at']
        indexes = [
            models.Index(fields=['-last_message_at']),
        ]

    def __str__(self):
        if self.is_group and self.title:
            return self.title
        participants_list = self.participants.all()[:2]
        return f"Conversation: {' & '.join([u.username for u in participants_list])}"

    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Get or create conversation between two users"""
        conversations = cls.objects.filter(
            participants=user1,
            is_group=False
        ).filter(
            participants=user2
        )

        if conversations.exists():
            return conversations.first(), False

        # Create new conversation
        conversation = cls.objects.create()
        conversation.participants.add(user1, user2)
        return conversation, True

    def get_other_participant(self, user):
        """Get the other participant in a two-person conversation"""
        if not self.is_group:
            return self.participants.exclude(id=user.id).first()
        return None

    def get_last_message(self):
        """Get the last message in conversation"""
        return self.messages.filter(is_deleted=False).first()

    def mark_as_read(self, user):
        """Mark all messages as read for a user"""
        self.messages.filter(
            is_read=False
        ).exclude(sender=user).update(
            is_read=True,
            read_at=timezone.now()
        )

    def add_participant(self, user):
        """Add participant to group conversation"""
        if self.is_group:
            self.participants.add(user)
            return True
        return False

    def remove_participant(self, user):
        """Remove participant from group conversation"""
        if self.is_group and self.participants.count() > 2:
            self.participants.remove(user)
            return True
        return False


class Message(models.Model):
    """Message model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    
    # Message content
    content = models.TextField(max_length=1000)
    attachment = models.FileField(upload_to='messages/attachments/', null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:30]}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def soft_delete(self):
        """Soft delete message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])


class MessageRequest(models.Model):
    """Message request for non-mutual followers"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_message_requests'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_message_requests'
    )
    
    message = models.TextField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Request from {self.from_user.username} to {self.to_user.username}"
    
    def accept(self):
        """Accept message request"""
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        
        # Create conversation
        Conversation.get_or_create_conversation(self.from_user, self.to_user)
    
    def reject(self):
        """Reject message request"""
        self.status = 'rejected'
        self.responded_at = timezone.now()
        self.save()