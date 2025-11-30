# apps/accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import View, TemplateView, ListView
from django.utils.decorators import method_decorator
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator

from .models import User, UserFollowing, LoginHistory, PointsHistory, UserPreferences
from .forms import (
    FanRegistrationForm, CelebrityRegistrationForm, UnifiedLoginForm,
    ProfileUpdateForm, PreferencesForm, CustomPasswordChangeForm
)

class HomeView(TemplateView):
    """Home page view - Landing page for non-authenticated, feed for authenticated"""

    def get_template_names(self):
        """Return different templates based on authentication"""
        if self.request.user.is_authenticated:
            return ['home.html']  # Authenticated user feed
        return ['landing.html']  # Public landing page

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Context for authenticated users
        if self.request.user.is_authenticated:
            # Get top celebrities
            context['top_celebrities'] = User.objects.filter(
                user_type='celebrity',
                is_active=True,
                is_banned=False
            ).order_by('-points')[:6]

            # Get trending content using AI algorithms
            try:
                from algorithms.recommendation import TrendingEngine
                from algorithms.sentiment import SentimentAnalyzer
                from apps.posts.models import Post
                from datetime import timedelta

                # Get trending posts
                trending_posts = TrendingEngine.calculate_trending_posts(days=7, limit=10)
                context['trending_posts'] = trending_posts

                # Get trending hashtags
                trending_hashtags = TrendingEngine.calculate_trending_hashtags(days=7, limit=10)
                context['trending_hashtags'] = trending_hashtags

                # Get trending celebrities (most engagement this week)
                trending_celebrities = User.objects.filter(
                    user_type='celebrity',
                    is_verified=True,
                    is_active=True,
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).annotate(
                    recent_engagement=Count('posts__likes') + Count('posts__comments')
                ).order_by('-recent_engagement')[:5]
                context['trending_celebrities'] = trending_celebrities

            except Exception:
                # Fallback: use basic queries
                from apps.posts.models import Post
                context['trending_posts'] = Post.objects.filter(
                    is_active=True
                ).annotate(
                    engagement=Count('likes') + Count('comments')
                ).order_by('-engagement')[:10]
                context['trending_hashtags'] = []
                context['trending_celebrities'] = []

            context['total_users'] = User.objects.filter(is_active=True).count()
            context['total_celebrities'] = User.objects.filter(
                user_type='celebrity',
                is_active=True
            ).count()

        return context


class FanRegistrationView(View):
    """Fan registration view"""
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        
        form = FanRegistrationForm()
        return render(request, 'accounts/fan_register.html', {'form': form})
    
    def post(self, request):
        form = FanRegistrationForm(request.POST, request.FILES)

        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please login to continue.')
            return redirect('login')
        else:
            # Show form errors to help debug
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return render(request, 'accounts/fan_register.html', {'form': form})


class CelebrityRegistrationView(View):
    """Celebrity registration view"""
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        
        form = CelebrityRegistrationForm()
        return render(request, 'accounts/celebrity_register.html', {'form': form})
    
    def post(self, request):
        form = CelebrityRegistrationForm(request.POST, request.FILES)

        if form.is_valid():
            user = form.save()

            # Log the user in
            from django.contrib.auth import login
            login(request, user)

            messages.success(request, 'Registration successful! Please upload your KYC documents to get verified.')
            return redirect('celebrity_kyc_upload')
        else:
            # Show form errors to help debug
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return render(request, 'accounts/celebrity_register.html', {'form': form})


