# apps/accounts/search_views.py
"""
Global search functionality for MANTRA platform
"""

from django.shortcuts import render
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from apps.accounts.models import User
from apps.posts.models import Post
from apps.events.models import Event
from apps.fanclubs.models import FanClub
from apps.merchandise.models import Merchandise


def global_search(request):
    """Search celebrities, fans, and posts"""
    query = request.GET.get('q', '').strip()

    context = {
        'query': query,
        'celebrities': [],
        'fans': [],
        'posts': [],
        'total_results': 0
    }

    if not query or len(query) < 2:
        return render(request, 'search/search_results.html', context)

    # 🔍 Search Celebrities
    celebrities = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(celebrity_profile__bio_extended__icontains=query),
        user_type='celebrity',
        is_active=True
    ).select_related('celebrity_profile').distinct()[:20]

    # 🔍 Search Fans
    fans = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query),
        user_type='fan',
        is_active=True
    ).distinct()[:20]

    # 🔍 Search Posts (content or author)
    posts = Post.objects.filter(
        Q(content__icontains=query) |
        Q(author__username__icontains=query),
        is_active=True
    ).select_related('author')[:20]

    total_results = (
        celebrities.count() +
        fans.count() +
        posts.count()
    )

    context.update({
        'celebrities': celebrities,
        'fans': fans,
        'posts': posts,
        'total_results': total_results
    })

    return render(request, 'search/search_results.html', context)



@login_required
def api_live_search(request):
    """
    AJAX API for live search results (for navbar dropdown)
    """
    query = request.GET.get('q', '').strip()

    if not query or len(query) < 2:
        return JsonResponse({
            'celebrities': [],
            'events': [],
            'fanclubs': []
        })

    # Search top celebrities
    celebrities = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query),
        user_type='celebrity',
        is_active=True
    ).values('username', 'first_name', 'last_name', 'profile_picture')[:5]

    # Format celebrity results
    celebrity_results = []
    for celeb in celebrities:
        celebrity_results.append({
            'username': celeb['username'],
            'name': f"{celeb['first_name']} {celeb['last_name']}".strip() or celeb['username'],
            'profile_picture': celeb['profile_picture'] if celeb['profile_picture'] else None
        })

    # Search events
    events = Event.objects.filter(
        Q(title__icontains=query) | Q(venue_name__icontains=query) | Q(city__icontains=query),
        status='published'
    ).values('title', 'slug', 'start_datetime')[:5]

    event_results = []
    for event in events:
        event_results.append({
            'title': event['title'],
            'slug': event['slug'],
            'date': event['start_datetime'].strftime('%B %d, %Y') if event['start_datetime'] else ''
        })

    # Search fan clubs
    fanclubs = FanClub.objects.filter(
        Q(name__icontains=query),
        is_active=True
    ).values('name', 'slug', 'members_count')[:5]

    fanclub_results = []
    for club in fanclubs:
        fanclub_results.append({
            'name': club['name'],
            'slug': club['slug'],
            'members_count': club['members_count']
        })

    return JsonResponse({
        'celebrities': celebrity_results,
        'events': event_results,
        'fanclubs': fanclub_results
    })