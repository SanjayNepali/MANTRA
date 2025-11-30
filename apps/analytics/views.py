# apps/analytics/views.py - Enhanced admin dashboard

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
import json

from apps.accounts.models import User
from apps.posts.models import Post, PostReport
from apps.events.models import Event
from apps.merchandise.models import Merchandise
from apps.payments.models import PaymentSimulation
from apps.celebrities.models import CelebrityProfile


@staff_member_required
def admin_dashboard(request):
    """Enhanced admin dashboard with comprehensive analytics"""
    
    # Date range filter
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # User Statistics
    user_stats = {
        'total_users': User.objects.filter(is_active=True).count(),
        'new_users_today': User.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
        'new_users_period': User.objects.filter(
            created_at__gte=start_date
        ).count(),
        'verified_celebrities': User.objects.filter(
            user_type='celebrity',
            is_verified=True
        ).count(),
        'active_fans': User.objects.filter(
            user_type='fan',
            last_seen__gte=start_date
        ).count(),
    }
    
    # Content Statistics
    content_stats = {
        'total_posts': Post.objects.filter(is_active=True).count(),
        'posts_period': Post.objects.filter(created_at__gte=start_date).count(),
        'active_events': Event.objects.filter(
            status='published',
            start_datetime__gte=timezone.now()
        ).count(),
        'merchandise_items': Merchandise.objects.filter(status='available').count(),
    }
    
    # Revenue Statistics
    revenue_stats = PaymentSimulation.objects.filter(
        payment_status='success',
        completed_at__gte=start_date
    ).aggregate(
        total_revenue=Sum('amount'),
        total_transactions=Count('id'),
        average_transaction=Avg('amount')
    )
    
    # Platform Health Metrics
    health_metrics = {
        'pending_reports': PostReport.objects.filter(is_reviewed=False).count(),
        'resolved_reports': PostReport.objects.filter(
            is_reviewed=True,
            reviewed_at__gte=start_date
        ).count(),
        'banned_users': User.objects.filter(is_banned=True).count(),
        'system_uptime': '99.9%',  # Placeholder
    }
    
    # Top Performers
    top_celebrities = User.objects.filter(
        user_type='celebrity'
    ).annotate(
        follower_count=Count('followers')
    ).order_by('-follower_count')[:5]
    
    top_fans = User.objects.filter(
        user_type='fan'
    ).order_by('-points')[:5]
    
    # Activity Timeline (for charts)
    timeline_data = []
    for i in range(days):
        date = timezone.now().date() - timedelta(days=i)
        timeline_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'users': User.objects.filter(created_at__date=date).count(),
            'posts': Post.objects.filter(created_at__date=date).count(),
            'revenue': float(PaymentSimulation.objects.filter(
                completed_at__date=date,
                payment_status='success'
            ).aggregate(Sum('amount'))['amount__sum'] or 0)
        })
    timeline_data.reverse()
    
    # Role-based actions
    user_role = 'admin' if request.user.is_superuser else 'subadmin'
    
    context = {
        'user_stats': user_stats,
        'content_stats': content_stats,
        'revenue_stats': revenue_stats,
        'health_metrics': health_metrics,
        'top_celebrities': top_celebrities,
        'top_fans': top_fans,
        'timeline_data': json.dumps(timeline_data),
        'days_filter': days,
        'user_role': user_role,
    }
    
    return render(request, 'analytics/admin_dashboard.html', context)