class UnifiedLoginView(View):
    """Unified login for all user types"""
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        
        form = UnifiedLoginForm()
        return render(request, 'accounts/login.html', {'form': form})
    
    def post(self, request):
        form = UnifiedLoginForm(request.POST)
        
        if form.is_valid():
            user = form.cleaned_data['user']
            
            # Create login history
            LoginHistory.objects.create(
                user=user,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=request.session.session_key or ''
            )
            
            # Update last active
            user.last_active = timezone.now()
            user.save(update_fields=['last_active'])
            
            # Login user
            login(request, user)
            
            # Remember me functionality
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)
            
            messages.success(request, f'Welcome back, {user.username}!')

            # Redirect based on user type (superusers always go to admin dashboard)
            if user.is_superuser or user.user_type == 'admin':
                return redirect('admin_dashboard')
            elif user.user_type == 'subadmin':
                return redirect('subadmin_dashboard')
            else:
                return redirect('dashboard')
        
        return render(request, 'accounts/login.html', {'form': form})
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@login_required
def logout_view(request):
    """Logout view"""
    # Update logout time in login history
    try:
        last_login = LoginHistory.objects.filter(
            user=request.user,
            logout_time__isnull=True
        ).latest('login_time')
        last_login.logout_time = timezone.now()
        last_login.save()
    except LoginHistory.DoesNotExist:
        pass
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def dashboard_view(request):
    """Main dashboard based on user type"""
    user = request.user
    context = {'user': user}
    followers = user.followers.all()

    if user.user_type == 'admin':
        # Redirect to the analytics admin dashboard view
        return redirect('admin_dashboard')

    elif user.user_type == 'subadmin':
        return redirect('subadmin_dashboard')

    elif user.user_type == 'celebrity':
        # Celebrity dashboard data
        from apps.celebrities.models import CelebrityProfile, Subscription
        from apps.posts.models import Post
        from apps.merchandise.models import MerchandiseOrder
        from apps.events.models import EventBooking
        from apps.celebrities.utils import get_or_create_default_fanclub

        try:
            celebrity_profile = user.celebrity_profile
        except:
            from apps.celebrities.models import CelebrityProfile
            celebrity_profile = CelebrityProfile.objects.create(user=user)

        # Ensure celebrity has a default fanclub
        default_fanclub = get_or_create_default_fanclub(user)

        # Get filter for fan posts
        fan_filter = request.GET.get('fan_filter', 'all')

        # Get top fans based on engagement
        top_fans_base = User.objects.filter(
            user_type='fan',
            following__following=user
        )

        # Apply filters to identify top fans
        if fan_filter == 'subscribers':
            # Fans who are subscribed
            subscriber_ids = Subscription.objects.filter(
                celebrity=celebrity_profile,
                status='active'
            ).values_list('subscriber_id', flat=True)
            top_fans_ids = list(subscriber_ids)
        elif fan_filter == 'purchasers':
            # Fans who bought merch
            purchaser_ids = MerchandiseOrder.objects.filter(
                items__merchandise__celebrity=user
            ).values_list('buyer_id', flat=True).distinct()
            top_fans_ids = list(purchaser_ids)
        elif fan_filter == 'event_attendees':
            # Fans who registered for events
            attendee_ids = EventBooking.objects.filter(
                event__celebrity=user
            ).values_list('user_id', flat=True).distinct()
            top_fans_ids = list(attendee_ids)
        else:  # 'all' or 'engaged'
            # All followers, ranked by engagement
            top_fans_ids = top_fans_base.annotate(
                engagement=Count('likes') + Count('comments')
            ).order_by('-engagement')[:50].values_list('id', flat=True)
            top_fans_ids = list(top_fans_ids)

        # Get posts from top fans
        fan_posts = Post.objects.filter(
            author_id__in=top_fans_ids,
            is_active=True
        ).select_related('author').order_by('-created_at')[:20]

        # Get top fans for sidebar
        top_fans_display = top_fans_base.annotate(
            engagement=Count('likes') + Count('comments')
        ).order_by('-engagement')[:10]

        # Get AI-powered recommendations for celebrity
        recommended_content = []
        trending_topics = []
        engagement_insights = {}

        try:
            from algorithms.recommendation import RecommendationEngine
            from algorithms.sentiment import SentimentAnalyzer
            from algorithms.engagement import EngagementPredictor

            rec_engine = RecommendationEngine()
            analyzer = SentimentAnalyzer()
            predictor = EngagementPredictor()

            # Get recommended content to post about
            all_recommendations = rec_engine.get_user_recommendations(
                user,
                recommendation_type='all',
                limit=5
            )
            recommended_content = all_recommendations.get('topics', [])[:3]

            # Get trending topics from fan interactions
            fan_posts_text = ' '.join([p.content for p in fan_posts[:20]])
            trending_topics = analyzer.extract_hashtags(fan_posts_text)[:5]

            # Get engagement insights for recent posts
            recent_posts_list = user.posts.filter(is_active=True).order_by('-created_at')[:3]
            for post in recent_posts_list:
                score = predictor.predict_engagement(post)
                engagement_insights[post.id] = score

        except Exception:
            # Fallback: basic recommendations
            pass

        context.update({
            'celebrity_profile': celebrity_profile,
            'default_fanclub': default_fanclub,
            'recent_posts': user.posts.filter(is_active=True).order_by('-created_at')[:5],
            'fan_posts': fan_posts,
            'fan_filter': fan_filter,
            'top_fans': top_fans_display,
            'total_followers': user.followers.count(),
            'total_posts': user.posts.filter(is_active=True).count(),
            'recommended_content': recommended_content,
            'trending_topics': trending_topics,
            'engagement_insights': engagement_insights,
        })
        return render(request, 'dashboard/celebrity_dashboard.html', context)

    else:  # fan
        # Fan dashboard data
        from apps.fans.models import FanProfile
        from apps.fanclubs.models import FanClubMembership
        from apps.posts.models import Post

        try:
            fan_profile = user.fan_profile
        except:
            fan_profile = FanProfile.objects.create(user=user)

        # Get feed posts from followed users
        following_ids = user.following.values_list('following', flat=True)
        feed_posts = Post.objects.filter(
            Q(author__in=following_ids) | Q(author=user),
            is_active=True
        ).select_related('author').order_by('-created_at')[:10]

        # Get AI-powered recommendations for fan
        recommended_celebrities = []
        recommended_posts = []
        recommended_events = []
        trending_hashtags = []

        try:
            from algorithms.recommendation import RecommendationEngine
            from algorithms.sentiment import SentimentAnalyzer
            from datetime import timedelta

            rec_engine = RecommendationEngine()
            analyzer = SentimentAnalyzer()

            # Get comprehensive recommendations
            all_recommendations = rec_engine.get_user_recommendations(
                user,
                recommendation_type='all',
                limit=5
            )

            recommended_celebrities = all_recommendations.get('celebrities', [])[:3]
            recommended_posts = all_recommendations.get('posts', [])[:4]
            recommended_events = all_recommendations.get('events', [])[:2]

            # Get trending hashtags
            recent_posts_text = ' '.join([
                p.content for p in Post.objects.filter(
                    is_active=True,
                    created_at__gte=timezone.now() - timedelta(days=1)
                )[:50]
            ])
            trending_hashtags = analyzer.extract_hashtags(recent_posts_text)[:5]

        except Exception:
            # Fallback: basic recommendations
            recommended_celebrities = User.objects.filter(
                user_type='celebrity',
                is_verified=True,
                is_active=True
            ).exclude(
                id__in=following_ids
            ).order_by('-points')[:3]

        context.update({
            'fan_profile': fan_profile,
            'feed_posts': feed_posts,
            'club_memberships': FanClubMembership.objects.filter(
                user=user,
                status='active'
            ).select_related('fanclub')[:5],
            'upcoming_events': user.event_registrations.filter(
                event__start_datetime__gte=timezone.now(),
                status='confirmed'
            ).select_related('event')[:5] if hasattr(user, 'event_registrations') else [],
            'total_following': user.following.count(),
            'recommended_celebrities': recommended_celebrities,
            'recommended_posts': recommended_posts,
            'recommended_events': recommended_events,
            'trending_hashtags': trending_hashtags,
        })
        return render(request, 'dashboard/fan_dashboard.html', context)


