# MANTRA/apps/messaging/utils.py

from django.core.cache import cache
from apps.accounts.models import UserFollowing


def can_message(user1, user2):
    """
    Check if two users can message each other (mutual follow required).

    Args:
        user1: First User object
        user2: Second User object

    Returns:
        bool: True if users mutually follow each other, False otherwise
    """
    # Check if user1 follows user2 AND user2 follows user1
    user1_follows_user2 = UserFollowing.objects.filter(
        follower=user1,
        following=user2
    ).exists()

    user2_follows_user1 = UserFollowing.objects.filter(
        follower=user2,
        following=user1
    ).exists()

    return user1_follows_user2 and user2_follows_user1


def clear_messages_cache(user):
    """
    Clear messages cache for a specific user

    Call this function when:
    - A message is sent
    - A message is marked as read
    - A message request is created/accepted/rejected

    Args:
        user: User object whose cache should be cleared
    """
    cache_key = f'unread_messages_{user.id}'
    cache.delete(cache_key)


def clear_conversation_participants_cache(conversation):
    """
    Clear messages cache for all participants in a conversation

    Args:
        conversation: Conversation object
    """
    for participant in conversation.participants.all():
        clear_messages_cache(participant)