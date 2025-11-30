# MANTRA/apps/notifications/context_processors.py

def notifications_count(request):
    """
    Add unread notifications count to context

    This context processor adds:
    - unread_notifications: Count of unread notifications
    - recent_notifications: Last 5 notifications for quick access

    Note: Uses caching to reduce database queries (30 second cache)
    """
    if request.user.is_authenticated:
        from .models import Notification
        from django.core.cache import cache

        # Cache key unique to user
        cache_key = f'notifications_count_{request.user.id}'

        # Try to get from cache first (cached for 30 seconds)
        cached_data = cache.get(cache_key)

        if cached_data is None:
            # Count unread notifications
            count = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()

            # Get recent notifications for navbar (optimized query)
            recent_notifications = list(
                Notification.objects.filter(
                    recipient=request.user
                ).select_related('sender').order_by('-created_at')[:5]
            )

            cached_data = {
                'unread_notifications': count,
                'recent_notifications': recent_notifications
            }

            # Cache for 30 seconds to reduce database queries
            cache.set(cache_key, cached_data, 30)

        return cached_data

    return {
        'unread_notifications': 0,
        'recent_notifications': []
    }