@login_required
def smart_feed_view(request):
    """Smart feed that routes to appropriate feed based on user type"""
    if request.user.user_type == 'celebrity':
        # Redirect celebrities to celebrity feed
        return redirect('celebrity_feed')
    else:
        # Redirect fans to fan feed
        return redirect('fan_feed')


@login_required
def profile_view(request, username):
    """View user profile"""
    profile_user = get_object_or_404(User, username=username)

    # Check if blocked
    from apps.accounts.models import UserBlock
    if UserBlock.objects.filter(
        blocker=profile_user,
        blocked=request.user
    ).exists():
        messages.error(request, 'You cannot view this profile.')
        return redirect('dashboard')

    # Check privacy settings for posts
    can_view_posts = True
    if profile_user != request.user:
        try:
            preferences = profile_user.preferences
            if preferences.who_can_see_posts == 'nobody':
                can_view_posts = False
            elif preferences.who_can_see_posts == 'followers':
                can_view_posts = UserFollowing.objects.filter(
                    follower=request.user,
                    following=profile_user
                ).exists()
        except:
            can_view_posts = True

    # Get user statistics
    followers_count = profile_user.followers.count()
    following_count = profile_user.following.count()

    # Check if current user follows this user
    is_following = False
    is_blocked = False
    can_message = False

    if request.user.is_authenticated and request.user != profile_user:
        is_following = UserFollowing.objects.filter(
            follower=request.user,
            following=profile_user
        ).exists()

        is_blocked = UserBlock.objects.filter(
            blocker=request.user,
            blocked=profile_user
        ).exists()

        # Check if mutual follow for messaging
        if is_following:
            mutual_follow = UserFollowing.objects.filter(
                follower=profile_user,
                following=request.user
            ).exists()
            can_message = mutual_follow

    # Get posts
    from apps.posts.models import Post
    if can_view_posts:
        posts = profile_user.posts.filter(
            is_active=True
        ).order_by('-created_at')
    else:
        posts = Post.objects.none()

    # Paginate posts
    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile_user': profile_user,
        'followers_count': followers_count,
        'following_count': following_count,
        'posts_count': profile_user.posts.filter(is_active=True).count(),
        'is_following': is_following,
        'is_blocked': is_blocked,
        'can_message': can_message,
        'can_view_posts': can_view_posts,
        'is_own_profile': request.user == profile_user,
        'posts': page_obj,
    }

    # Add type-specific data
    if profile_user.user_type == 'celebrity':
        try:
            context['celebrity_profile'] = profile_user.celebrity_profile
            from apps.events.models import Event
            from apps.merchandise.models import Merchandise

            # Get all events (upcoming and past)
            context['upcoming_events'] = Event.objects.filter(
                celebrity=profile_user,
                start_datetime__gte=timezone.now(),
                status='published'
            ).order_by('start_datetime')[:6]

            context['past_events'] = Event.objects.filter(
                celebrity=profile_user,
                start_datetime__lt=timezone.now(),
                status__in=['completed', 'published']
            ).order_by('-start_datetime')[:4]

            # Get merchandise
            context['merchandise'] = Merchandise.objects.filter(
                celebrity=profile_user,
                status='available'
            ).order_by('-created_at')[:6]

            context['merchandise_count'] = Merchandise.objects.filter(
                celebrity=profile_user,
                status='available'
            ).count()

            context['events_count'] = Event.objects.filter(
                celebrity=profile_user,
                status='published'
            ).count()

            # Add subscription data
            from apps.celebrities.models import Subscription
            context['subscriber_count'] = Subscription.objects.filter(
                celebrity=profile_user.celebrity_profile,
                status='active'
            ).count()

            # Check if current user is subscribed
            if request.user.is_authenticated and request.user != profile_user:
                try:
                    user_subscription = Subscription.objects.get(
                        celebrity=profile_user.celebrity_profile,
                        subscriber=request.user
                    )
                    context['is_subscribed'] = user_subscription.is_active()
                    context['user_subscription'] = user_subscription
                except Subscription.DoesNotExist:
                    context['is_subscribed'] = False

            # Add default fanclub
            from apps.fanclubs.models import FanClub, FanClubMembership
            from apps.celebrities.utils import get_or_create_default_fanclub
            celebrity_fanclub = get_or_create_default_fanclub(profile_user)
            context['celebrity_fanclub'] = celebrity_fanclub

            # Check if current user is a member
            if request.user.is_authenticated and request.user != profile_user:
                is_fanclub_member = FanClubMembership.objects.filter(
                    user=request.user,
                    fanclub=celebrity_fanclub,
                    status='active'
                ).exists()
                context['is_fanclub_member'] = is_fanclub_member
            else:
                context['is_fanclub_member'] = False
        except Exception as e:
            print(f"Error loading celebrity profile data: {e}")
            pass

    elif profile_user.user_type == 'fan':
        try:
            from apps.fanclubs.models import FanClubMembership
            from apps.celebrities.models import Subscription

            context['fan_profile'] = profile_user.fan_profile

            # Get fanclub memberships
            context['fanclub_memberships'] = FanClubMembership.objects.filter(
                user=profile_user,
                status='active'
            ).select_related('fanclub', 'fanclub__celebrity')[:6]

            context['fanclub_count'] = FanClubMembership.objects.filter(
                user=profile_user,
                status='active'
            ).count()

            # Get active subscriptions
            context['active_subscriptions'] = Subscription.objects.filter(
                subscriber=profile_user,
                status='active'
            ).select_related('celebrity')[:6]

            context['subscription_count'] = Subscription.objects.filter(
                subscriber=profile_user,
                status='active'
            ).count()

            # Get badges if available
            if hasattr(profile_user, 'earned_badges'):
                context['badges'] = profile_user.earned_badges.all()[:8]
        except Exception as e:
            print(f"Error loading fan profile data: {e}")
            pass

    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    """Edit user profile"""
    # Get social links from user model (available for all user types)
    social_links = request.user.social_links or {}

    # Get celebrity profile if applicable
    celebrity_profile = None
    if request.user.user_type == 'celebrity':
        try:
            celebrity_profile = request.user.celebrity_profile
        except:
            pass

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            user = form.save(commit=False)

            # Handle social links for all user types
            social_links = {
                'facebook': request.POST.get('facebook', ''),
                'instagram': request.POST.get('instagram', ''),
                'twitter': request.POST.get('twitter', ''),
                'youtube': request.POST.get('youtube', ''),
                'tiktok': request.POST.get('tiktok', ''),
                'linkedin': request.POST.get('linkedin', ''),
            }
            # Remove empty values
            social_links = {k: v for k, v in social_links.items() if v}
            user.social_links = social_links
            user.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('profile', username=request.user.username)
    else:
        form = ProfileUpdateForm(instance=request.user)

    context = {
        'form': form,
        'celebrity_profile': celebrity_profile,
        'social_links': social_links,
    }
    return render(request, 'accounts/edit_profile.html', context)


