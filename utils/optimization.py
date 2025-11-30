# utils/optimization.py

from django.db.models import Prefetch
from django.core.cache import cache

def optimize_celebrity_queryset(queryset):
    """Optimize celebrity queries with proper prefetching"""
    from apps.posts.models import Post

    return queryset.select_related(
        'celebrity_profile'
    ).prefetch_related(
        Prefetch('posts',
                queryset=Post.objects.filter(is_active=True)[:5]),
        'followers',
        'events'
    )

def optimize_post_queryset(queryset):
    """Optimize post queries"""
    return queryset.select_related(
        'author',
        'author__celebrity_profile'
    ).prefetch_related(
        'likes',
        'comments__author',
        'media_files',
        'tags'
    )