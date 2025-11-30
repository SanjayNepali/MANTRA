# MANTRA/apps/messaging/context_processors.py

def unread_messages(request):
    """
    Add unread messages count to context

    This context processor adds:
    - unread_messages: Count of unread messages in conversations
    - pending_message_requests: Count of pending message requests
    - total_unread_messages: Combined total

    Note: Uses caching to reduce database queries (30 second cache)
    """
    if request.user.is_authenticated:
        from .models import Conversation, Message, MessageRequest
        from django.core.cache import cache

        # Cache key unique to user
        cache_key = f'unread_messages_{request.user.id}'

        # Try to get from cache first (cached for 30 seconds)
        cached_data = cache.get(cache_key)

        if cached_data is None:
            # Optimized query: Count unread messages in a single query
            unread_count = Message.objects.filter(
                conversation__participants=request.user,
                conversation__is_active=True,
                is_read=False,
                is_deleted=False
            ).exclude(sender=request.user).count()

            # Count pending message requests
            pending_requests = MessageRequest.objects.filter(
                to_user=request.user,
                status='pending'
            ).count()

            cached_data = {
                'unread_messages': unread_count,
                'pending_message_requests': pending_requests,
                'total_unread_messages': unread_count + pending_requests
            }

            # Cache for 30 seconds to reduce database queries
            cache.set(cache_key, cached_data, 30)

        return cached_data

    return {
        'unread_messages': 0,
        'pending_message_requests': 0,
        'total_unread_messages': 0
    }