@login_required
def settings_view(request):
    """User settings and preferences"""
    try:
        preferences = request.user.preferences
    except UserPreferences.DoesNotExist:
        preferences = UserPreferences.objects.create(user=request.user)

    if request.method == 'POST':
        form = PreferencesForm(request.POST, instance=preferences)

        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings')
    else:
        form = PreferencesForm(instance=preferences)

    context = {
        'preferences_form': form,
        'login_history': LoginHistory.objects.filter(
            user=request.user
        ).order_by('-login_time')[:10]
    }

    return render(request, 'accounts/settings.html', context)


@login_required
def change_password_view(request):
    """Change password view"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('settings')
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def follow_user_view(request, username):
    """Follow/unfollow a user"""
    if request.method != 'POST':
        return HttpResponseForbidden()

    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': "You can't follow yourself."}, status=400)
        messages.error(request, "You can't follow yourself.")
        return redirect('profile', username=username)

    following, created = UserFollowing.objects.get_or_create(
        follower=request.user,
        following=target_user
    )

    if not created:
        # Already following, so unfollow
        following.delete()

        # Update counts
        request.user.total_following = max(0, request.user.total_following - 1)
        request.user.save(update_fields=['total_following'])

        target_user.total_followers = max(0, target_user.total_followers - 1)
        target_user.save(update_fields=['total_followers'])

        request.user.add_points(-3, f"Unfollowed {target_user.username}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'action': 'unfollowed',
                'message': f'You unfollowed {target_user.username}',
                'followers_count': target_user.total_followers,
                'following_count': target_user.total_following
            })

        messages.info(request, f'You unfollowed {target_user.username}')
    else:
        # New follow
        # Update counts
        request.user.total_following += 1
        request.user.save(update_fields=['total_following'])

        target_user.total_followers += 1
        target_user.save(update_fields=['total_followers'])

        request.user.add_points(3, f"Followed {target_user.username}")

        # Create notification
        from apps.notifications.models import Notification
        Notification.objects.create(
            recipient=target_user,
            sender=request.user,
            notification_type='follow',
            message=f"{request.user.username} started following you!",
            description='You have a new follower.',
            target_url=f"/accounts/profile/{request.user.username}/",
        )


        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'action': 'followed',
                'message': f'You are now following {target_user.username}',
                'followers_count': target_user.total_followers,
                'following_count': target_user.total_following
            })

        messages.success(request, f'You are now following {target_user.username}')

    return redirect('profile', username=username)


@login_required
def followers_list_view(request, username):
    """View user's followers"""
    user = get_object_or_404(User, username=username)

    # Check privacy settings
    try:
        preferences = user.preferences
        if preferences.who_can_see_followers == 'nobody':
            if user != request.user:
                if request.GET.get('ajax') == '1':
                    return JsonResponse({'success': False, 'error': 'This user\'s followers are private.'}, status=403)
                messages.error(request, 'This user\'s followers are private.')
                return redirect('profile', username=username)
        elif preferences.who_can_see_followers == 'followers':
            if not UserFollowing.objects.filter(
                follower=request.user,
                following=user
            ).exists() and user != request.user:
                if request.GET.get('ajax') == '1':
                    return JsonResponse({'success': False, 'error': 'Only followers can see this list.'}, status=403)
                messages.error(request, 'Only followers can see this list.')
                return redirect('profile', username=username)
    except:
        pass

    followers = User.objects.filter(
        following__following=user
    ).order_by('-following__created_at')

    # AJAX request - return JSON
    if request.GET.get('ajax') == '1':
        search_query = request.GET.get('search', '').strip()
        if search_query:
            followers = followers.filter(
                Q(username__icontains=search_query) |
                Q(full_name__icontains=search_query)
            )

        followers_data = []
        for follower in followers[:50]:  # Limit to 50 for performance
            # Check if current user follows this follower
            is_following = UserFollowing.objects.filter(
                follower=request.user,
                following=follower
            ).exists() if follower != request.user else False

            followers_data.append({
                'id': follower.id,
                'username': follower.username,
                'full_name': follower.full_name or follower.username,
                'profile_picture': follower.profile_picture.url if follower.profile_picture else None,
                'is_verified': follower.is_verified,
                'user_type': follower.user_type,
                'is_following': is_following,
                'is_own_profile': follower == request.user,
                'profile_url': f'/profile/{follower.username}/'
            })

        return JsonResponse({
            'success': True,
            'followers': followers_data,
            'total_count': followers.count()
        })

    # Pagination
    paginator = Paginator(followers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile_user': user,
        'followers': page_obj,
        'total_count': paginator.count,
        'is_own_profile': user == request.user
    }

    return render(request, 'accounts/followers.html', context)


