# apps/notifications/utils.py

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.cache import cache
from .models import Notification, NotificationPreference

def send_notification(recipient, sender=None, notification_type='system', 
                      message='', description='', target_id='', target_url=''):
    """Helper function to create and send notification"""
    
    # Create notification
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message,
        description=description,
        target_id=target_id,
        target_url=target_url
    )
    
    # Send through WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{recipient.id}',
        {
            'type': 'send_notification',
            'notification': {
                'id': str(notification.id),
                'type': notification.notification_type,
                'message': notification.message,
                'description': notification.description,
                'sender': {
                    'username': sender.username if sender else 'System',
                    'profile_picture': sender.profile_picture.url if sender and sender.profile_picture else None
                },
                'created_at': notification.created_at.isoformat(),
                'icon': notification.get_icon(),
                'color': notification.get_color(),
                'target_url': notification.target_url
            }
        }
    )
    
    # Check if email notification should be sent
    try:
        preferences = recipient.notification_preferences
        if preferences.should_send_email(notification_type):
            send_email_notification(recipient, notification)
    except NotificationPreference.DoesNotExist:
        pass

    # Clear cache so new notification count is reflected immediately
    clear_notifications_cache(recipient)

    return notification


def send_email_notification(user, notification):
    """Send email notification"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    subject = f'MANTRA - {notification.get_notification_type_display()}'

    html_message = render_to_string('emails/notification.html', {
        'user': user,
        'notification': notification
    })

    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        'notifications@mantra.com',
        [user.email],
        html_message=html_message,
        fail_silently=True
    )


def clear_notifications_cache(user):
    """
    Clear notifications cache for a specific user

    Call this function when:
    - A notification is marked as read
    - A notification is created
    - A notification is deleted

    Args:
        user: User object whose cache should be cleared
    """
    cache_key = f'notifications_count_{user.id}'
    cache.delete(cache_key)