@staff_member_required
def subadmin_dashboard(request):
    """SubAdmin dashboard with limited access"""
    
    # SubAdmins have limited view
    if not request.user.user_type == 'subadmin':
        return redirect('dashboard')
    
    # Get assigned areas (e.g., content moderation, user management)
    assigned_areas = request.user.subadmin_profile.assigned_areas  # Assuming profile exists
    
    context = {
        'assigned_areas': assigned_areas,
        'pending_reports': 0,
        'pending_verifications': 0,
    }
    
    # Content Moderation
    if 'content_moderation' in assigned_areas:
        context['pending_reports'] = PostReport.objects.filter(
            is_reviewed=False
        ).count()
    
    # User Verification
    if 'user_verification' in assigned_areas:
        context['pending_verifications'] = CelebrityProfile.objects.filter(
            verification_status='pending'
        ).count()
    
    return render(request, 'analytics/subadmin_dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def manage_subadmins(request):
    """Manage sub-admins - list all sub-admins"""
    from apps.accounts.models import SubAdminProfile

    subadmins = User.objects.filter(
        user_type='sub_admin'
    ).select_related('subadmin_profile').order_by('-date_joined')

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        subadmins = subadmins.filter(is_active=True)
    elif status_filter == 'inactive':
        subadmins = subadmins.filter(is_active=False)

    # Filter by region
    region_filter = request.GET.get('region', '')
    if region_filter:
        subadmins = subadmins.filter(subadmin_profile__assigned_region=region_filter)

    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        subadmins = subadmins.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(subadmins, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'subadmins': page_obj,
        'total_subadmins': subadmins.count(),
        'active_subadmins': User.objects.filter(user_type='sub_admin', is_active=True).count(),
        'status_filter': status_filter,
        'region_filter': region_filter,
        'search_query': search_query,
    }

    return render(request, 'analytics/manage_subadmins.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def create_subadmin(request):
    """Create a new sub-admin"""
    from apps.accounts.models import SubAdminProfile
    from apps.accounts.forms import SubAdminCreationForm

    if request.method == 'POST':
        form = SubAdminCreationForm(request.POST)
        if form.is_valid():
            # Create user
            user = form.save(commit=False)
            user.user_type = 'sub_admin'
            user.is_staff = True
            user.set_password(form.cleaned_data['password1'])
            user.save()

            # Create sub-admin profile
            SubAdminProfile.objects.create(
                user=user,
                assigned_region=form.cleaned_data.get('assigned_region', ''),
                assigned_areas=form.cleaned_data.get('assigned_areas', [])
            )

            messages.success(request, f'Sub-admin {user.username} created successfully!')
            return redirect('manage_subadmins')
    else:
        form = SubAdminCreationForm()

    context = {
        'form': form,
    }

    return render(request, 'analytics/create_subadmin.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def edit_subadmin(request, user_id):
    """Edit an existing sub-admin"""
    from apps.accounts.models import SubAdminProfile

    subadmin = get_object_or_404(User, id=user_id, user_type='sub_admin')

    try:
        profile = subadmin.subadmin_profile
    except SubAdminProfile.DoesNotExist:
        profile = SubAdminProfile.objects.create(user=subadmin)

    if request.method == 'POST':
        # Update user fields
        subadmin.first_name = request.POST.get('first_name', '')
        subadmin.last_name = request.POST.get('last_name', '')
        subadmin.email = request.POST.get('email', '')
        subadmin.is_active = request.POST.get('is_active') == 'on'
        subadmin.save()

        # Update profile fields
        profile.assigned_region = request.POST.get('assigned_region', '')
        assigned_areas = request.POST.getlist('assigned_areas')
        profile.assigned_areas = assigned_areas
        profile.save()

        messages.success(request, f'Sub-admin {subadmin.username} updated successfully!')
        return redirect('manage_subadmins')

    context = {
        'subadmin': subadmin,
        'profile': profile,
        'available_areas': ['content_moderation', 'user_verification', 'analytics', 'support'],
    }

    return render(request, 'analytics/edit_subadmin.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def delete_subadmin(request, user_id):
    """Delete a sub-admin"""
    subadmin = get_object_or_404(User, id=user_id, user_type='sub_admin')

    if request.method == 'POST':
        username = subadmin.username
        subadmin.delete()
        messages.success(request, f'Sub-admin {username} deleted successfully!')
        return redirect('manage_subadmins')

    context = {
        'subadmin': subadmin,
    }

    return render(request, 'analytics/delete_subadmin.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def toggle_subadmin_status(request, user_id):
    """Toggle sub-admin active status"""
    if request.method == 'POST':
        subadmin = get_object_or_404(User, id=user_id, user_type='sub_admin')
        subadmin.is_active = not subadmin.is_active
        subadmin.save()

        status = 'activated' if subadmin.is_active else 'deactivated'
        messages.success(request, f'Sub-admin {subadmin.username} {status} successfully!')

        return JsonResponse({
            'status': 'success',
            'is_active': subadmin.is_active,
            'message': f'Sub-admin {status}'
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'sub_admin'])
def generate_report(request):
    """Generate various reports for admins and sub-admins"""
    from django.core.paginator import Paginator
    from apps.accounts.models import SubAdminProfile

    # Check if user is sub-admin and get their permissions
    is_subadmin = request.user.user_type == 'sub_admin'
    assigned_areas = []
    assigned_region = ''

    if is_subadmin:
        try:
            profile = request.user.subadmin_profile
            assigned_areas = profile.assigned_areas or []
            assigned_region = profile.assigned_region or ''
        except SubAdminProfile.DoesNotExist:
            assigned_areas = []

    # Get report type
    report_type = request.GET.get('type', 'overview')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    context = {
        'report_type': report_type,
        'date_from': date_from,
        'date_to': date_to,
        'is_subadmin': is_subadmin,
        'assigned_areas': assigned_areas,
    }

    # Apply date filters
    from datetime import datetime
    filters = {}
    if date_from:
        try:
            filters['created_at__gte'] = datetime.strptime(date_from, '%Y-%m-%d')
        except ValueError:
            pass
    if date_to:
        try:
            filters['created_at__lte'] = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            pass

    # Generate different types of reports
    if report_type == 'users':
        if is_subadmin and 'user_verification' not in assigned_areas:
            messages.error(request, 'You do not have permission to generate user reports.')
            return redirect('subadmin_dashboard')

        users = User.objects.filter(**filters).annotate(
            posts_count=Count('posts'),
            followers_count=Count('followers')
        ).order_by('-date_joined')

        # Regional filtering for sub-admins
        if is_subadmin and assigned_region:
            # Filter by region if applicable
            pass

        context['users'] = users[:100]  # Limit to 100 for performance
        context['total_users'] = users.count()
        context['user_types'] = User.objects.values('user_type').annotate(count=Count('id'))

    elif report_type == 'content':
        if is_subadmin and 'content_moderation' not in assigned_areas:
            messages.error(request, 'You do not have permission to generate content reports.')
            return redirect('subadmin_dashboard')

        posts = Post.objects.filter(**filters).select_related('author').annotate(
            total_engagement=F('likes_count') + F('comments_count') + F('shares_count')
        ).order_by('-total_engagement')

        context['posts'] = posts[:100]
        context['total_posts'] = posts.count()
        context['avg_engagement'] = posts.aggregate(
            avg_likes=Avg('likes_count'),
            avg_comments=Avg('comments_count'),
            avg_shares=Avg('shares_count')
        )

    elif report_type == 'moderation':
        if is_subadmin and 'content_moderation' not in assigned_areas:
            messages.error(request, 'You do not have permission to generate moderation reports.')
            return redirect('subadmin_dashboard')

        reports = PostReport.objects.filter(**filters).select_related('post', 'reported_by').order_by('-created_at')

        context['reports'] = reports[:100]
        context['total_reports'] = reports.count()
        context['pending_reports'] = reports.filter(is_reviewed=False).count()
        context['report_reasons'] = reports.values('reason').annotate(count=Count('id'))

    elif report_type == 'engagement':
        posts_engagement = Post.objects.filter(**filters).aggregate(
            total_likes=Sum('likes_count'),
            total_comments=Sum('comments_count'),
            total_shares=Sum('shares_count'),
            total_views=Sum('views_count'),
            avg_likes=Avg('likes_count'),
            avg_comments=Avg('comments_count')
        )

        context['engagement_stats'] = posts_engagement

        # Top performers
        context['top_posts'] = Post.objects.filter(**filters).order_by('-likes_count')[:10]
        context['top_celebrities'] = User.objects.filter(
            user_type='celebrity',
            posts__created_at__gte=filters.get('created_at__gte', timezone.now() - timedelta(days=30))
        ).annotate(
            total_engagement=Sum('posts__likes_count') + Sum('posts__comments_count')
        ).order_by('-total_engagement')[:10]

    elif report_type == 'revenue':
        if is_subadmin:
            messages.error(request, 'Only admins can generate revenue reports.')
            return redirect('subadmin_dashboard')

        from apps.payments.models import PaymentSimulation

        payments = PaymentSimulation.objects.filter(**filters)

        context['total_revenue'] = payments.aggregate(total=Sum('amount'))['total'] or 0
        context['total_transactions'] = payments.count()
        context['successful_transactions'] = payments.filter(status='completed').count()
        context['payment_methods'] = payments.values('payment_method').annotate(count=Count('id'))

    return render(request, 'analytics/generate_report.html', context)


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'sub_admin'])
def export_report(request):
    """Export report as CSV or PDF"""
    import csv
    from django.http import HttpResponse

    report_type = request.GET.get('type', 'overview')
    export_format = request.GET.get('format', 'csv')

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d")}.csv"'

        writer = csv.writer(response)

        if report_type == 'users':
            writer.writerow(['Username', 'Email', 'User Type', 'Date Joined', 'Posts Count', 'Followers Count'])
            users = User.objects.annotate(
                posts_count=Count('posts'),
                followers_count=Count('followers')
            ).order_by('-date_joined')[:1000]

            for user in users:
                writer.writerow([
                    user.username,
                    user.email,
                    user.user_type,
                    user.date_joined.strftime('%Y-%m-%d'),
                    user.posts_count,
                    user.followers_count
                ])

        elif report_type == 'content':
            writer.writerow(['Post ID', 'Author', 'Content Preview', 'Likes', 'Comments', 'Shares', 'Created At'])
            posts = Post.objects.select_related('author').order_by('-created_at')[:1000]

            for post in posts:
                writer.writerow([
                    str(post.id),
                    post.author.username,
                    post.content[:100],
                    post.likes_count,
                    post.comments_count,
                    post.shares_count,
                    post.created_at.strftime('%Y-%m-%d %H:%M')
                ])

        elif report_type == 'moderation':
            writer.writerow(['Report ID', 'Post ID', 'Reported By', 'Reason', 'Status', 'Created At'])
            reports = PostReport.objects.select_related('post', 'reported_by').order_by('-created_at')[:1000]

            for report in reports:
                writer.writerow([
                    report.id,
                    str(report.post.id),
                    report.reported_by.username,
                    report.reason,
                    'Reviewed' if report.is_reviewed else 'Pending',
                    report.created_at.strftime('%Y-%m-%d %H:%M')
                ])

        return response

    else:
        messages.error(request, 'Invalid export format')
        return redirect('generate_report')