@login_required
def following_list_view(request, username):
    """View user's following list"""
    user = get_object_or_404(User, username=username)

    following = User.objects.filter(
        followers__follower=user
    ).order_by('-followers__created_at')

    # AJAX request - return JSON
    if request.GET.get('ajax') == '1':
        search_query = request.GET.get('search', '').strip()
        if search_query:
            following = following.filter(
                Q(username__icontains=search_query) |
                Q(full_name__icontains=search_query)
            )

        following_data = []
        for followed_user in following[:50]:  # Limit to 50 for performance
            # Check if current user follows this user
            is_following = UserFollowing.objects.filter(
                follower=request.user,
                following=followed_user
            ).exists() if followed_user != request.user else False

            following_data.append({
                'id': followed_user.id,
                'username': followed_user.username,
                'full_name': followed_user.full_name or followed_user.username,
                'profile_picture': followed_user.profile_picture.url if followed_user.profile_picture else None,
                'is_verified': followed_user.is_verified,
                'user_type': followed_user.user_type,
                'is_following': is_following,
                'is_own_profile': followed_user == request.user,
                'profile_url': f'/profile/{followed_user.username}/'
            })

        return JsonResponse({
            'success': True,
            'following': following_data,
            'total_count': following.count()
        })

    # Pagination
    paginator = Paginator(following, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile_user': user,
        'following': page_obj,
        'total_count': paginator.count,
        'is_own_profile': user == request.user
    }

    return render(request, 'accounts/following.html', context)


