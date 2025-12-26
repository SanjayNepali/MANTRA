# apps/celebrities/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal

from apps.accounts.models import User
from .models import (
    CelebrityProfile, Subscription, KYCDocument, 
    CelebrityEarning, CelebrityAnalytics, CelebrityAchievement
)
from .forms import (
    CelebrityProfileForm, KYCUploadForm, SubscriptionSettingsForm,
    PaymentMethodForm
)

@method_decorator(login_required, name='dispatch')
class CelebrityDashboardView(TemplateView):
    """Dashboard for celebrity users"""
    template_name = 'dashboard/celebrity_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'celebrity':
            messages.error(request, 'Access restricted to celebrities only')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            profile = self.request.user.celebrity_profile
        except CelebrityProfile.DoesNotExist:
            # Create profile if doesn't exist
            profile = CelebrityProfile.objects.create(
                user=self.request.user,
                category='other'
            )
        
        # Get analytics for last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        analytics = CelebrityAnalytics.objects.filter(
            celebrity=self.request.user,
            date__gte=thirty_days_ago
        )
        
        # Calculate totals
        context['profile'] = profile
        context['total_followers'] = self.request.user.followers.count()
        
        # Use correct query for subscribers
        context['total_subscribers'] = Subscription.objects.filter(
            celebrity=self.request.user,
            status='active'
        ).count()
        
        context['total_earnings'] = profile.total_earnings
        context['this_month_earnings'] = CelebrityEarning.objects.filter(
            celebrity=self.request.user,
            created_at__gte=thirty_days_ago
        ).aggregate(total=Sum('amount'))['total'] or 0

        # KYC Verification Status
        context['verification_status'] = profile.verification_status
        context['verification_date'] = profile.verification_date
        context['kyc_documents'] = KYCDocument.objects.filter(celebrity=self.request.user).order_by('-uploaded_at')
        context['pending_kyc'] = profile.verification_status == 'pending'
        context['verified'] = profile.verification_status == 'approved'
        context['rejected'] = profile.verification_status == 'rejected'
        
        # Engagement metrics - FIXED: Use correct field names
        # Use profile_visits + post_views for total views
        context['total_views'] = (analytics.aggregate(
            total=Sum('profile_visits')
        )['total'] or 0) + (analytics.aggregate(
            total=Sum('post_views')
        )['total'] or 0)
        
        # Calculate engagement rate manually
        total_engagement = (analytics.aggregate(
            total=Sum('post_likes')
        )['total'] or 0) + (analytics.aggregate(
            total=Sum('post_comments')
        )['total'] or 0) + (analytics.aggregate(
            total=Sum('post_shares')
        )['total'] or 0)
        
        total_views = context['total_views']
        context['engagement_rate'] = round((total_engagement / total_views * 100) if total_views > 0 else 0, 2)
        
        # Recent activities
        context['recent_subscribers'] = Subscription.objects.filter(
            celebrity=self.request.user
        ).select_related('subscriber').order_by('-created_at')[:5]

        context['recent_earnings'] = CelebrityEarning.objects.filter(
            celebrity=self.request.user
        ).order_by('-created_at')[:5]

        # FIXED: Remove the check_and_unlock functionality for now
        # Just get unlocked achievements
        context['recent_achievements'] = CelebrityAchievement.objects.filter(
            celebrity=self.request.user,
            is_unlocked=True
        ).order_by('-unlocked_at')[:3]

        # Official Fanclub stats
        try:
            from apps.fanclubs.models import FanClub
            official_fanclub = FanClub.objects.filter(
                celebrity=self.request.user,
                is_official=True
            ).first()
            if official_fanclub:
                context['official_fanclub'] = official_fanclub
                context['fanclub_members'] = official_fanclub.memberships.filter(status='active').count()
                context['fanclub_messages'] = official_fanclub.posts.count() if hasattr(official_fanclub, 'posts') else 0
            else:
                context['official_fanclub'] = None
                context['fanclub_members'] = 0
                context['fanclub_messages'] = 0
        except Exception as e:
            print(f"Error loading fanclub data: {e}")
            context['official_fanclub'] = None
            context['fanclub_members'] = 0
            context['fanclub_messages'] = 0

        # Additional dashboard stats
        # Get total posts count
        try:
            from apps.posts.models import Post
            context['total_posts'] = Post.objects.filter(author=self.request.user).count()
        except:
            context['total_posts'] = 0
            
        # Get total likes count
        try:
            from apps.posts.models import Like
            context['total_likes'] = Like.objects.filter(post__author=self.request.user).count()
        except:
            context['total_likes'] = 0
            
        # New followers this week
        try:
            from apps.accounts.models import UserFollowing
            week_ago = timezone.now() - timedelta(days=7)
            context['new_followers_this_week'] = UserFollowing.objects.filter(
                following=self.request.user,
                created_at__gte=week_ago
            ).count()
        except:
            context['new_followers_this_week'] = 0
        
        # Revenue data
        context['revenue_this_month'] = context['this_month_earnings']
        context['pending_revenue'] = 0  # You can implement pending revenue logic
        
        # Fan posts data (placeholder - implement based on your app structure)
        context['fan_posts'] = []
        context['fan_filter'] = 'all'
        
        # Upcoming events (placeholder)
        context['upcoming_events'] = []
        
        # Top fans (placeholder)
        context['top_fans'] = []

        return context
    
