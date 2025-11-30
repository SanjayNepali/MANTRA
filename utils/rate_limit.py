# utils/rate_limit.py

from django.core.cache import cache
from django.http import HttpResponse
import time

def rate_limit(key_prefix, limit=10, window=60):
    """Rate limiting decorator"""
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            # Create unique key for user
            ident = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR')
            key = f"rate_limit:{key_prefix}:{ident}"
            
            # Get current count
            requests = cache.get(key, 0)
            
            if requests >= limit:
                return HttpResponse("Rate limit exceeded. Please try again later.", status=429)
            
            # Increment counter
            cache.set(key, requests + 1, window)
            
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator