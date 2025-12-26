# apps/fanclubs/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, DetailView, ListView
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.urls import reverse

from apps.accounts.models import User
from .models import FanClub, FanClubMembership, FanClubPost, FanClubEvent
from .forms import FanClubCreateForm, FanClubPostForm, FanClubEventForm
from algorithms.integration import get_user_recommendations

class FanClubListView(TemplateView):
    template_name = 'fanclubs/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        base_qs = FanClub.objects.filter(is_active=True).select_related('celebrity')

        # 🏆 Top Fanclubs (by member count)
        context['top_fanclubs'] = base_qs.annotate(
            member_count=Count('memberships')
        ).order_by('-member_count')[:10]

        # 🔥 Trending Fanclubs (created this month)
        thirty_days_ago = now - timedelta(days=30)
        context['trending_fanclubs'] = base_qs.filter(
            created_at__gte=thirty_days_ago
        ).annotate(
            member_count=Count('memberships')
        ).order_by('-member_count')[:10]

        # ⭐ AI-Powered Recommended Fanclubs
        if self.request.user.is_authenticated and self.request.user.user_type == 'fan':
            try:
                # Get AI recommendations for celebrities
                recommendations = get_user_recommendations(
                    self.request.user,
                    recommendation_type='celebrities',
                    limit=10
                )

                # Get fanclubs of recommended celebrities
                if recommendations and 'celebrities' in recommendations:
                    recommended_celeb_ids = [celeb.user.id for celeb in recommendations['celebrities']]
                    context['recommended_fanclubs'] = base_qs.filter(
                        celebrity_id__in=recommended_celeb_ids
                    ).annotate(member_count=Count('memberships')).order_by('-member_count')[:10]
                else:
                    # Fallback to followed celebrities' fanclubs
                    followed_celebs = self.request.user.following.filter(
                        following__user_type='celebrity'
                    ).values_list('following_id', flat=True)
                    context['recommended_fanclubs'] = base_qs.filter(
                        celebrity_id__in=followed_celebs
                    ).annotate(member_count=Count('memberships')).order_by('-member_count')[:10]
            except Exception as e:
                print(f"Error getting fanclub recommendations: {e}")
                # Fallback to simple recommendations
                followed_celebs = self.request.user.following.filter(
                    following__user_type='celebrity'
                ).values_list('following_id', flat=True)
                context['recommended_fanclubs'] = base_qs.filter(
                    celebrity_id__in=followed_celebs
                ).annotate(member_count=Count('memberships')).order_by('-member_count')[:10]
        else:
            context['recommended_fanclubs'] = context['top_fanclubs']

        queryset = base_qs

        # 🎯 Filters
        celebrity_id = self.request.GET.get('celebrity')
        if celebrity_id:
            queryset = queryset.filter(celebrity_id=celebrity_id)

        club_type = self.request.GET.get('type')
        if club_type:
            queryset = queryset.filter(club_type=club_type)
        context['current_type'] = club_type

        # 🔍 Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(celebrity__username__icontains=search)
            )
        context['search_query'] = search

        # ↕️ Sorting
        sort = self.request.GET.get('sort', '-created_at')
        if sort == 'memberships':
            queryset = queryset.annotate(member_count=Count('memberships')).order_by('-member_count')
        elif sort == 'recent':
            queryset = queryset.order_by('-created_at')
        elif sort == 'name':
            queryset = queryset.order_by('name')
        else:
            queryset = queryset.order_by('-created_at')
        context['current_sort'] = sort

        # 📄 Pagination
        paginator = Paginator(queryset, 12)
        page_number = self.request.GET.get('page')
        context['fanclubs'] = paginator.get_page(page_number)

        # 👥 User membership context
        if self.request.user.is_authenticated:
            context['user_fanclubs'] = FanClubMembership.objects.filter(
                user=self.request.user,
                status='active'
            ).values_list('fanclub_id', flat=True)

        return context