class CelebrityListView(TemplateView):
    """List all celebrities with different sections"""
    template_name = 'celebrities/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Base queryset for all celebrities
        base_qs = User.objects.filter(
            user_type='celebrity',
            is_active=True,
            is_banned=False
        ).select_related('celebrity_profile')

        # Unverified celebrities (pending verification)
        context['unverified_celebrities'] = base_qs.filter(
            celebrity_profile__verification_status='pending'
        ).order_by('-created_at')[:10]

        # Top celebrities (by points)
        context['top_celebrities'] = base_qs.filter(
            celebrity_profile__verification_status='approved'
        ).order_by('-points')[:10]

        # Trending celebrities (most followed this month)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['trending_celebrities'] = base_qs.filter(
            celebrity_profile__verification_status='approved',
            created_at__gte=thirty_days_ago
        ).annotate(
            followers_count=Count('followers')
        ).order_by('-followers_count')[:10]

        # Smart AI-powered celebrity recommendations
        if self.request.user.is_authenticated and self.request.user.user_type == 'fan':
            try:
                from algorithms.integration import get_user_recommendations

                # Get personalized celebrity recommendations with caching
                all_recommendations = get_user_recommendations(
                    self.request.user,
                    recommendation_type='celebrities',
                    limit=10,
                    use_cache=True
                )

                recommended_celeb_list = all_recommendations.get('celebrities', [])

                if recommended_celeb_list:
                    context['recommended_celebrities'] = recommended_celeb_list[:10]
                else:
                    # Fallback: Show verified celebrities with high points
                    context['recommended_celebrities'] = base_qs.filter(
                        celebrity_profile__verification_status='approved'
                    ).exclude(
                        id__in=self.request.user.following.values_list('following_id', flat=True)
                    ).order_by('-points')[:10]

            except Exception:
                # Fallback: Show top verified celebrities
                context['recommended_celebrities'] = base_qs.filter(
                    celebrity_profile__verification_status='approved'
                ).order_by('-points')[:10]
        else:
            # For non-authenticated users, show top rated
            context['recommended_celebrities'] = base_qs.filter(
                celebrity_profile__verification_status='approved'
            ).order_by('-points')[:10]

        # All verified celebrities for main list with filtering
        queryset = base_qs.filter(celebrity_profile__verification_status='approved')

        # Filter by category (categories is a JSONField containing a list)
        # For SQLite compatibility, filter by checking if category string is in JSON
        category = self.request.GET.get('category')
        if category:
            # Get all celebrities and filter in Python for SQLite compatibility
            all_celebs = queryset.select_related('celebrity_profile')
            filtered_ids = [
                celeb.id for celeb in all_celebs
                if hasattr(celeb, 'celebrity_profile') and
                category in (celeb.celebrity_profile.categories or [])
            ]
            queryset = queryset.filter(id__in=filtered_ids)
            context['current_category'] = category

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(bio__icontains=search)
            )
            context['search_query'] = search

        # Sorting
        sort = self.request.GET.get('sort', '-points')
        if sort == '-followers':
            queryset = queryset.annotate(
                followers_count=Count('followers')
            ).order_by('-followers_count')
        elif sort == '-created_at':
            queryset = queryset.order_by('-created_at')
        elif sort == 'name':
            queryset = queryset.order_by('first_name', 'last_name', 'username')
        else:  # Default: -points
            queryset = queryset.order_by('-points')

        context['current_sort'] = sort

        # Pagination
        paginator = Paginator(queryset, 20)
        page_number = self.request.GET.get('page')
        context['celebrities'] = paginator.get_page(page_number)

        # Categories
        context['categories'] = settings.MANTRA_SETTINGS['CELEBRITY_CATEGORIES']

        return context


class CelebrityDetailView(DetailView):
    """View celebrity profile"""
    model = User
    template_name = 'celebrities/detail.html'
    context_object_name = 'celebrity'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    
    def get_queryset(self):
        return User.objects.filter(
            user_type='celebrity'
        ).select_related('celebrity_profile')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        celebrity = self.object
        
        # Get profile
        try:
            profile = celebrity.celebrity_profile
        except CelebrityProfile.DoesNotExist:
            profile = None
        
        context['profile'] = profile
        context['followers_count'] = celebrity.followers.count()
        context['following_count'] = celebrity.following.count()
        
        # Check if user follows this celebrity
        if self.request.user.is_authenticated:
            from apps.accounts.models import UserFollowing
            context['is_following'] = UserFollowing.objects.filter(
                follower=self.request.user,
                following=celebrity
            ).exists()
            
            # Check subscription status
            if profile:
                context['is_subscribed'] = Subscription.objects.filter(
                    subscriber=self.request.user,
                    celebrity=celebrity,
                    status='active'
                ).exists()
        else:
            context['is_following'] = False
            context['is_subscribed'] = False
        
        # Get recent posts (will be implemented later)
        # context['recent_posts'] = Post.objects.filter(author=celebrity)[:6]
        
        # Update view count
        if profile:
            profile.total_views += 1
            profile.save(update_fields=['total_views'])
            
            # Update daily analytics
            today = timezone.now().date()
            analytics, created = CelebrityAnalytics.objects.get_or_create(
                celebrity=celebrity,
                date=today
            )
            analytics.profile_views += 1
            analytics.save()
        
        return context


class CelebrityProfileView(DetailView):
    """Celebrity-specific profile view"""
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        username = self.kwargs.get('username')
        return get_object_or_404(
            User.objects.select_related('celebrity_profile'),
            username=username,
            user_type='celebrity'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.object
        
        # Add celebrity-specific context
        context.update({
            'celebrity_profile': profile_user.celebrity_profile,
            'is_celebrity_profile': True,
        })
        
        return context

@login_required
def celebrity_profile_setup(request):
    """Setup celebrity profile"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    try:
        profile = request.user.celebrity_profile
    except CelebrityProfile.DoesNotExist:
        profile = CelebrityProfile.objects.create(
            user=request.user,
            category='other'
        )
    
    if request.method == 'POST':
        form = CelebrityProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('celebrity_dashboard')
    else:
        form = CelebrityProfileForm(instance=profile)
    
    return render(request, 'celebrities/profile_setup.html', {
        'form': form,
        'profile': profile
    })


@login_required
def kyc_upload(request):
    """Upload KYC documents with proper redirect"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    profile = request.user.celebrity_profile
    
    if request.method == 'POST':
        form = KYCUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.celebrity = request.user
            document.save()
            
            # Update verification status to pending
            profile.verification_status = 'pending'
            profile.document_submitted_at = timezone.now()
            profile.save()

            messages.success(request, 'KYC document uploaded successfully! Your submission is now under review.')
            return redirect('celebrity_dashboard')  # Fixed redirect
    else:
        form = KYCUploadForm()
    
    documents = KYCDocument.objects.filter(celebrity=request.user)
    
    return render(request, 'celebrities/kyc_upload.html', {
        'form': form,
        'documents': documents,
        'profile': profile
    })

@login_required
def kyc_resubmit(request):
    """Resubmit KYC documents after rejection or request for more docs"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    profile = request.user.celebrity_profile
    
    # Check if resubmission is needed or if previously rejected
    if not profile.needs_resubmission and profile.verification_status != 'rejected':
        messages.info(request, 'No resubmission required.')
        return redirect('celebrity_dashboard')
    
    if request.method == 'POST':
        form = KYCUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.celebrity = request.user
            document.save()
            
            # Reset resubmission flag and update status
            profile.verification_status = 'pending'
            profile.needs_resubmission = False
            profile.document_submitted_at = timezone.now()
            profile.save()

            messages.success(request, 'Additional documents submitted successfully! Your KYC is back in review.')
            return redirect('celebrity_dashboard')
    else:
        form = KYCUploadForm()
    
    # Get previous rejection notes safely
    rejection_notes = getattr(profile, 'verification_notes', '')
    
    return render(request, 'celebrities/kyc_resubmit.html', {
        'form': form,
        'profile': profile,
        'rejection_notes': rejection_notes
    })

@login_required
def subscription_settings(request):
    """Manage subscription settings"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    profile = request.user.celebrity_profile
    
    if request.method == 'POST':
        form = SubscriptionSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subscription settings updated!')
            return redirect('celebrity_dashboard')
    else:
        form = SubscriptionSettingsForm(instance=profile)
    
    return render(request, 'celebrities/subscription_settings.html', {
        'form': form,
        'profile': profile,
        'subscribers_count': profile.subscription_records.filter(
            status='active'
        ).count()
    })


@login_required
def payment_methods(request):
    """Manage payment methods"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    profile = request.user.celebrity_profile
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, request.FILES)
        if form.is_valid():
            method = form.cleaned_data['payment_method']
            qr_code = form.cleaned_data['qr_code']
            
            # Save QR code
            if qr_code:
                import os
                from django.core.files.storage import default_storage
                
                filename = f"payment_qr/{request.user.id}_{method}.png"
                path = default_storage.save(filename, qr_code)
                
                # Update payment methods
                if not profile.payment_methods:
                    profile.payment_methods = {}
                profile.payment_methods[method] = path
                profile.save()
            
            messages.success(request, f'{method} payment method updated!')
            return redirect('payment_methods')
    else:
        form = PaymentMethodForm()
    
    return render(request, 'celebrities/payment_methods.html', {
        'form': form,
        'profile': profile,
        'payment_methods': profile.payment_methods or {}
    })


@login_required
def subscribe_to_celebrity(request, username):
    """Subscribe to a celebrity"""
    celebrity_user = get_object_or_404(User, username=username, user_type='celebrity')
    profile = celebrity_user.celebrity_profile

    # Check if already subscribed
    existing = Subscription.objects.filter(
        subscriber=request.user,
        celebrity=celebrity_user,
        status='active'
    ).first()

    if request.method == 'GET':
        # Show payment/subscription confirmation page
        if existing:
            messages.info(request, f'You are already subscribed to {celebrity_user.username}.')
            return redirect('profile', username=username)

        context = {
            'celebrity_user': celebrity_user,
            'celebrity_profile': profile,
            'subscription_price': profile.default_subscription_price or 9.99,
        }
        return render(request, 'celebrities/subscribe.html', context)

    # POST - Initiate eSewa payment for subscription
    if existing:
        return JsonResponse({'error': 'Already subscribed'}, status=400)

    from datetime import timedelta
    from apps.payments.models import PaymentTransaction
    from django.urls import reverse
    from django.conf import settings

    # Create pending subscription
    subscription = Subscription.objects.create(
        subscriber=request.user,
        celebrity=celebrity_user,
        end_date=timezone.now() + timedelta(days=30),
        amount_paid=profile.default_subscription_price,
        payment_method='esewa',
        status='pending',
        transaction_id=f'SUB{timezone.now().timestamp()}'
    )

    # Create payment transaction
    payment = PaymentTransaction.objects.create(
        user=request.user,
        amount=profile.default_subscription_price,
        payment_method='esewa',
        payment_type='subscription',
        related_object_id=str(subscription.id),
        related_object_type='subscription',
        status='pending',
        metadata={
            'celebrity_id': str(celebrity_user.id),
            'celebrity_username': celebrity_user.username,
            'subscription_id': str(subscription.id)
        }
    )

    # Generate eSewa payment parameters
    success_url = request.build_absolute_uri(
        reverse('esewa_success')
    )
    failure_url = request.build_absolute_uri(
        reverse('esewa_failure')
    )

    # Generate eSewa v2 signature
    from utils.helpers import generate_esewa_signature

    total_amount = str(payment.amount)
    transaction_uuid = payment.transaction_id
    product_code = settings.ESEWA_MERCHANT_CODE

    # Create message for signature: total_amount,transaction_uuid,product_code
    signature_message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    signature = generate_esewa_signature(signature_message, settings.ESEWA_SECRET_KEY)

    # Store payment info in session for verification
    request.session[f'payment_{payment.transaction_id}'] = {
        'amount': str(payment.amount),
        'payment_id': str(payment.id),
        'type': 'subscription',
        'reference_id': str(subscription.id),
        'celebrity_username': celebrity_user.username
    }

    context = {
        'esewa_url': settings.ESEWA_PAYMENT_URL,
        'amount': str(payment.amount),
        'transaction_id': payment.transaction_id,
        'merchant_code': settings.ESEWA_MERCHANT_CODE,
        'success_url': success_url,
        'failure_url': failure_url,
        'signature': signature,
        'celebrity_username': celebrity_user.username,
    }

    return render(request, 'payments/esewa_payment.html', context)


@login_required
def celebrity_analytics(request):
    """View detailed analytics"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    profile = request.user.celebrity_profile
    
    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    analytics = CelebrityAnalytics.objects.filter(
        celebrity=request.user,
        date__gte=start_date
    ).order_by('date')
    
    # Prepare data for charts
    dates = []
    views = []
    followers = []
    earnings = []
    
    for entry in analytics:
        dates.append(entry.date.strftime('%Y-%m-%d'))
        views.append(entry.profile_views + entry.post_views)
        followers.append(entry.new_followers - entry.lost_followers)
        earnings.append(float(entry.earnings))
    
    context = {
        'profile': profile,
        'analytics': analytics,
        'chart_data': {
            'dates': dates,
            'views': views,
            'followers': followers,
            'earnings': earnings
        },
        'total_views': sum(views),
        'total_new_followers': sum(followers),
        'total_earnings': sum(earnings),
        'days': days
    }
    
    return render(request, 'celebrities/analytics.html', context)


@login_required
def celebrity_achievements(request):
    """View achievements"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    profile = request.user.celebrity_profile
    
    # Check and unlock achievements
    achievements = CelebrityAchievement.objects.filter(celebrity=request.user)
    for achievement in achievements:
        achievement.check_and_unlock()
    
    unlocked = achievements.filter(is_unlocked=True)
    locked = achievements.filter(is_unlocked=False)
    
    context = {
        'profile': profile,
        'unlocked_achievements': unlocked,
        'locked_achievements': locked,
        'total_points_earned': unlocked.aggregate(
            total=Sum('points_reward')
        )['total'] or 0
    }
    
    return render(request, 'celebrities/achievements.html', context)


@login_required
def celebrity_feed(request):
    """Personalized feed for celebrities showing posts from users they follow"""
    if request.user.user_type != 'celebrity':
        messages.error(request, 'Access restricted to celebrities')
        return redirect('dashboard')

    # Get followed users
    from apps.accounts.models import UserFollowing
    from apps.posts.models import Post, Like

    followed_user_ids = UserFollowing.objects.filter(
        follower=request.user
    ).values_list('following_id', flat=True)

    followed_users = User.objects.filter(
        id__in=followed_user_ids
    )

    # Get sorting preference
    sort = request.GET.get('sort', 'recent')

    # Base queryset - posts from followed users
    posts = Post.objects.filter(
        author_id__in=followed_user_ids,
        is_active=True
    ).select_related('author')

    # Apply sorting
    if sort == 'top_fans':
        # Get top fans - users who engage most with celebrity's content
        # Comprehensive engagement scoring system
        from apps.merchandise.models import Order
        from apps.fanclubs.models import FanClubPost, FanClubMembership
        from apps.posts.models import Comment

        # Calculate engagement scores for each fan
        fan_scores = {}

        # 1. Post likes (1 point each)
        post_likes = Like.objects.filter(
            post__author=request.user
        ).values('user_id').annotate(like_count=Count('id'))
        for item in post_likes:
            fan_scores[item['user_id']] = fan_scores.get(item['user_id'], 0) + item['like_count']

        # 2. Comments (3 points each - more valuable than likes)
        comments = Comment.objects.filter(
            post__author=request.user
        ).values('user_id').annotate(comment_count=Count('id'))
        for item in comments:
            fan_scores[item['user_id']] = fan_scores.get(item['user_id'], 0) + (item['comment_count'] * 3)

        # 3. Subscriptions (50 points - high value)
        subscriptions = Subscription.objects.filter(
            celebrity=request.user,
            status='active'
        ).values_list('subscriber_id', flat=True)
        for user_id in subscriptions:
            fan_scores[user_id] = fan_scores.get(user_id, 0) + 50

        # 4. Merchandise purchases (20 points per order)
        try:
            merchandise_orders = Order.objects.filter(
                items__product__seller=request.user,
                status__in=['processing', 'shipped', 'delivered']
            ).values('user_id').annotate(order_count=Count('id'))
            for item in merchandise_orders:
                fan_scores[item['user_id']] = fan_scores.get(item['user_id'], 0) + (item['order_count'] * 20)
        except:
            pass

        # 5. Fanclub interactions (5 points per post/comment in fanclub)
        try:
            fanclub_posts = FanClubPost.objects.filter(
                fanclub__celebrity=request.user
            ).values('author_id').annotate(post_count=Count('id'))
            for item in fanclub_posts:
                fan_scores[item['author_id']] = fan_scores.get(item['author_id'], 0) + (item['post_count'] * 5)
        except:
            pass

        # 6. Fanclub membership (30 points for being a member)
        try:
            fanclub_members = FanClubMembership.objects.filter(
                fanclub__celebrity=request.user,
                is_active=True
            ).values_list('user_id', flat=True)
            for user_id in fanclub_members:
                fan_scores[user_id] = fan_scores.get(user_id, 0) + 30
        except:
            pass

        # Sort fans by engagement score and get top 50
        top_fan_ids = sorted(fan_scores.items(), key=lambda x: x[1], reverse=True)[:50]
        top_fan_ids = [user_id for user_id, score in top_fan_ids]

        # Filter posts from top fans
        posts = posts.filter(author_id__in=top_fan_ids).order_by('-created_at')

        # Add engagement scores to context for display
        context_top_fans = User.objects.filter(id__in=top_fan_ids[:10])
        for fan in context_top_fans:
            fan.engagement_score = fan_scores.get(fan.id, 0)

    elif sort == 'most_engaging':
        # Sort by total engagement (likes + comments)
        posts = posts.annotate(
            engagement_score=Count('likes') + Count('comments') * 2
        ).order_by('-engagement_score', '-created_at')

    elif sort == 'verified_only':
        # Show only verified users' posts
        posts = posts.filter(author__is_verified=True).order_by('-created_at')

    else:  # recent (default)
        posts = posts.order_by('-created_at')

    # Get AI-powered recommendations with caching
    recommended_posts = []
    recommended_users = []
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
        recommended_users = all_recommendations.get('potential_fans', [])[:5]
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

    except Exception:
        # Fallback: get popular content
        recommended_posts = Post.objects.filter(
            author_id__in=followed_user_ids,
            is_active=True,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).annotate(
            engagement=Count('likes') + Count('comments') * 2
        ).order_by('-engagement')[:4]

        recommended_users = User.objects.filter(
            is_active=True,
            is_verified=True
        ).exclude(
            id=request.user.id
        ).exclude(
            id__in=followed_user_ids
        ).order_by('-points')[:5]

    # Get suggested users (use recommended or fallback)
    suggested_users = recommended_users if recommended_users else User.objects.filter(
        is_active=True,
        is_verified=True
    ).exclude(
        id=request.user.id
    ).exclude(
        id__in=followed_user_ids
    ).order_by('-points')[:5]

    context = {
        'posts': posts[:20],
        'sort': sort,
        'followed_users_count': followed_users.count(),
        'trending_hashtags': trending_hashtags,
        'suggested_users': suggested_users,
        'recommended_posts': recommended_posts,
        'recommended_events': recommended_events,
    }

    return render(request, 'celebrities/feed.html', context)


@login_required
def cancel_subscription(request, subscription_id):
    """Cancel a subscription"""
    subscription = get_object_or_404(
        Subscription,
        id=subscription_id,
        subscriber=request.user
    )

    if subscription.status != 'active':
        messages.error(request, 'This subscription is already inactive')
        return redirect('my_subscriptions')

    if request.method == 'POST':
        subscription.status = 'cancelled'
        subscription.auto_renew = False
        subscription.save()

        messages.success(request, f'Subscription to {subscription.celebrity.user.username} has been cancelled')
        return redirect('my_subscriptions')

    context = {
        'subscription': subscription,
        'celebrity': subscription.celebrity.user
    }

    return render(request, 'celebrities/cancel_subscription.html', context)


@login_required
def renew_subscription(request, celebrity_id):
    """Renew or create a subscription"""
    celebrity_user = get_object_or_404(User, id=celebrity_id, user_type='celebrity')
    profile = celebrity_user.celebrity_profile

    # Check if user has an existing subscription
    existing = Subscription.objects.filter(
        subscriber=request.user,
        celebrity=celebrity_user
    ).first()

    subscription_type = request.POST.get('subscription_type', 'monthly')  # monthly or annual

    if request.method == 'POST':
        from datetime import timedelta

        # Calculate duration and price
        if subscription_type == 'annual':
            duration_days = 365
            amount = profile.default_subscription_price * 12 * Decimal('0.85')  # 15% discount
        else:
            duration_days = 30
            amount = profile.default_subscription_price

        if existing:
            # Renew existing subscription
            existing.end_date = timezone.now() + timedelta(days=duration_days)
            existing.status = 'active'
            existing.amount_paid = amount
            existing.transaction_id = f'TXN{timezone.now().timestamp()}'
            existing.save()

            messages.success(request, f'Subscription renewed successfully for {duration_days} days!')
        else:
            # Create new subscription
            subscription = Subscription.objects.create(
                subscriber=request.user,
                celebrity=celebrity_user,
                end_date=timezone.now() + timedelta(days=duration_days),
                amount_paid=amount,
                payment_method='simulated',
                transaction_id=f'TXN{timezone.now().timestamp()}'
            )

            # Award points
            if hasattr(request.user, 'add_points'):
                request.user.add_points(50, f"Subscribed to {celebrity_user.username}")

            # Add earnings to celebrity
            if hasattr(profile, 'add_earnings'):
                profile.add_earnings(amount, f"New subscription from {request.user.username}")

            messages.success(request, f'Successfully subscribed to {celebrity_user.username}!')

        return redirect('profile', username=celebrity_user.username)

    # Calculate prices
    monthly_price = profile.default_subscription_price
    annual_price = profile.default_subscription_price * 12 * Decimal('0.85')  # 15% discount

    context = {
        'celebrity_user': celebrity_user,
        'celebrity_profile': profile,
        'monthly_price': monthly_price,
        'annual_price': annual_price,
        'existing_subscription': existing,
        'is_renewal': existing is not None
    }

    return render(request, 'celebrities/renew_subscription.html', context)


@login_required
def toggle_auto_renew(request, subscription_id):
    """Toggle auto-renew for a subscription"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    subscription = get_object_or_404(
        Subscription,
        id=subscription_id,
        subscriber=request.user
    )

    subscription.auto_renew = not subscription.auto_renew
    subscription.save()

    return JsonResponse({
        'status': 'success',
        'auto_renew': subscription.auto_renew,
        'message': f'Auto-renew {"enabled" if subscription.auto_renew else "disabled"}'
    })


@login_required
def my_subscriptions(request):
    """View user's subscriptions"""
    subscriptions = Subscription.objects.filter(
        subscriber=request.user
    ).select_related('celebrity__user').order_by('-created_at')

    # Filter by status
    status_filter = request.GET.get('status', 'active')
    if status_filter == 'active':
        subscriptions = subscriptions.filter(status='active')
    elif status_filter == 'expired':
        subscriptions = subscriptions.filter(status='expired')
    elif status_filter == 'cancelled':
        subscriptions = subscriptions.filter(status='cancelled')

    context = {
        'subscriptions': subscriptions,
        'status_filter': status_filter
    }

    return render(request, 'celebrities/my_subscriptions.html', context)

@login_required
def celebrity_posts(request):
    """View for celebrities to manage their posts"""
    if request.user.user_type != 'celebrity':
        messages.error(request, 'Access restricted to celebrities only')
        return redirect('dashboard')
    
    # Get the celebrity's posts
    from apps.posts.models import Post
    
    posts = Post.objects.filter(
        author=request.user,
        is_active=True
    ).order_by('-created_at')
    
    # Get stats
    total_posts = posts.count()
    total_likes = sum(post.likes.count() for post in posts)
    total_comments = sum(post.comments.count() for post in posts)
    
    context = {
        'posts': posts,
        'total_posts': total_posts,
        'total_likes': total_likes,
        'total_comments': total_comments,
    }
    
    return render(request, 'celebrities/posts.html', context)

@login_required
def celebrity_events(request):
    """Celebrity events management view"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    from apps.events.models import Event
    events = Event.objects.filter(host=request.user).order_by('-date')
    
    return render(request, 'celebrities/events.html', {'events': events})

@login_required
def celebrity_merchandise(request):
    """Celebrity merchandise management view"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    from apps.merchandise.models import Product
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    
    return render(request, 'celebrities/merchandise.html', {'products': products})

@login_required
def celebrity_fanclubs(request):
    """Celebrity fanclubs management view"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    from apps.fanclubs.models import FanClub
    fanclubs = FanClub.objects.filter(celebrity=request.user).order_by('-created_at')
    
    return render(request, 'celebrities/fanclubs.html', {'fanclubs': fanclubs})

@login_required
def celebrity_settings(request):
    """Celebrity settings management view"""
    if request.user.user_type != 'celebrity':
        return HttpResponseForbidden()
    
    profile = request.user.celebrity_profile
    
    if request.method == 'POST':
        # Handle form submissions for settings
        # You'll need to create a CelebritySettingsForm for this
        pass
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'celebrities/settings.html', context)