@login_required
def points_history_view(request):
    """View points history"""
    history = PointsHistory.objects.filter(user=request.user)
    
    # Pagination
    paginator = Paginator(history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'history': page_obj,
        'current_points': request.user.points,
        'current_rank': request.user.rank,
    }
    
    return render(request, 'accounts/points_history.html', context)


@login_required
def celebrity_follow_suggestions(request):
    """Suggest celebrities to follow for new users"""
    if request.user.following.count() >= 5:
        return redirect('dashboard')
    
    # Get top celebrities by category
    from django.conf import settings
    categories = settings.MANTRA_SETTINGS['CELEBRITY_CATEGORIES']
    
    suggestions = {}
    for cat_code, cat_name in categories:
        celebs = User.objects.filter(
            user_type='celebrity',
            is_active=True,
            is_verified=True
        ).exclude(
            followers__follower=request.user
        ).order_by('-points')[:3]
        
        if celebs:
            suggestions[cat_name] = celebs
    
    if request.method == 'POST':
        # Handle follow selections
        selected = request.POST.getlist('celebrities')
        for celeb_id in selected:
            try:
                celeb = User.objects.get(id=celeb_id, user_type='celebrity')
                UserFollowing.objects.get_or_create(
                    follower=request.user,
                    following=celeb
                )
                request.user.add_points(3, f"Followed {celeb.username}")
            except User.DoesNotExist:
                pass
        
        messages.success(request, 'Great! You are now following your favorite celebrities.')
        return redirect('dashboard')
    
    context = {
        'suggestions': suggestions,
        'skip_url': 'dashboard'
    }

    return render(request, 'accounts/celebrity_suggestions.html', context)

# ==================== Account Management ====================

@login_required
def deactivate_account(request):
    """Temporarily deactivate user account"""
    user = request.user
    user.is_active = False
    user.save(update_fields=['is_active'])
    logout(request)
    messages.info(request, 'Your account has been deactivated. You can log in again anytime to reactivate it.')
    return redirect('login')  # or redirect('home')


@login_required
def delete_account(request):
    """Permanently delete user account"""
    user = request.user
    logout(request)
    username = user.username
    user.delete()
    messages.success(request, f'Account "{username}" deleted permanently.')
    return redirect('home')

# ==================== Error Handlers ====================

def error_404_view(request, exception):
    """Custom 404 error page"""
    return render(request, 'errors/404.html', status=404)


def error_500_view(request):
    """Custom 500 error page"""
    return render(request, 'errors/500.html', status=500)


def error_403_view(request, exception):
    """Custom 403 error page"""
    return render(request, 'errors/403.html', status=403)


def error_400_view(request, exception):
    """Custom 400 error page"""
    return render(request, 'errors/400.html', status=400)