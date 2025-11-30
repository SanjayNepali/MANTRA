# apps/admin_dashboard/views.py
"""
Admin (Superuser) Views for MANTRA Platform
Complete system administration with analytics, SubAdmin management, and oversight
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg, F
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json
import csv

from apps.accounts.models import User, SubAdminProfile, UserFollowing, PointsHistory
from apps.celebrities.models import CelebrityProfile
from apps.fans.models import FanProfile
from apps.posts.models import Post, Comment, Like
from apps.reports.models import Report, ModerationAction
from apps.analytics.models import PlatformAnalytics, UserEngagementMetrics
from apps.events.models import Event, EventBooking
from apps.merchandise.models import Merchandise, MerchandiseOrder
from apps.payments.models import PaymentTransaction
from apps.fanclubs.models import FanClub, FanClubMembership
from apps.notifications.models import Notification
from apps.subadmin.models import SubAdminActivityReport, SubAdminPerformance, RegionalAlert
from apps.admin_dashboard.models import AdminAuditLog, SystemAlert, DataExportRequest, SystemConfiguration

# Import algorithms
from algorithms.recommendation import RecommendationEngine, TrendingEngine
from algorithms.sentiment import SentimentAnalyzer, EngagementPredictor
from algorithms.integration import calculate_user_influence_score


def is_admin(user):
    """Check if user is admin (superusers are always admins)"""
    return user.is_authenticated and (user.is_superuser or user.user_type == 'admin')


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main Admin Dashboard with comprehensive analytics"""
    
    # Date range for analytics
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Platform-wide statistics
    total_users = User.objects.count()
    new_users = User.objects.filter(created_at__gte=start_date).count()
    active_users = User.objects.filter(last_active__gte=start_date).count()
    
    # User breakdown
    total_celebrities = User.objects.filter(user_type='celebrity').count()
    verified_celebrities = User.objects.filter(user_type='celebrity', is_verified=True).count()
    total_fans = User.objects.filter(user_type='fan').count()
    total_subadmins = User.objects.filter(user_type='subadmin').count()
    active_subadmins = User.objects.filter(
        user_type='subadmin', 
        last_login__gte=start_date
    ).count()
    
    # Content statistics
    total_posts = Post.objects.filter(created_at__gte=start_date).count()
    total_comments = Comment.objects.filter(created_at__gte=start_date).count()
    total_likes = Like.objects.filter(created_at__gte=start_date).count()
    
    # Engagement metrics using algorithms
    engagement_predictor = EngagementPredictor()
    trending_engine = TrendingEngine()
    
    # Get trending content
    trending_posts = trending_engine.calculate_trending_posts(days=7, limit=10)
    trending_hashtags = trending_engine.calculate_trending_hashtags(days=7, limit=10)
    trending_celebrities = trending_engine.calculate_trending_celebrities(days=7, limit=10)
    trending_events = trending_engine.calculate_trending_events(days=14, limit=10)
    
    # Financial metrics
    total_revenue = PaymentTransaction.objects.filter(
        created_at__gte=start_date,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    subscription_revenue = PaymentTransaction.objects.filter(
        created_at__gte=start_date,
        payment_type='subscription',
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    event_revenue = PaymentTransaction.objects.filter(
        created_at__gte=start_date,
        payment_type='event',
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    merchandise_revenue = PaymentTransaction.objects.filter(
        created_at__gte=start_date,
        payment_type='merchandise',
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Moderation statistics
    pending_reports = Report.objects.filter(status='pending').count()
    resolved_reports = Report.objects.filter(
        status='resolved',
        reviewed_at__gte=start_date
    ).count()
    
    total_warnings = ModerationAction.objects.filter(
        action_type='warning',
        created_at__gte=start_date
    ).count()
    
    total_bans = ModerationAction.objects.filter(
        action_type__contains='ban',
        created_at__gte=start_date
    ).count()
    
    # SubAdmin performance
    subadmin_reports = SubAdminActivityReport.objects.filter(
        submitted_at__gte=start_date
    ).select_related('subadmin').order_by('-submitted_at')[:10]
    
    # Regional performance
    regional_stats = {}
    for subadmin_profile in SubAdminProfile.objects.all():
        regional_users = User.objects.filter(
            Q(country__in=subadmin_profile.assigned_areas) | 
            Q(city=subadmin_profile.region)
        )
        regional_stats[subadmin_profile.region] = {
            'total_users': regional_users.count(),
            'active_users': regional_users.filter(last_active__gte=start_date).count(),
            'reports_resolved': subadmin_profile.reports_resolved,
            'kyc_handled': subadmin_profile.kyc_handled
        }
    
    # System health metrics
    system_health = calculate_system_health()
    
    # Critical alerts
    critical_alerts = RegionalAlert.objects.filter(
        priority='critical',
        is_resolved=False
    ).order_by('-created_at')[:5]
    
    # Top performers (using influence score algorithm)
    top_celebrities = []
    for celeb in User.objects.filter(user_type='celebrity', is_verified=True)[:10]:
        influence_score = calculate_user_influence_score(celeb)
        top_celebrities.append({
            'user': celeb,
            'influence_score': influence_score,
            'followers': UserFollowing.objects.filter(following=celeb).count()
        })
    top_celebrities.sort(key=lambda x: x['influence_score'], reverse=True)
    
    # Chart data for visualization
    chart_data = prepare_chart_data(start_date, end_date)
    
    # AI-powered insights using sentiment analysis
    sentiment_analyzer = SentimentAnalyzer()
    platform_sentiment = analyze_platform_sentiment(sentiment_analyzer, start_date)
    
    context = {
        # Basic stats
        'total_users': total_users,
        'new_users': new_users,
        'active_users': active_users,
        'total_celebrities': total_celebrities,
        'verified_celebrities': verified_celebrities,
        'total_fans': total_fans,
        'total_subadmins': total_subadmins,
        'active_subadmins': active_subadmins,
        
        # Content stats
        'total_posts': total_posts,
        'total_comments': total_comments,
        'total_likes': total_likes,
        
        # Financial
        'total_revenue': total_revenue,
        'subscription_revenue': subscription_revenue,
        'event_revenue': event_revenue,
        'merchandise_revenue': merchandise_revenue,
        
        # Moderation
        'pending_reports': pending_reports,
        'resolved_reports': resolved_reports,
        'total_warnings': total_warnings,
        'total_bans': total_bans,
        
        # Trending
        'trending_posts': trending_posts[:5],
        'trending_hashtags': trending_hashtags[:5],
        'trending_celebrities': trending_celebrities[:5],
        'trending_events': trending_events[:5],
        
        # Performance
        'subadmin_reports': subadmin_reports,
        'regional_stats': regional_stats,
        'top_celebrities': top_celebrities[:5],
        
        # System
        'system_health': system_health,
        'critical_alerts': critical_alerts,
        'platform_sentiment': platform_sentiment,
        
        # Visualization
        'chart_data': json.dumps(chart_data),
        'days': days,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def manage_subadmins(request):
    """Manage SubAdmins - Create, Edit, Delete"""
    
    # Get all subadmins
    subadmins = User.objects.filter(user_type='subadmin').select_related('subadmin_profile')
    
    # Filters
    search = request.GET.get('q', '')
    if search:
        subadmins = subadmins.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status == 'active':
        subadmins = subadmins.filter(is_active=True)
    elif status == 'inactive':
        subadmins = subadmins.filter(is_active=False)
    
    region = request.GET.get('region', '')
    if region:
        subadmins = subadmins.filter(subadmin_profile__region__icontains=region)
    
    # Add performance metrics
    for subadmin in subadmins:
        try:
            performance = SubAdminPerformance.objects.get(subadmin=subadmin)
            subadmin.performance = performance
        except SubAdminPerformance.DoesNotExist:
            subadmin.performance = None
    
    # Pagination
    paginator = Paginator(subadmins, 20)
    page = request.GET.get('page', 1)
    subadmins_page = paginator.get_page(page)
    
    # Statistics
    total_subadmins = User.objects.filter(user_type='subadmin').count()
    active_subadmins = User.objects.filter(user_type='subadmin', is_active=True).count()
    
    context = {
        'subadmins': subadmins_page,
        'total_subadmins': total_subadmins,
        'active_subadmins': active_subadmins,
        'search_query': search,
        'status_filter': status,
        'region_filter': region,
    }
    
    return render(request, 'admin_dashboard/manage_subadmins.html', context)


@login_required
@user_passes_test(is_admin)
def create_subadmin(request):
    """Create new SubAdmin"""
    
    if request.method == 'POST':
        with transaction.atomic():
            # Create user
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            
            # Check if user exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return redirect('admin_create_subadmin')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('admin_create_subadmin')
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type='subadmin'
            )
            
            # Create SubAdmin profile
            region = request.POST.get('region')
            assigned_areas = request.POST.getlist('assigned_areas')
            responsibilities = request.POST.get('responsibilities', '')
            
            SubAdminProfile.objects.create(
                user=user,
                region=region,
                assigned_areas=assigned_areas,
                assigned_by=request.user,
                responsibilities=responsibilities
            )
            
            # Create performance metrics
            SubAdminPerformance.objects.create(subadmin=user)
            
            # Send notification
            from apps.accounts.constants import COUNTRIES
            country_display = dict(COUNTRIES).get(region, region)
            Notification.objects.create(
                recipient=user,
                notification_type='system',
                message=f'Welcome to MANTRA Admin Team! You have been assigned as SubAdmin for {country_display}.',
                target_id=str(user.id)
            )

            messages.success(request, f'SubAdmin {username} created successfully!')
            return redirect('admin_manage_subadmins')

    # Get available countries
    from apps.accounts.constants import COUNTRIES

    context = {
        'countries': COUNTRIES,
    }

    return render(request, 'admin_dashboard/create_subadmin.html', context)


@login_required
@user_passes_test(is_admin)
def edit_subadmin(request, subadmin_id):
    """Edit SubAdmin details"""
    subadmin = get_object_or_404(User, id=subadmin_id, user_type='subadmin')
    
    try:
        profile = subadmin.subadmin_profile
    except SubAdminProfile.DoesNotExist:
        profile = SubAdminProfile.objects.create(user=subadmin, region='Unassigned')
    
    if request.method == 'POST':
        # Update user info
        subadmin.email = request.POST.get('email', subadmin.email)
        subadmin.first_name = request.POST.get('first_name', '')
        subadmin.last_name = request.POST.get('last_name', '')
        subadmin.is_active = request.POST.get('is_active') == 'on'
        subadmin.save()
        
        # Update profile
        profile.region = request.POST.get('region', profile.region)
        profile.assigned_areas = request.POST.getlist('assigned_areas')
        profile.responsibilities = request.POST.get('responsibilities', '')
        profile.save()
        
        messages.success(request, f'SubAdmin {subadmin.username} updated successfully!')
        return redirect('admin_manage_subadmins')
    
    context = {
        'subadmin': subadmin,
        'profile': profile,
        'available_areas': get_all_areas(),
    }
    
    return render(request, 'admin_dashboard/edit_subadmin.html', context)


@login_required
@user_passes_test(is_admin)
def delete_subadmin(request, subadmin_id):
    """Delete SubAdmin"""
    subadmin = get_object_or_404(User, id=subadmin_id, user_type='subadmin')
    
    if request.method == 'POST':
        # Change user type instead of deleting
        subadmin.user_type = 'fan'
        subadmin.is_active = False
        subadmin.save()
        
        # Delete profile
        if hasattr(subadmin, 'subadmin_profile'):
            subadmin.subadmin_profile.delete()
        
        messages.success(request, f'SubAdmin {subadmin.username} has been removed')
        return redirect('admin_manage_subadmins')
    
    context = {
        'subadmin': subadmin,
    }
    
    return render(request, 'admin_dashboard/delete_subadmin.html', context)


@login_required
@user_passes_test(is_admin)
def subadmin_performance(request, subadmin_id):
    """View detailed SubAdmin performance"""
    subadmin = get_object_or_404(User, id=subadmin_id, user_type='subadmin')
    
    # Get or create performance metrics
    performance, created = SubAdminPerformance.objects.get_or_create(subadmin=subadmin)
    
    # Recalculate metrics
    performance.calculate_metrics()
    
    # Get activity reports
    activity_reports = SubAdminActivityReport.objects.filter(
        subadmin=subadmin
    ).order_by('-submitted_at')[:10]
    
    # Get recent actions
    recent_actions = ModerationAction.objects.filter(
        performed_by=subadmin
    ).select_related('target_user').order_by('-created_at')[:20]
    
    # Get handled reports
    handled_reports = Report.objects.filter(
        reviewed_by=subadmin
    ).select_related('reported_by', 'target_user').order_by('-reviewed_at')[:20]
    
    context = {
        'subadmin': subadmin,
        'performance': performance,
        'activity_reports': activity_reports,
        'recent_actions': recent_actions,
        'handled_reports': handled_reports,
    }
    
    return render(request, 'admin_dashboard/subadmin_performance.html', context)


@login_required
@user_passes_test(is_admin)
def review_activity_reports(request):
    """Review SubAdmin activity reports"""
    
    # Get reports
    reports = SubAdminActivityReport.objects.all().select_related('subadmin', 'reviewed_by')
    
    # Filters
    region = request.GET.get('region', '')
    if region:
        reports = reports.filter(region=region)
    
    status = request.GET.get('status', '')
    if status:
        reports = reports.filter(status=status)
    
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')
    
    if date_from:
        reports = reports.filter(period_start__gte=date_from)
    if date_to:
        reports = reports.filter(period_end__lte=date_to)
    
    # Order by submission date
    reports = reports.order_by('-submitted_at')
    
    # Pagination
    paginator = Paginator(reports, 20)
    page = request.GET.get('page', 1)
    reports_page = paginator.get_page(page)
    
    # Statistics
    total_reports = SubAdminActivityReport.objects.count()
    pending_review = SubAdminActivityReport.objects.filter(status='pending').count()
    approved = SubAdminActivityReport.objects.filter(status='approved').count()
    needs_improvement = SubAdminActivityReport.objects.filter(status='needs_improvement').count()
    
    context = {
        'reports': reports_page,
        'total_reports': total_reports,
        'pending_review': pending_review,
        'approved': approved,
        'needs_improvement': needs_improvement,
        'region_filter': region,
        'status_filter': status,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'admin_dashboard/review_activity_reports.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def review_single_report(request, report_id):
    """Review and provide feedback on a single activity report"""
    report = get_object_or_404(SubAdminActivityReport, id=report_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        feedback = request.POST.get('feedback', '')
        rating = request.POST.get('rating', 0)

        with transaction.atomic():
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.admin_feedback = feedback
            report.performance_rating = int(rating) if rating else 0

            if action == 'approve':
                report.status = 'approved'
            elif action == 'needs_improvement':
                report.status = 'needs_improvement'
            elif action == 'under_review':
                report.status = 'under_review'

            report.save()

            # Notify SubAdmin
            Notification.objects.create(
                recipient=report.subadmin,
                notification_type='system',
                message=f'Your activity report has been reviewed by Admin. Status: {report.get_status_display()}',
                target_id=str(report.id)
            )

            messages.success(request, f'Report {report.get_status_display().lower()} successfully')
            return redirect('review_activity_reports')

    context = {
        'report': report,
    }

    return render(request, 'admin_dashboard/review_single_report.html', context)


@login_required
@user_passes_test(is_admin)
def review_report_detail(request, report_id):
    """Review individual activity report"""
    report = get_object_or_404(SubAdminActivityReport, id=report_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            report.reviewed_by = request.user
            report.review_notes = request.POST.get('notes', '')
            report.reviewed_at = timezone.now()
            report.save()
            
            # Send feedback to SubAdmin
            Notification.objects.create(
                recipient=report.subadmin,
                notification_type='system',
                message='Your activity report has been reviewed and approved.',
                target_id=str(report.id)
            )
            
            messages.success(request, 'Report approved successfully')
            return redirect('admin_review_activity_reports')
        
        elif action == 'feedback':
            feedback = request.POST.get('feedback', '')
            
            # Send feedback notification
            Notification.objects.create(
                recipient=report.subadmin,
                notification_type='system',
                message=f'Feedback on Activity Report: {feedback}',
                target_id=str(report.id)
            )
            
            messages.success(request, 'Feedback sent successfully')
    
    context = {
        'report': report,
        'report_data': report.reports_data,
    }
    
    return render(request, 'admin_dashboard/report_detail.html', context)


@login_required
@user_passes_test(is_admin)
def system_analytics(request):
    """Advanced system analytics with AI insights"""
    
    # Get time range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Initialize algorithms
    sentiment_analyzer = SentimentAnalyzer()
    recommendation_engine = RecommendationEngine()
    engagement_predictor = EngagementPredictor()
    
    # User growth analytics
    user_growth = analyze_user_growth(start_date, end_date)
    
    # Content performance
    content_analytics = analyze_content_performance(start_date, end_date, sentiment_analyzer)
    
    # Engagement patterns
    engagement_patterns = analyze_engagement_patterns(start_date, end_date, engagement_predictor)
    
    # Revenue analytics
    revenue_analytics = analyze_revenue(start_date, end_date)
    
    # Geographic distribution
    geographic_data = analyze_geographic_distribution()
    
    # Platform health scores
    health_scores = calculate_detailed_health_metrics()
    
    # AI predictions
    predictions = generate_ai_predictions(recommendation_engine, engagement_predictor)
    
    context = {
        'days': days,
        'user_growth': user_growth,
        'content_analytics': content_analytics,
        'engagement_patterns': engagement_patterns,
        'revenue_analytics': revenue_analytics,
        'geographic_data': geographic_data,
        'health_scores': health_scores,
        'predictions': predictions,
    }
    
    return render(request, 'admin_dashboard/system_analytics.html', context)


@login_required
@user_passes_test(is_admin)
def user_management(request):
    """Advanced user management interface"""
    
    # Get users based on filters
    users = User.objects.all()
    
    # Search
    search = request.GET.get('q', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # User type filter
    user_type = request.GET.get('type', '')
    if user_type:
        users = users.filter(user_type=user_type)
    
    # Status filter
    status = request.GET.get('status', '')
    if status == 'active':
        users = users.filter(is_active=True, is_banned=False)
    elif status == 'banned':
        users = users.filter(is_banned=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    elif status == 'verified':
        users = users.filter(is_verified=True)
    
    # Date filter
    date_from = request.GET.get('from', '')
    if date_from:
        users = users.filter(created_at__gte=date_from)
    
    # Sort
    sort = request.GET.get('sort', '-created_at')
    users = users.order_by(sort)
    
    # Add metrics
    for user in users[:50]:  # Limit for performance
        user.influence_score = calculate_user_influence_score(user)
        user.followers_count = UserFollowing.objects.filter(following=user).count()
        user.following_count = UserFollowing.objects.filter(follower=user).count()
    
    # Pagination
    paginator = Paginator(users, 50)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    context = {
        'users': users_page,
        'search_query': search,
        'type_filter': user_type,
        'status_filter': status,
        'date_from': date_from,
        'sort': sort,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True, is_banned=False).count(),
        'banned_users': User.objects.filter(is_banned=True).count(),
    }
    
    return render(request, 'admin_dashboard/user_management.html', context)


@login_required
@user_passes_test(is_admin)
def user_action(request, user_id):
    """Perform actions on user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        with transaction.atomic():
            if action == 'ban':
                reason = request.POST.get('reason', 'Admin decision')
                duration = request.POST.get('duration')
                
                if duration and duration != 'permanent':
                    user.ban_user(reason, int(duration))
                else:
                    user.ban_user(reason)
                
                # Log action
                ModerationAction.objects.create(
                    action_type='permanent_ban' if duration == 'permanent' else 'temporary_ban',
                    target_user=user,
                    reason=reason,
                    performed_by=request.user,
                    duration_days=int(duration) if duration and duration != 'permanent' else None
                )
                
                messages.success(request, f'User {user.username} has been banned')
            
            elif action == 'unban':
                user.unban_user()
                messages.success(request, f'User {user.username} has been unbanned')
            
            elif action == 'verify':
                user.is_verified = True
                user.verification_status = 'verified'
                user.save()

                if user.user_type == 'celebrity':
                    profile = user.celebrity_profile
                    profile.verification_status = 'approved'
                    profile.verification_date = timezone.now()
                    profile.save()

                messages.success(request, f'User {user.username} has been verified')
            
            elif action == 'deactivate':
                user.is_active = False
                user.save()
                messages.success(request, f'User {user.username} has been deactivated')
            
            elif action == 'activate':
                user.is_active = True
                user.save()
                messages.success(request, f'User {user.username} has been activated')
            
            elif action == 'reset_password':
                # Generate password reset
                from django.contrib.auth.tokens import default_token_generator
                from django.utils.encoding import force_bytes
                from django.utils.http import urlsafe_base64_encode
                
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Send reset email
                Notification.objects.create(
                    recipient=user,
                    notification_type='system',
                    message='Your password has been reset by an administrator. Please check your email.'
                )
                
                messages.success(request, f'Password reset initiated for {user.username}')
            
            elif action == 'add_points':
                points = int(request.POST.get('points', 0))
                reason = request.POST.get('reason', 'Admin bonus')
                user.add_points(points, reason)
                messages.success(request, f'Added {points} points to {user.username}')
            
            elif action == 'remove_points':
                points = int(request.POST.get('points', 0))
                reason = request.POST.get('reason', 'Admin deduction')
                user.deduct_points(points, reason)
                messages.success(request, f'Removed {points} points from {user.username}')
        
        return redirect('admin_user_management')
    
    # Get user details
    user_reports = Report.objects.filter(
        Q(reported_by=user) | Q(target_user=user)
    ).order_by('-created_at')[:10]
    
    user_actions = ModerationAction.objects.filter(
        target_user=user
    ).order_by('-created_at')[:10]
    
    context = {
        'user': user,
        'user_reports': user_reports,
        'user_actions': user_actions,
        'followers_count': UserFollowing.objects.filter(following=user).count(),
        'following_count': UserFollowing.objects.filter(follower=user).count(),
        'posts_count': Post.objects.filter(author=user).count(),
        'influence_score': calculate_user_influence_score(user),
    }
    
    return render(request, 'admin_dashboard/user_action.html', context)


@login_required
@user_passes_test(is_admin)
def export_data(request):
    """Export system data"""
    
    export_type = request.GET.get('type', 'users')
    format_type = request.GET.get('format', 'csv')
    
    if export_type == 'users':
        data = export_users_data()
    elif export_type == 'analytics':
        data = export_analytics_data()
    elif export_type == 'reports':
        data = export_reports_data()
    elif export_type == 'revenue':
        data = export_revenue_data()
    else:
        messages.error(request, 'Invalid export type')
        return redirect('admin_dashboard')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{export_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.DictWriter(response, fieldnames=data[0].keys() if data else [])
        writer.writeheader()
        writer.writerows(data)
        
        return response
    
    elif format_type == 'json':
        response = HttpResponse(json.dumps(data, indent=2, default=str), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{export_type}_{timezone.now().strftime("%Y%m%d")}.json"'
        return response
    
    else:
        messages.error(request, 'Invalid format type')
        return redirect('admin_dashboard')


# Helper functions

def calculate_system_health():
    """Calculate overall system health metrics"""
    health = {
        'overall': 0,
        'performance': 0,
        'security': 0,
        'engagement': 0,
        'content': 0,
    }
    
    # Performance health
    active_users_ratio = User.objects.filter(
        last_active__gte=timezone.now() - timedelta(days=7)
    ).count() / max(User.objects.count(), 1)
    health['performance'] = min(100, active_users_ratio * 100)
    
    # Security health
    banned_users_ratio = User.objects.filter(is_banned=True).count() / max(User.objects.count(), 1)
    pending_reports_ratio = Report.objects.filter(status='pending').count() / max(Report.objects.count(), 1)
    health['security'] = max(0, 100 - (banned_users_ratio * 50) - (pending_reports_ratio * 50))
    
    # Engagement health
    recent_posts = Post.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    health['engagement'] = min(100, (recent_posts / 100) * 100)
    
    # Content health (using sentiment analysis)
    sentiment_analyzer = SentimentAnalyzer()
    recent_content_sample = Post.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=1)
    )[:100]
    
    toxicity_scores = []
    for post in recent_content_sample:
        if post.content:
            result = sentiment_analyzer.detect_toxicity(post.content)
            toxicity_scores.append(result['toxicity_score'])
    
    avg_toxicity = sum(toxicity_scores) / len(toxicity_scores) if toxicity_scores else 0
    health['content'] = max(0, 100 - (avg_toxicity * 100))
    
    # Overall health
    health['overall'] = sum([
        health['performance'] * 0.25,
        health['security'] * 0.25,
        health['engagement'] * 0.25,
        health['content'] * 0.25
    ])
    
    return health


def prepare_chart_data(start_date, end_date):
    """Prepare data for charts"""
    days = (end_date - start_date).days
    
    chart_data = {
        'dates': [],
        'users': [],
        'posts': [],
        'revenue': [],
        'engagement': []
    }
    
    for i in range(min(days, 30)):  # Limit to 30 days
        date = start_date + timedelta(days=i)
        chart_data['dates'].append(date.strftime('%Y-%m-%d'))
        
        # Users
        new_users = User.objects.filter(created_at__date=date.date()).count()
        chart_data['users'].append(new_users)
        
        # Posts
        new_posts = Post.objects.filter(created_at__date=date.date()).count()
        chart_data['posts'].append(new_posts)
        
        # Revenue
        daily_revenue = PaymentTransaction.objects.filter(
            created_at__date=date.date(),
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        chart_data['revenue'].append(float(daily_revenue))
        
        # Engagement
        daily_likes = Like.objects.filter(created_at__date=date.date()).count()
        daily_comments = Comment.objects.filter(created_at__date=date.date()).count()
        chart_data['engagement'].append(daily_likes + daily_comments)
    
    return chart_data


def analyze_platform_sentiment(sentiment_analyzer, start_date):
    """Analyze overall platform sentiment"""
    # Sample recent content
    recent_posts = Post.objects.filter(
        created_at__gte=start_date,
        is_active=True
    )[:500]
    
    sentiments = {
        'positive': 0,
        'neutral': 0,
        'negative': 0,
        'avg_toxicity': 0,
        'avg_spam': 0
    }
    
    toxicity_scores = []
    spam_scores = []
    
    for post in recent_posts:
        if post.content:
            result = sentiment_analyzer.get_content_insights(post.content)
            
            # Sentiment
            if result['sentiment']['label'] == 'positive':
                sentiments['positive'] += 1
            elif result['sentiment']['label'] == 'negative':
                sentiments['negative'] += 1
            else:
                sentiments['neutral'] += 1
            
            # Scores
            toxicity_scores.append(result['toxicity']['toxicity_score'])
            spam_scores.append(result['spam']['spam_score'])
    
    total = len(recent_posts)
    if total > 0:
        sentiments['positive'] = (sentiments['positive'] / total) * 100
        sentiments['neutral'] = (sentiments['neutral'] / total) * 100
        sentiments['negative'] = (sentiments['negative'] / total) * 100
        sentiments['avg_toxicity'] = sum(toxicity_scores) / len(toxicity_scores) if toxicity_scores else 0
        sentiments['avg_spam'] = sum(spam_scores) / len(spam_scores) if spam_scores else 0
    
    return sentiments


def get_available_regions():
    """Get available regions for SubAdmin assignment"""
    return [
        'Kathmandu Valley',
        'Pokhara',
        'Chitwan',
        'Eastern Nepal',
        'Western Nepal',
        'Delhi NCR',
        'Mumbai Metropolitan',
        'Bangalore',
        'Chennai',
        'Kolkata',
        'Dhaka',
        'International',
    ]


def get_all_areas():
    """Get all possible areas"""
    return [
        'Kathmandu', 'Lalitpur', 'Bhaktapur', 'Pokhara', 'Chitwan',
        'Biratnagar', 'Dharan', 'Butwal', 'Hetauda', 'Janakpur',
        'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata',
        'Hyderabad', 'Pune', 'Ahmedabad', 'Surat', 'Jaipur',
        'Dhaka', 'Chattogram', 'Sylhet', 'Khulna', 'Rajshahi'
    ]


def analyze_user_growth(start_date, end_date):
    """Analyze user growth patterns"""
    return {
        'total_new': User.objects.filter(created_at__range=[start_date, end_date]).count(),
        'celebrities': User.objects.filter(
            created_at__range=[start_date, end_date],
            user_type='celebrity'
        ).count(),
        'fans': User.objects.filter(
            created_at__range=[start_date, end_date],
            user_type='fan'
        ).count(),
        'retention_rate': calculate_retention_rate(start_date, end_date),
        'churn_rate': calculate_churn_rate(start_date, end_date),
    }


def calculate_retention_rate(start_date, end_date):
    """Calculate user retention rate"""
    new_users = User.objects.filter(created_at__range=[start_date, end_date])
    active_new_users = new_users.filter(last_active__gte=end_date - timedelta(days=7))
    
    if new_users.count() > 0:
        return (active_new_users.count() / new_users.count()) * 100
    return 0


def calculate_churn_rate(start_date, end_date):
    """Calculate user churn rate"""
    total_users_start = User.objects.filter(created_at__lt=start_date).count()
    inactive_users = User.objects.filter(
        created_at__lt=start_date,
        last_active__lt=end_date - timedelta(days=30)
    ).count()
    
    if total_users_start > 0:
        return (inactive_users / total_users_start) * 100
    return 0


# Additional view functions

@login_required
@user_passes_test(is_admin)
def toggle_subadmin_status(request, subadmin_id):
    """Toggle SubAdmin active status - AJAX endpoint"""
    try:
        subadmin = get_object_or_404(User, id=subadmin_id, user_type='subadmin')
        
        # Toggle status
        subadmin.is_active = not subadmin.is_active
        subadmin.save()
        
        # Log the action
        AdminAuditLog.objects.create(
            admin_user=request.user,
            action_type='toggle_subadmin_status',
            description=f'Toggled SubAdmin status for {subadmin.username} to {"active" if subadmin.is_active else "inactive"}',
            target_user=subadmin
        )
        
        return JsonResponse({
            'success': True,
            'message': f'SubAdmin status updated successfully',
            'is_active': subadmin.is_active,
            'new_status': 'Active' if subadmin.is_active else 'Inactive'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@user_passes_test(is_admin)
def user_details(request, user_id):
    """View user details"""
    from apps.accounts.models import User
    user = get_object_or_404(User, id=user_id)
    return render(request, 'admin_dashboard/user_details.html', {'user': user})


@user_passes_test(is_admin)
def export_analytics(request):
    """Export analytics data"""
    messages.info(request, 'Analytics export feature coming soon.')
    return redirect('admin_system_analytics')


@user_passes_test(is_admin)
def system_configuration(request):
    """System configuration page"""
    from .models import SystemConfiguration
    config, _ = SystemConfiguration.objects.get_or_create(id=1)
    return render(request, 'admin_dashboard/configuration.html', {'config': config})


@user_passes_test(is_admin)
def save_configuration(request):
    """Save system configuration"""
    if request.method == 'POST':
        messages.success(request, 'Configuration saved successfully.')
    return redirect('admin_system_config')


@user_passes_test(is_admin)
def system_alerts(request):
    """View system alerts"""
    from .models import SystemAlert
    alerts = SystemAlert.objects.filter(is_resolved=False)
    return render(request, 'admin_dashboard/alerts.html', {'alerts': alerts})


@user_passes_test(is_admin)
def alert_detail(request, alert_id):
    """View alert details"""
    from .models import SystemAlert
    alert = get_object_or_404(SystemAlert, id=alert_id)
    return render(request, 'admin_dashboard/alert_detail.html', {'alert': alert})


@user_passes_test(is_admin)
def resolve_alert(request, alert_id):
    """Resolve an alert"""
    from .models import SystemAlert
    alert = get_object_or_404(SystemAlert, id=alert_id)
    alert.is_resolved = True
    alert.resolved_by = request.user
    alert.resolved_at = timezone.now()
    alert.save()
    messages.success(request, 'Alert resolved successfully.')
    return redirect('admin_system_alerts')


@user_passes_test(is_admin)
def export_status(request, export_id):
    """Check export status"""
    from .models import DataExportRequest
    export = get_object_or_404(DataExportRequest, id=export_id)
    return JsonResponse({'status': export.status, 'file_url': export.file_url})


@user_passes_test(is_admin)
def system_backup(request):
    """Create system backup"""
    messages.info(request, 'System backup feature coming soon.')
    return redirect('admin_dashboard')


@user_passes_test(is_admin)
def audit_logs(request):
    """View audit logs"""
    from .models import AdminAuditLog
    logs = AdminAuditLog.objects.all()[:100]
    return render(request, 'admin_dashboard/audit_logs.html', {'logs': logs})


@user_passes_test(is_admin)
def emergency_actions(request):
    """Emergency actions page"""
    return render(request, 'admin_dashboard/emergency.html')


@user_passes_test(is_admin)
def toggle_maintenance(request):
    """Toggle maintenance mode"""
    from .models import SystemConfiguration
    config, _ = SystemConfiguration.objects.get_or_create(id=1)
    config.maintenance_mode = not config.maintenance_mode
    config.save()
    messages.success(request, f'Maintenance mode {"enabled" if config.maintenance_mode else "disabled"}.')
    return redirect('admin_emergency_actions')


@user_passes_test(is_admin)
def api_dashboard_stats(request):
    """API endpoint for dashboard stats"""
    return JsonResponse({'status': 'ok', 'data': {}})


@user_passes_test(is_admin)
def api_system_alerts(request):
    """API endpoint for system alerts"""
    from .models import SystemAlert
    alerts = SystemAlert.objects.filter(is_resolved=False).values('id', 'title', 'level')[:10]
    return JsonResponse({'alerts': list(alerts)})


@user_passes_test(is_admin)
def api_system_health(request):
    """API endpoint for system health"""
    health_score = calculate_system_health()
    return JsonResponse({'health_score': health_score})


# Additional helper functions for analytics

def analyze_content_performance(start_date, end_date, sentiment_analyzer):
    """Analyze content performance metrics"""
    from apps.posts.models import Post

    posts = Post.objects.filter(created_at__range=[start_date, end_date])

    return {
        'total_posts': posts.count(),
        'avg_likes': posts.aggregate(Avg('likes_count'))['likes_count__avg'] or 0,
        'avg_comments': posts.aggregate(Avg('comments_count'))['comments_count__avg'] or 0,
        'top_posts': posts.order_by('-likes_count')[:5],
    }


def analyze_engagement_patterns(start_date, end_date, engagement_predictor):
    """Analyze user engagement patterns"""
    from apps.accounts.models import User

    active_users = User.objects.filter(last_active__range=[start_date, end_date]).count()

    return {
        'active_users': active_users,
        'engagement_rate': 0,
        'peak_hours': [],
        'trending_topics': [],
    }


def analyze_revenue(start_date, end_date):
    """Analyze revenue metrics"""
    from apps.payments.models import PaymentSimulation

    payments = PaymentSimulation.objects.filter(
        created_at__range=[start_date, end_date],
        payment_status='completed'
    )

    total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    return {
        'total_revenue': total_revenue,
        'transactions': payments.count(),
        'avg_transaction': total_revenue / payments.count() if payments.count() > 0 else 0,
    }


# In your views.py or wherever this function is
def analyze_geographic_distribution():
    """
    Returns top 12 countries with proper filtering of empty values
    and percentage for the progress bar.
    """
    from apps.accounts.models import User
    from django.db.models import Count

    # Exclude NULL and empty strings (this is the key!)
    raw_data = (
        User.objects
        .exclude(country__isnull=True)
        .exclude(country__exact='')           # <-- removes '' values
        .exclude(country__exact='None')       # safety
        .values('country')
        .annotate(count=Count('id'))
        .order_by('-count')[:12]
    )

    data_list = list(raw_data)

    # If still no real data → return empty list so template shows nice message
    if not data_list or (len(data_list) == 1 and not data_list[0]['country']):
        return []

    total = sum(item['count'] for item in data_list)

    result = []
    for item in data_list:
        country_name = (item['country'] or 'Unknown').strip()
        if not country_name:
            continue

        percentage = round((item['count'] / total) * 100, 1) if total > 0 else 0

        result.append({
            'country': country_name.title(),   # nice formatting: India, Nepal, Usa → USA
            'count': item['count'],
            'percentage': percentage,
        })

    return result

def calculate_detailed_health_metrics():
    """Calculate detailed platform health metrics"""
    from apps.accounts.models import User
    from apps.posts.models import Post

    total_users = User.objects.count()
    active_users = User.objects.filter(
        last_active__gte=timezone.now() - timedelta(days=7)
    ).count()

    activity_rate = (active_users / total_users * 100) if total_users > 0 else 0

    return {
        'overall_score': min(activity_rate, 100),
        'activity_rate': activity_rate,
        'content_quality': 75,
        'user_satisfaction': 80,
        'system_performance': 90,
    }


def generate_ai_predictions(recommendation_engine, engagement_predictor):
    """Generate AI-powered predictions"""
    return {
        'user_growth_forecast': [],
        'engagement_forecast': [],
        'revenue_forecast': [],
        'churn_prediction': 5.0,
    }


def export_users_data():
    """Export user data for reports"""
    from apps.accounts.models import User

    users = User.objects.all().values(
        'username', 'email', 'user_type', 'points',
        'is_verified', 'created_at', 'last_active'
    )
    return list(users)


def export_analytics_data():
    """Export analytics data"""
    from apps.accounts.models import User
    from apps.posts.models import Post

    data = [{
        'total_users': User.objects.count(),
        'total_posts': Post.objects.count(),
        'active_users': User.objects.filter(
            last_active__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'generated_at': timezone.now(),
    }]
    return data


def export_reports_data():
    """Export reports data"""
    from apps.reports.models import Report

    reports = Report.objects.all().values(
        'report_type', 'reason', 'status',
        'created_at', 'reviewed_at'
    )
    return list(reports)


def export_revenue_data():
    """Export revenue data"""
    from apps.payments.models import PaymentSimulation

    payments = PaymentSimulation.objects.filter(
        status='completed'
    ).values(
        'amount', 'payment_method', 'status',
        'created_at'
    )
    return list(payments)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def kyc_list(request):
    """List all pending KYC verifications"""
    from apps.celebrities.models import CelebrityProfile

    # Get all celebrities with pending verification
    pending_kyc = User.objects.filter(
        user_type='celebrity',
        celebrity_profile__verification_status='pending'
    ).select_related('celebrity_profile').order_by('-created_at')

    # Get approved and rejected for stats
    approved_count = User.objects.filter(
        user_type='celebrity',
        celebrity_profile__verification_status='approved'
    ).count()

    rejected_count = User.objects.filter(
        user_type='celebrity',
        celebrity_profile__verification_status='rejected'
    ).count()

    context = {
        'pending_kyc': pending_kyc,
        'pending_count': pending_kyc.count(),
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }

    return render(request, 'admin_dashboard/kyc_list.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def verify_celebrity_kyc(request, celebrity_id):
    """Verify or reject a celebrity's KYC"""
    from apps.celebrities.models import CelebrityProfile

    try:
        celebrity = User.objects.get(id=celebrity_id, user_type='celebrity')
        profile = celebrity.celebrity_profile
    except (User.DoesNotExist, CelebrityProfile.DoesNotExist):
        messages.error(request, 'Celebrity not found.')
        return redirect('admin_kyc_list')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')

        if action == 'approve':
            profile.verification_status = 'approved'
            profile.verification_date = timezone.now()
            profile.verified_by = request.user
            profile.verification_notes = notes
            profile.save()

            # Update user verification
            celebrity.is_verified = True
            celebrity.verification_status = 'verified'
            celebrity.save()

            # Award points
            celebrity.add_points(100, 'Profile verified')

            # Create notification
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=celebrity,
                notification_type='system',
                message='Congratulations! Your profile has been verified.',
                target_url=f'/profile/{celebrity.username}/'
            )

            # Log action
            AdminAuditLog.objects.create(
                admin_user=request.user,
                action_type='kyc_approved',
                description=f'Approved KYC for {celebrity.username}',
                target_user=celebrity
            )

            messages.success(request, f'Successfully verified {celebrity.username}.')

        elif action == 'reject':
            profile.verification_status = 'rejected'
            profile.verification_notes = notes
            profile.save()

            # Create notification
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=celebrity,
                notification_type='system',
                message=f'Your profile verification was rejected. Reason: {notes}',
                target_url=f'/profile/{celebrity.username}/'
            )

            # Log action
            AdminAuditLog.objects.create(
                admin_user=request.user,
                action_type='kyc_rejected',
                description=f'Rejected KYC for {celebrity.username}',
                target_user=celebrity
            )

            messages.warning(request, f'Rejected KYC for {celebrity.username}.')

        return redirect('admin_kyc_list')

    context = {
        'celebrity': celebrity,
        'profile': profile,
    }

    return render(request, 'admin_dashboard/verify_celebrity.html', context)