class FanClubDetailView(DetailView):
    model = FanClub
    template_name = 'fanclubs/detail.html'
    context_object_name = 'fanclub'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fanclub = self.object
        is_member = False
        membership = None

        if self.request.user.is_authenticated:
            try:
                membership = FanClubMembership.objects.get(
                    user=self.request.user,
                    fanclub=fanclub
                )
                is_member = membership.status == 'active'
            except FanClubMembership.DoesNotExist:
                pass

        context['is_member'] = is_member
        context['membership'] = membership
        context['is_owner'] = fanclub.celebrity == self.request.user

        if is_member or not fanclub.is_private or context['is_owner']:
            context['posts'] = FanClubPost.objects.filter(
                fanclub=fanclub,
                is_active=True
            ).select_related('author')[:10]

        context['upcoming_events'] = FanClubEvent.objects.filter(
            fanclub=fanclub,
            event_date__gte=timezone.now(),
            is_active=True,
            is_cancelled=False
        )[:5]

        context['moderators'] = FanClubMembership.objects.filter(
            fanclub=fanclub,
            role='moderator',
            status='active'
        ).count()

        return context

@login_required
def create_fanclub(request):
    """Create a new fanclub (celebrities only)"""
    if request.user.user_type != 'celebrity':
        messages.error(request, 'Only celebrities can create fanclubs')
        return redirect('fanclub_list')
    
    # Check if user already has an official fanclub
    official_fanclub = FanClub.objects.filter(
        celebrity=request.user,
        is_official=True
    ).first()
    
    if official_fanclub:
        messages.info(request, 'You already have an official fan club. You can edit it below.')
        return redirect('edit_fanclub', slug=official_fanclub.slug)
    
    # For non-official fanclubs, check limits
    existing_count = FanClub.objects.filter(
        celebrity=request.user,
        is_official=False
    ).count()
    
    if existing_count >= 3:  # Limit to 3 additional fanclubs
        messages.error(request, 'You can only create up to 3 additional fanclubs besides your official one')
        return redirect('fanclub_list')
    
    if request.method == 'POST':
        form = FanClubCreateForm(request.POST, request.FILES)
        
        if form.is_valid():
            fanclub = form.save(commit=False)
            fanclub.celebrity = request.user
            fanclub.is_official = False  # Additional fanclubs are not official
            fanclub.save()
            
            # Auto-join creator as admin
            FanClubMembership.objects.create(
                user=request.user,
                fanclub=fanclub,
                role='admin',
                status='active'
            )
            
            # Award points
            request.user.add_points(20, f"Created fanclub: {fanclub.name}")
            
            messages.success(request, f'Fanclub "{fanclub.name}" created successfully!')
            return redirect('fanclub_detail', slug=fanclub.slug)
    else:
        form = FanClubCreateForm()
    
    context = {
        'form': form,
        'existing_count': existing_count
    }
    
    return render(request, 'fanclubs/create.html', context)

@login_required
def edit_fanclub(request, slug):
    """Edit fanclub details (celebrity only)"""
    fanclub = get_object_or_404(FanClub, slug=slug)

    # Check if user is the celebrity owner
    if request.user != fanclub.celebrity:
        messages.error(request, 'Only the fanclub owner can edit it')
        return redirect('fanclub_detail', slug=slug)

    if request.method == 'POST':
        form = FanClubCreateForm(request.POST, request.FILES, instance=fanclub)

        if form.is_valid():
            updated_fanclub = form.save()

            # Update group chat if name or icon changed
            if updated_fanclub.group_chat:
                updated_fanclub.group_chat.title = updated_fanclub.name
                updated_fanclub.group_chat.group_image = updated_fanclub.icon
                updated_fanclub.group_chat.save(update_fields=['title', 'group_image'])

            messages.success(request, f'Fanclub "{updated_fanclub.name}" updated successfully!')
            return redirect('fanclub_detail', slug=updated_fanclub.slug)
    else:
        form = FanClubCreateForm(instance=fanclub)

    return render(request, 'fanclubs/edit.html', {
        'form': form,
        'fanclub': fanclub
    })


