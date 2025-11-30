# apps/fans/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.paginator import Paginator

from apps.accounts.models import User, UserFollowing
from apps.celebrities.models import CelebrityProfile, Subscription
from apps.fans.models import FanProfile, FanActivity, FanRecommendation
from apps.fans.utils import generate_fan_recommendations
from algorithms.recommendation import RecommendationEngine
from django.views.decorators.http import require_POST

@require_POST
@login_required
def refresh_recommendations(request):
    """
    Regenerate AI-based recommendations for the logged-in fan.
    This connects to algorithms/recommendation.py → RecommendationEngine.
    """
    try:
        engine = RecommendationEngine()
        data = engine.get_user_recommendations(request.user, recommendation_type='all', limit=10)
        return JsonResponse({
            'success': True,
            'message': 'Recommendations refreshed successfully.',
            'recommendations': data
        })
    except Exception as e:
        print("Error refreshing recommendations:", e)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@method_decorator(login_required, name='dispatch')
class FanDashboardView(TemplateView):
    """Dashboard for fan users"""
    template_name = 'dashboard/fan_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'fan':
            messages.error(request, 'Access restricted to fans only')
            return redirect('fan_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            profile = self.request.user.fan_profile
        except FanProfile.DoesNotExist:
            profile = FanProfile.objects.create(user=self.request.user)
        
        # Update statistics
        if hasattr(profile, 'update_statistics'):
            profile.update_statistics()
        
        # Get followed celebrities
        followed_celebrities = User.objects.filter(
            id__in=UserFollowing.objects.filter(
                follower=self.request.user
            ).values_list('following_id', flat=True),
            user_type='celebrity'
        ).select_related('celebrity_profile')[:6]
        
        # Get recommendations
        recommendations = FanRecommendation.objects.filter(
            fan=self.request.user,
            is_viewed=False,
            expires_at__gt=timezone.now()
        ).select_related('recommended_celebrity', 'recommended_celebrity__celebrity_profile')[:5]
        
        # Get recent activities
        recent_activities = FanActivity.objects.filter(
            fan=self.request.user
        ).select_related('target_user')[:10]
        
        # Get trending celebrities
        trending_celebrities = User.objects.filter(
            user_type='celebrity',
            is_verified=True,
            is_active=True
        ).annotate(
            recent_followers=Count(
                'id',
                filter=Q(created_at__gte=timezone.now() - timedelta(days=7))
            )
        ).order_by('-recent_followers')[:5]
        
        # Get following count
        following_count = UserFollowing.objects.filter(follower=self.request.user).count()
        
        context.update({
            'profile': profile,
            'followed_celebrities': followed_celebrities,
            'recommendations': recommendations,
            'recent_activities': recent_activities,
            'trending_celebrities': trending_celebrities,
            'total_following': following_count,
            'points': self.request.user.points if hasattr(self.request.user, 'points') else 0,
            'rank': self.request.user.rank if hasattr(self.request.user, 'rank') else 'Bronze',
        })
        
        return context


@login_required
def celebrity_follow_suggestions(request):
    """Suggest celebrities for new fans to follow"""
    if request.user.user_type != 'fan':
        messages.info(request, 'Redirected to discover page')
        return redirect('discover_celebrities')

    # Generate recommendations
    generate_fan_recommendations(request.user)

    # Get top celebrities across categories
    top_celebrities = User.objects.filter(
        user_type='celebrity',
        is_verified=True,
        is_active=True
    ).order_by('-points')[:20]

    # Get new celebrities
    new_celebrities = User.objects.filter(
        user_type='celebrity',
        is_verified=True,
        is_active=True,
        created_at__gte=timezone.now() - timedelta(days=30)
    ).order_by('-created_at')[:10]

    # Get recommendations
    recommendations = FanRecommendation.objects.filter(
        fan=request.user,
        expires_at__gt=timezone.now()
    ).select_related('recommended_celebrity', 'recommended_celebrity__celebrity_profile')[:15]

    # Get categories
    categories = getattr(settings, 'CELEBRITY_CATEGORIES', [])
    if hasattr(settings, 'MANTRA_SETTINGS'):
        categories = settings.MANTRA_SETTINGS.get('CELEBRITY_CATEGORIES', [])

    context = {
        'top_celebrities': top_celebrities,
        'new_celebrities': new_celebrities,
        'recommendations': recommendations,
        'categories': categories,
        'skip_count': request.GET.get('skip', 0),
    }

    return render(request, 'fans/follow_suggestions.html', context)


@login_required
def discover_celebrities(request):
    """Discover page for fans"""
    if request.user.user_type != 'fan':
        return redirect('celebrity_list')
    
    # Generate recommendations if needed
    generate_fan_recommendations(request.user)
    
    # Categories
    categories = getattr(settings, 'CELEBRITY_CATEGORIES', [])
    if hasattr(settings, 'MANTRA_SETTINGS'):
        categories = settings.MANTRA_SETTINGS.get('CELEBRITY_CATEGORIES', [])
    
    selected_category = request.GET.get('category', '')
    
    # Get recommendations
    recommendations = FanRecommendation.objects.filter(
        fan=request.user,
        expires_at__gt=timezone.now()
    ).select_related('recommended_celebrity', 'recommended_celebrity__celebrity_profile')
    
    if selected_category:
        recommendations = recommendations.filter(
            recommended_celebrity__celebrity_profile__category=selected_category
        )
    
    # Mark as viewed
    recommendations.update(is_viewed=True, viewed_at=timezone.now())
    
    # Get top celebrities
    top_celebrities = User.objects.filter(
        user_type='celebrity',
        is_verified=True,
        is_active=True
    ).order_by('-points')[:10]
    
    # Get new celebrities
    new_celebrities = User.objects.filter(
        user_type='celebrity',
        is_verified=True,
        is_active=True,
        created_at__gte=timezone.now() - timedelta(days=30)
    ).order_by('-created_at')[:10]
    
    context = {
        'categories': categories,
        'selected_category': selected_category,
        'recommendations': recommendations,
        'top_celebrities': top_celebrities,
        'new_celebrities': new_celebrities,
    }
    
    return render(request, 'fans/discover.html', context)


@login_required
def fan_feed(request):
    """Personalized feed for fans"""
    if request.user.user_type != 'fan':
        messages.error(request, 'Access restricted to fans')
        return redirect('dashboard')

    # Get followed celebrities
    from apps.posts.models import Post
    from apps.celebrities.models import Subscription

    followed_celebrity_ids = UserFollowing.objects.filter(
        follower=request.user
    ).values_list('following_id', flat=True)

    followed_celebrities = User.objects.filter(
        id__in=followed_celebrity_ids,
        user_type='celebrity'
    )

    # Get filter preference
    filter_type = request.GET.get('filter', 'all')

    # Base queryset - posts from followed celebrities
    posts = Post.objects.filter(
        author_id__in=followed_celebrity_ids,
        is_active=True
    ).select_related('author')

    # Apply filters
    if filter_type == 'exclusive':
        # Show only posts from celebrities the user is subscribed to
        subscribed_celeb_ids = Subscription.objects.filter(
            subscriber=request.user,
            status='active'
        ).values_list('celebrity__id', flat=True)

        # Filter posts marked as exclusive or from subscribed celebrities
        posts = posts.filter(
            Q(is_exclusive=True) | Q(author_id__in=subscribed_celeb_ids)
        ).order_by('-created_at')

    elif filter_type == 'verified_only':
        # Show only verified celebrities' posts
        posts = posts.filter(author__is_verified=True).order_by('-created_at')

    elif filter_type == 'most_popular':
        # Sort by total engagement (likes + comments)
        posts = posts.annotate(
            popularity_score=Count('likes') + Count('comments') * 2
        ).order_by('-popularity_score', '-created_at')

    elif filter_type == 'recent':
        posts = posts.order_by('-created_at')

    else:  # all (default) - Use recommendation algorithm
        # Get AI-powered recommendations for intelligent sorting
        try:
            from algorithms.recommendation import RecommendationEngine
            engine = RecommendationEngine()

            # Get recommended posts based on user preferences
            rec_posts = engine.get_user_recommendations(
                request.user,
                recommendation_type='posts',
                limit=100  # Get more for better sorting
            )

            if rec_posts and rec_posts.get('posts'):
                # Sort posts by recommendation score
                recommended_post_ids = [p.id for p in rec_posts['posts'] if hasattr(p, 'id')]
                # Preserve recommendation order
                posts = Post.objects.filter(
                    id__in=recommended_post_ids,
                    is_active=True
                ).select_related('author')

                # Sort by recommendation order (using case/when)
                from django.db.models import Case, When, IntegerField
                preserved_order = Case(
                    *[When(id=pk, then=pos) for pos, pk in enumerate(recommended_post_ids)],
                    output_field=IntegerField()
                )
                posts = posts.order_by(preserved_order)
            else:
                # Fallback to engagement-based sorting
                posts = posts.annotate(
                    engagement_score=Count('likes') + Count('comments') * 2 + Count('shares') * 3
                ).order_by('-engagement_score', '-created_at')
        except:
            # Final fallback to chronological
            posts = posts.order_by('-created_at')

    # Get AI-powered recommendations with caching
    recommended_posts = []
    recommended_celebrities = []
    recommended_events = []
    trending_hashtags = []

    try:
        from algorithms.integration import get_user_recommendations
        from algorithms.sentiment import SentimentAnalyzer

        # Get comprehensive recommendations with caching
        all_recommendations = get_user_recommendations(
            request.user,
            recommendation_type='all',
            limit=5,
            use_cache=True
        )

        recommended_posts = all_recommendations.get('posts', [])[:4]
        recommended_celebrities = all_recommendations.get('celebrities', [])[:5]
        recommended_events = all_recommendations.get('events', [])[:3]

        # Get trending hashtags using sentiment analysis
        analyzer = SentimentAnalyzer()
        recent_posts_text = ' '.join([
            p.content for p in Post.objects.filter(
                is_active=True,
                created_at__gte=timezone.now() - timedelta(days=1)
            )[:100]
        ])
        trending_hashtags = analyzer.extract_hashtags(recent_posts_text)[:5]

    except Exception as e:
        # Fallback: get popular content
        recommended_posts = Post.objects.filter(
            author_id__in=followed_celebrity_ids,
            is_active=True,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).annotate(
            engagement=Count('likes') + Count('comments') * 2
        ).order_by('-engagement')[:4]

        recommended_celebrities = User.objects.filter(
            user_type='celebrity',
            is_verified=True,
            is_active=True
        ).exclude(
            id__in=followed_celebrity_ids
        ).exclude(
            id=request.user.id
        ).order_by('-points')[:5]

    # Get suggested celebrities (use recommended or fallback)
    suggested_celebrities = recommended_celebrities if recommended_celebrities else User.objects.filter(
        user_type='celebrity',
        is_verified=True,
        is_active=True
    ).exclude(
        id__in=followed_celebrity_ids
    ).exclude(
        id=request.user.id
    ).order_by('-points')[:5]

    context = {
        'posts': posts[:20],
        'filter': filter_type,
        'followed_celebrities': followed_celebrities.count(),
        'trending_hashtags': trending_hashtags,
        'suggested_celebrities': suggested_celebrities,
        'recommended_posts': recommended_posts,
        'recommended_events': recommended_events,
    }

    return render(request, 'fans/feed.html', context)


@login_required
def my_subscriptions(request):
    """View fan's subscriptions"""
    if request.user.user_type != 'fan':
        messages.error(request, 'Access restricted to fans')
        return redirect('dashboard')
    
    subscriptions = Subscription.objects.filter(
        subscriber=request.user
    ).select_related('celebrity', 'tier').order_by('-created_at')
    
    active_subs = subscriptions.filter(status='active')
    expired_subs = subscriptions.filter(status='expired')
    
    context = {
        'active_subscriptions': active_subs,
        'expired_subscriptions': expired_subs,
        'total_spent': subscriptions.aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
    }
    
    return render(request, 'fans/subscriptions.html', context)


@login_required
def fan_activities(request):
    """View all fan activities"""
    if request.user.user_type != 'fan':
        messages.error(request, 'Access restricted to fans')
        return redirect('dashboard')
    
    activities = FanActivity.objects.filter(
        fan=request.user
    ).select_related('target_user')
    
    # Filter by activity type
    activity_type = request.GET.get('type', '')
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    
    # Pagination
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    activity_types = FanActivity.ACTIVITY_TYPES if hasattr(FanActivity, 'ACTIVITY_TYPES') else []
    
    context = {
        'activities': page_obj,
        'activity_types': activity_types,
        'selected_type': activity_type,
    }
    
    return render(request, 'fans/activities.html', context)


@login_required
def follow_celebrity_ajax(request):
    """AJAX endpoint for following/unfollowing celebrities AND fans"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    celebrity_id = request.POST.get('celebrity_id')
    user_id = request.POST.get('user_id')  # Support both celebrity_id and user_id
    action = request.POST.get('action')

    target_id = celebrity_id or user_id

    if not target_id:
        return JsonResponse({'error': 'User ID required'}, status=400)

    try:
        target_user = User.objects.get(id=target_id)

        # Prevent self-following
        if target_user == request.user:
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)

    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    if action == 'follow':
        following, created = UserFollowing.objects.get_or_create(
            follower=request.user,
            following=target_user
        )

        if created:
            # Log activity
            FanActivity.objects.create(
                fan=request.user,
                activity_type='follow',
                description=f'Started following {target_user.username}',
                target_user=target_user
            )

            # Award points
            if hasattr(request.user, 'add_points'):
                request.user.add_points(3, f'Followed {target_user.username}')

            # Update recommendations (only for celebrities)
            if target_user.user_type == 'celebrity' and hasattr(request.user, 'fan_profile'):
                try:
                    profile = request.user.fan_profile
                    profile.last_celebrity_followed = target_user
                    profile.save()
                except:
                    pass

            user_type = 'celebrity' if target_user.user_type == 'celebrity' else 'user'

            return JsonResponse({
                'status': 'followed',
                'message': f'You are now following {target_user.username}',
                'user_type': user_type
            })
        else:
            return JsonResponse({
                'status': 'already_following',
                'message': f'You are already following {target_user.username}'
            })
    
    elif action == 'unfollow':
        try:
            following = UserFollowing.objects.get(
                follower=request.user,
                following=target_user
            )
            following.delete()

            # Log activity
            FanActivity.objects.create(
                fan=request.user,
                activity_type='unfollow',
                description=f'Unfollowed {target_user.username}',
                target_user=target_user
            )

            user_type = 'celebrity' if target_user.user_type == 'celebrity' else 'user'

            return JsonResponse({
                'status': 'unfollowed',
                'message': f'You have unfollowed {target_user.username}',
                'user_type': user_type
            })
        except UserFollowing.DoesNotExist:
            return JsonResponse({
                'status': 'not_following',
                'message': 'You are not following this user'
            })
    
    return JsonResponse({'error': 'Invalid action'}, status=400)


class FanFeedView(LoginRequiredMixin, ListView):
    """Fan feed with posts from followed celebrities"""
    template_name = 'fans/feed.html'
    context_object_name = 'posts'
    paginate_by = 20
    
    def get_queryset(self):
        # Get followed celebrities
        followed_celebrity_ids = UserFollowing.objects.filter(
            follower=self.request.user
        ).values_list('following_id', flat=True)
        
        # Get posts from followed celebrities
        from apps.posts.models import Post
        posts = Post.objects.filter(
            author_id__in=followed_celebrity_ids,
            is_active=True
        ).select_related(
            'author'
        ).order_by('-created_at')
        
        return posts
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add trending content if integration exists
        try:
            from algorithms.integration import get_trending_content, get_user_recommendations
            context['trending_posts'] = get_trending_content('posts', days=7, limit=5)
            context['trending_hashtags'] = get_trending_content('hashtags', days=7, limit=10)
            
            # Add recommendations
            recommendations = get_user_recommendations(
                self.request.user, 
                recommendation_type='posts', 
                limit=5
            )
            context['recommended_posts'] = recommendations.get('posts', [])
        except ImportError:
            pass
        
        return context