@login_required
def join_fanclub(request, slug):
    """Join a fanclub"""
    fanclub = get_object_or_404(FanClub, slug=slug, is_active=True)
    
    # Check if already member
    existing = FanClubMembership.objects.filter(
        user=request.user,
        fanclub=fanclub
    ).first()
    
    if existing:
        if existing.status == 'active':
            messages.info(request, 'You are already a member')
        elif existing.status == 'banned':
            messages.error(request, 'You are banned from this fanclub')
        elif existing.status == 'pending':
            messages.info(request, 'Your membership is pending approval')
        return redirect('fanclub_detail', slug=fanclub.slug)
    
    # Check if exclusive fanclub requires subscription
    if fanclub.club_type == 'exclusive':
        from apps.celebrities.models import Subscription
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user,
            celebrity__user=fanclub.celebrity,
            status='active'
        ).exists()
        
        if not is_subscribed:
            messages.error(request, 'You need an active subscription to join this exclusive fanclub')
            return redirect('fanclub_detail', slug=fanclub.slug)
    
    # Create membership
    status = 'pending' if fanclub.requires_approval else 'active'
    membership = FanClubMembership.objects.create(
        user=request.user,
        fanclub=fanclub,
        status=status
    )
    
    if status == 'active':
        fanclub.members_count += 1
        fanclub.save(update_fields=['members_count'])
        
        # Award points
        request.user.add_points(5, f"Joined fanclub: {fanclub.name}")
        
        # Log activity
        from apps.fans.models import FanActivity
        if request.user.user_type == 'fan':
            FanActivity.objects.create(
                fan=request.user,
                activity_type='join_fanclub',
                description=f'Joined {fanclub.name}',
                target_user=fanclub.celebrity,
                target_id=str(fanclub.id)
            )
        
        messages.success(request, f'Successfully joined {fanclub.name}!')
    else:
        messages.info(request, 'Your membership request has been sent for approval')
    
    return redirect('fanclub_detail', slug=fanclub.slug)


@login_required
def leave_fanclub(request, slug):
    """Leave a fanclub"""
    fanclub = get_object_or_404(FanClub, slug=slug)
    
    try:
        membership = FanClubMembership.objects.get(
            user=request.user,
            fanclub=fanclub
        )
        
        # Can't leave if you're the celebrity owner
        if fanclub.celebrity == request.user:
            messages.error(request, "You can't leave your own fanclub")
            return redirect('fanclub_detail', slug=fanclub.slug)
        
        membership.delete()
        fanclub.members_count = max(0, fanclub.members_count - 1)
        fanclub.save(update_fields=['members_count'])
        
        messages.success(request, f'You have left {fanclub.name}')
        
    except FanClubMembership.DoesNotExist:
        messages.error(request, 'You are not a member of this fanclub')
    
    return redirect('fanclub_detail', slug=fanclub.slug)


@login_required
def post_in_fanclub(request, slug):
    """Create post in fanclub"""
    fanclub = get_object_or_404(FanClub, slug=slug)
    
    # Check membership
    try:
        membership = FanClubMembership.objects.get(
            user=request.user,
            fanclub=fanclub,
            status='active'
        )
    except FanClubMembership.DoesNotExist:
        messages.error(request, 'You must be a member to post')
        return redirect('fanclub_detail', slug=fanclub.slug)
    
    if request.method == 'POST':
        form = FanClubPostForm(request.POST, request.FILES)
        
        if form.is_valid():
            post = form.save(commit=False)
            post.fanclub = fanclub
            post.author = request.user
            
            # Only admins/mods can make announcements
            if form.cleaned_data.get('is_announcement'):
                if membership.role not in ['admin', 'moderator']:
                    post.is_announcement = False
            
            post.save()
            
            # Update fanclub post count
            fanclub.posts_count += 1
            fanclub.save(update_fields=['posts_count'])
            
            # Update membership contribution
            membership.contribution_points += 5
            membership.last_active = timezone.now()
            membership.save()
            
            messages.success(request, 'Post created successfully!')
            return redirect('fanclub_detail', slug=fanclub.slug)
    else:
        form = FanClubPostForm()
    
    return render(request, 'fanclubs/post_create.html', {
        'form': form,
        'fanclub': fanclub
    })