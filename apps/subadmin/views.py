# apps/subadmin/views.py
"""
SubAdmin Views for MANTRA Platform
Handles regional management, KYC verification, report processing, and moderation
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Q, Count, Avg
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime, timedelta
from collections import Counter

from apps.accounts.models import User, SubAdminProfile, PointsHistory
from apps.celebrities.models import CelebrityProfile, KYCDocument
from apps.reports.models import Report, ModerationAction
from apps.posts.models import Post, Comment
from apps.notifications.models import Notification
from apps.analytics.models import PlatformAnalytics
from apps.subadmin.models import SubAdminActivityReport, ContentModerationAlert

# Import enhanced sentiment analysis from algorithms
from algorithms.sentiment import SentimentAnalyzer, EngagementPredictor


def is_subadmin(user):
    """Check if user is a subadmin"""
    return user.is_authenticated and user.user_type == 'subadmin'


def is_admin_or_subadmin(user):
    """Check if user is admin or subadmin"""
    return user.is_authenticated and user.user_type in ['admin', 'subadmin']


class ContentModerationView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """AI-powered content moderation dashboard with enhanced sentiment analysis"""
    model = ContentModerationAlert
    template_name = 'subadmin/content_moderation.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def test_func(self):
        return is_subadmin(self.request.user)
    
    def get_queryset(self):
        subadmin_profile = self.request.user.subadmin_profile
        assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
        if subadmin_profile.region:
            assigned_countries.append(subadmin_profile.region)
        
        # Filter by status
        status_filter = self.request.GET.get('status', 'pending')
        severity_filter = self.request.GET.get('severity', 'all')
        
        queryset = ContentModerationAlert.objects.filter(
            Q(assigned_to=self.request.user) |
            Q(content_author__country__in=assigned_countries, assigned_to__isnull=True)
        ).select_related('content_author', 'assigned_to')
        
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        if severity_filter != 'all':
            queryset = queryset.filter(severity=severity_filter)
        
        return queryset.order_by('-severity', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add enhanced sentiment analysis results
        context['flagged_content'] = self.get_flagged_content_with_sentiment()
        context['moderation_queue'] = self.get_moderation_queue()
        context['ai_recommendations'] = self.get_ai_moderation_suggestions()
        context['moderation_stats'] = self.get_moderation_statistics()
        context['sentiment_insights'] = self.get_sentiment_insights()
        return context
    
    def get_flagged_content_with_sentiment(self):
        """Get flagged content with enhanced sentiment analysis"""
        subadmin_profile = self.request.user.subadmin_profile
        assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
        if subadmin_profile.region:
            assigned_countries.append(subadmin_profile.region)
        
        # Get recent flagged content
        alerts = ContentModerationAlert.objects.filter(
            Q(assigned_to=self.request.user) |
            Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
            status='pending'
        ).select_related('content_author')[:10]
        
        # Add enhanced sentiment analysis
        sentiment_analyzer = SentimentAnalyzer()
        engagement_predictor = EngagementPredictor()
        
        for alert in alerts:
            if alert.content_preview:
                # Get comprehensive content insights
                sentiment_result = sentiment_analyzer.get_content_insights(alert.content_preview)
                alert.sentiment_score = sentiment_result['sentiment']['score']
                alert.sentiment_label = sentiment_result['sentiment']['label']
                alert.sentiment_confidence = sentiment_result['sentiment']['confidence']
                alert.toxicity_breakdown = sentiment_result['toxicity']
                alert.emotion_analysis = sentiment_result['emotions']
                alert.spam_analysis = sentiment_result['spam']
                
                # Predict engagement for context
                if alert.content_author:
                    author_stats = {
                        'followers_count': alert.content_author.total_followers or 0,
                        'avg_likes': getattr(alert.content_author, 'avg_likes', 0)
                    }
                    engagement_prediction = engagement_predictor.predict_post_engagement(
                        alert.content_preview, author_stats
                    )
                    alert.engagement_prediction = engagement_prediction
                    alert.viral_potential = engagement_prediction['viral_potential']
        
        return alerts
    
    def get_moderation_queue(self):
        """Get moderation queue with enhanced priority scoring"""
        subadmin_profile = self.request.user.subadmin_profile
        assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
        if subadmin_profile.region:
            assigned_countries.append(subadmin_profile.region)
        
        # Get pending alerts and calculate enhanced priority score
        alerts = ContentModerationAlert.objects.filter(
            Q(assigned_to=self.request.user) |
            Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
            status='pending'
        ).select_related('content_author')
        
        sentiment_analyzer = SentimentAnalyzer()
        
        # Calculate enhanced priority score based on multiple factors
        for alert in alerts:
            alert.priority_score = self.calculate_enhanced_priority_score(alert, sentiment_analyzer)
        
        return sorted(alerts, key=lambda x: x.priority_score, reverse=True)[:15]
    
    def get_ai_moderation_suggestions(self):
        """Get AI-powered moderation suggestions with sentiment context"""
        subadmin_profile = self.request.user.subadmin_profile
        assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
        if subadmin_profile.region:
            assigned_countries.append(subadmin_profile.region)
        
        # Get high-priority alerts for AI suggestions
        high_priority_alerts = ContentModerationAlert.objects.filter(
            Q(assigned_to=self.request.user) |
            Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
            status='pending',
            severity__in=['high', 'critical']
        )[:5]
        
        sentiment_analyzer = SentimentAnalyzer()
        suggestions = []
        
        for alert in high_priority_alerts:
            if alert.content_preview:
                # Get comprehensive analysis
                content_insights = sentiment_analyzer.get_content_insights(alert.content_preview)
                
                # Generate context-aware suggestions
                suggestion = self.generate_moderation_suggestion(content_insights, alert)
                suggestions.append({
                    'alert': alert,
                    'suggestion': suggestion,
                    'content_insights': content_insights,
                    'confidence': suggestion.get('confidence', 0)
                })
        
        return suggestions
    
    def get_moderation_statistics(self):
        """Get enhanced moderation statistics with sentiment analysis"""
        subadmin_profile = self.request.user.subadmin_profile
        assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
        if subadmin_profile.region:
            assigned_countries.append(subadmin_profile.region)
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # Get sentiment analysis for recent alerts
        recent_alerts = ContentModerationAlert.objects.filter(
            Q(assigned_to=self.request.user) |
            Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
            created_at__date__gte=week_ago
        )
        
        sentiment_analyzer = SentimentAnalyzer()
        sentiment_scores = []
        toxicity_scores = []
        emotion_distribution = Counter()
        
        for alert in recent_alerts[:50]:  # Sample for performance
            if alert.content_preview:
                insights = sentiment_analyzer.get_content_insights(alert.content_preview)
                sentiment_scores.append(insights['sentiment']['score'])
                toxicity_scores.append(insights['toxicity']['toxicity_score'])
                emotion_distribution[insights['emotions']['primary_emotion']] += 1
        
        stats = {
            'total_pending': ContentModerationAlert.objects.filter(
                Q(assigned_to=self.request.user) |
                Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
                status='pending'
            ).count(),
            
            'critical_alerts': ContentModerationAlert.objects.filter(
                Q(assigned_to=self.request.user) |
                Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
                severity='critical',
                status='pending'
            ).count(),
            
            'resolved_this_week': ContentModerationAlert.objects.filter(
                assigned_to=self.request.user,
                status='resolved',
                resolved_at__date__gte=week_ago
            ).count(),
            
            'avg_resolution_time': self.calculate_avg_resolution_time(),
            
            'top_violation_types': ContentModerationAlert.objects.filter(
                Q(assigned_to=self.request.user) |
                Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
                status='resolved',
                resolved_at__date__gte=week_ago
            ).values('alert_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5],
            
            # Sentiment analytics
            'avg_sentiment': round(sum(sentiment_scores) / len(sentiment_scores), 3) if sentiment_scores else 0,
            'avg_toxicity': round(sum(toxicity_scores) / len(toxicity_scores), 3) if toxicity_scores else 0,
            'emotion_distribution': dict(emotion_distribution.most_common(5)),
            'sentiment_trend': self.calculate_sentiment_trend(week_ago)
        }
        
        return stats
    
    def get_sentiment_insights(self):
        """Get comprehensive sentiment insights for the region"""
        subadmin_profile = self.request.user.subadmin_profile
        assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
        if subadmin_profile.region:
            assigned_countries.append(subadmin_profile.region)
        
        # Analyze recent content in the region
        recent_posts = Post.objects.filter(
            author__country__in=assigned_countries,
            created_at__gte=timezone.now() - timedelta(days=7)
        )[:100]
        
        sentiment_analyzer = SentimentAnalyzer()
        engagement_predictor = EngagementPredictor()
        
        sentiment_data = {
            'total_posts_analyzed': len(recent_posts),
            'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
            'avg_engagement_score': 0,
            'common_emotions': [],
            'toxicity_level': 'low'
        }
        
        if recent_posts:
            engagement_scores = []
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
            emotion_counts = Counter()
            toxicity_scores = []
            
            for post in recent_posts:
                if post.content:
                    insights = sentiment_analyzer.get_content_insights(post.content)
                    
                    # Count sentiments
                    sentiment_label = insights['sentiment']['label']
                    sentiment_counts[sentiment_label] += 1
                    
                    # Track emotions
                    primary_emotion = insights['emotions']['primary_emotion']
                    if primary_emotion != 'neutral':
                        emotion_counts[primary_emotion] += 1
                    
                    # Track toxicity
                    toxicity_scores.append(insights['toxicity']['toxicity_score'])
                    
                    # Predict engagement
                    engagement_pred = engagement_predictor.predict_post_engagement(post.content)
                    engagement_scores.append(engagement_pred['engagement_score'])
            
            sentiment_data.update({
                'sentiment_distribution': sentiment_counts,
                'avg_engagement_score': round(sum(engagement_scores) / len(engagement_scores), 2) if engagement_scores else 0,
                'common_emotions': emotion_counts.most_common(3),
                'avg_toxicity': round(sum(toxicity_scores) / len(toxicity_scores), 3) if toxicity_scores else 0,
                'toxicity_level': self.get_toxicity_level(sum(toxicity_scores) / len(toxicity_scores) if toxicity_scores else 0)
            })
        
        return sentiment_data
    
    def calculate_enhanced_priority_score(self, alert, sentiment_analyzer):
        """Calculate enhanced priority score using sentiment analysis"""
        score = 0
        
        # Severity multiplier
        severity_multipliers = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 5
        }
        
        score += severity_multipliers.get(alert.severity, 1) * 10
        
        # Analyze content if available
        if alert.content_preview:
            insights = sentiment_analyzer.get_content_insights(alert.content_preview)
            
            # Factor in toxicity
            score += insights['toxicity']['toxicity_score'] * 30
            
            # Factor in negative sentiment
            if insights['sentiment']['label'] == 'negative':
                score += 15
            
            # Factor in emotional intensity
            if insights['emotions']['primary_emotion'] in ['anger', 'fear']:
                score += 10
        
        # User violation history
        previous_violations = ContentModerationAlert.objects.filter(
            content_author=alert.content_author,
            status='resolved',
            created_at__lt=alert.created_at
        ).count()
        
        score += min(previous_violations * 8, 40)  # Increased weight for repeat offenders
        
        # Content type multiplier
        if alert.content_type == 'post':
            score += 8  # Higher visibility
        elif alert.content_type == 'comment':
            score += 5
        
        # Recency bonus (newer alerts get slight priority)
        hours_old = (timezone.now() - alert.created_at).total_seconds() / 3600
        if hours_old < 1:
            score += 10  # Very recent
        elif hours_old < 4:
            score += 5   # Recent
        
        return min(score, 100)  # Cap at 100
    
    def generate_moderation_suggestion(self, content_insights, alert):
        """Generate context-aware moderation suggestions"""
        toxicity = content_insights['toxicity']
        sentiment = content_insights['sentiment']
        emotions = content_insights['emotions']
        spam = content_insights['spam']
        
        suggestion = {
            'recommended_action': 'review',
            'confidence': 0.7,
            'reasons': [],
            'risk_factors': []
        }
        
        # High toxicity content
        if toxicity['toxicity_score'] > 0.8:
            suggestion['recommended_action'] = 'remove_content'
            suggestion['confidence'] = 0.9
            suggestion['reasons'].append(f"High toxicity score: {toxicity['toxicity_score']:.2f}")
            if toxicity['toxic_words']:
                suggestion['reasons'].append(f"Toxic words detected: {', '.join(toxicity['toxic_words'][:3])}")
        
        # Spam content
        elif spam['is_spam'] and spam['spam_score'] > 0.7:
            suggestion['recommended_action'] = 'remove_content'
            suggestion['confidence'] = 0.8
            suggestion['reasons'].append("High probability of spam content")
        
        # Negative emotional content
        elif emotions['primary_emotion'] in ['anger', 'disgust'] and sentiment['score'] < -0.3:
            suggestion['recommended_action'] = 'warn_user'
            suggestion['confidence'] = 0.75
            suggestion['reasons'].append(f"Negative emotional content: {emotions['primary_emotion']}")
        
        # Low risk content
        elif toxicity['toxicity_score'] < 0.3 and not spam['is_spam']:
            suggestion['recommended_action'] = 'dismiss'
            suggestion['confidence'] = 0.6
            suggestion['reasons'].append("Low risk content based on sentiment analysis")
        
        # Add risk factors
        if toxicity['toxic_words']:
            suggestion['risk_factors'].append(f"Contains toxic language: {len(toxicity['toxic_words'])} words")
        if spam['spam_indicators']:
            suggestion['risk_factors'].append(f"Spam indicators: {len(spam['spam_indicators'])}")
        if sentiment['score'] < -0.5:
            suggestion['risk_factors'].append("Highly negative sentiment")
        
        return suggestion
    
    def calculate_avg_resolution_time(self):
        """Calculate average resolution time for alerts"""
        resolved_alerts = ContentModerationAlert.objects.filter(
            assigned_to=self.request.user,
            status='resolved',
            resolved_at__isnull=False,
            created_at__isnull=False
        )
        
        if not resolved_alerts:
            return 0
        
        total_seconds = 0
        count = 0
        
        for alert in resolved_alerts:
            resolution_time = alert.resolved_at - alert.created_at
            total_seconds += resolution_time.total_seconds()
            count += 1
        
        return round(total_seconds / count / 60, 2) if count > 0 else 0  # Return in minutes
    
    def calculate_sentiment_trend(self, since_date):
        """Calculate sentiment trend over time"""
        # This would typically involve more complex time-series analysis
        # Simplified implementation for demo purposes
        recent_alerts = ContentModerationAlert.objects.filter(
            assigned_to=self.request.user,
            created_at__date__gte=since_date
        )
        
        if recent_alerts.count() < 10:
            return "stable"
        
        # Simple trend calculation (could be enhanced with proper time-series analysis)
        return "improving"  # Placeholder
    
    def get_toxicity_level(self, avg_toxicity):
        """Convert toxicity score to level"""
        if avg_toxicity > 0.7:
            return "critical"
        elif avg_toxicity > 0.5:
            return "high"
        elif avg_toxicity > 0.3:
            return "medium"
        else:
            return "low"


@login_required
@user_passes_test(is_subadmin)
def subadmin_dashboard(request):
    """Main dashboard for SubAdmin showing regional overview"""
    try:
        subadmin_profile = request.user.subadmin_profile
    except SubAdminProfile.DoesNotExist:
        messages.error(request, 'SubAdmin profile not configured')
        return redirect('dashboard')
    
    # Get regional statistics (country-based)
    region = subadmin_profile.region
    assigned_areas = subadmin_profile.assigned_areas

    # Get assigned countries for this SubAdmin
    assigned_countries = assigned_areas if assigned_areas else []
    if region:
        assigned_countries.append(region)

    # Get reports relevant to this SubAdmin's countries (based on target content author's country)
    all_reports = Report.objects.all()
    regional_report_ids = []
    for report in all_reports:
        # Check if target user is from assigned countries
        if report.target_user and report.target_user.country in assigned_countries:
            regional_report_ids.append(report.id)

    # Pending reports in countries (based on content author's location)
    pending_reports = Report.objects.filter(
        id__in=regional_report_ids,
        status='pending'
    ).count()

    # Reports under review
    reviewing_reports = Report.objects.filter(
        reviewed_by=request.user,
        status='reviewing'
    ).count()

    # Get regional users using country filtering (not region)
    regional_users = User.objects.filter(country__in=assigned_countries)

    # Pending KYC verifications
    pending_kyc = CelebrityProfile.objects.filter(
        user__in=regional_users,
        verification_status='pending'
    ).count()

    # Recent reports (filtered by target region)
    recent_reports = Report.objects.filter(
        id__in=regional_report_ids
    ).select_related('reported_by', 'target_user').order_by('-created_at')[:10]
    
    # KYC queue
    kyc_queue = CelebrityProfile.objects.filter(
        user__in=regional_users.filter(user_type='celebrity'),
        verification_status='pending'
    ).select_related('user').order_by('created_at')[:5]
    
    # Recent moderation actions
    recent_actions = ModerationAction.objects.filter(
        performed_by=request.user
    ).select_related('target_user').order_by('-created_at')[:10]
    
    # Calculate daily statistics
    today = timezone.now().date()
    today_reports_resolved = Report.objects.filter(
        reviewed_by=request.user,
        reviewed_at__date=today,
        status__in=['resolved', 'dismissed']
    ).count()
    
    today_kyc_processed = CelebrityProfile.objects.filter(
        user__in=regional_users,
        verification_status__in=['verified', 'rejected'],
        updated_at__date=today
    ).count()

    # Get AI moderation alert statistics
    from apps.subadmin.models import ContentModerationAlert

    pending_alerts = ContentModerationAlert.objects.filter(
        Q(assigned_to=request.user) |
        Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
        status='pending'
    ).count()

    critical_alerts = ContentModerationAlert.objects.filter(
        Q(assigned_to=request.user) |
        Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
        severity='critical',
        status='pending'
    ).count()

    # Get AI-powered insights with enhanced sentiment analysis
    sentiment_analyzer = SentimentAnalyzer()
    engagement_predictor = EngagementPredictor()
    
    # Analyze recent regional content sentiment
    recent_regional_posts = Post.objects.filter(
        author__country__in=assigned_countries,
        created_at__gte=timezone.now() - timedelta(days=1)
    )[:20]
    
    regional_sentiment = {
        'positive_posts': 0,
        'negative_posts': 0,
        'avg_engagement': 0,
        'content_health': 'good'
    }
    
    if recent_regional_posts:
        engagement_scores = []
        for post in recent_regional_posts:
            if post.content:
                insights = sentiment_analyzer.get_content_insights(post.content)
                if insights['sentiment']['label'] == 'positive':
                    regional_sentiment['positive_posts'] += 1
                elif insights['sentiment']['label'] == 'negative':
                    regional_sentiment['negative_posts'] += 1
                
                engagement_pred = engagement_predictor.predict_post_engagement(post.content)
                engagement_scores.append(engagement_pred['engagement_score'])
        
        regional_sentiment['avg_engagement'] = round(sum(engagement_scores) / len(engagement_scores), 2) if engagement_scores else 0
        
        # Determine content health
        positivity_ratio = regional_sentiment['positive_posts'] / len(recent_regional_posts) if recent_regional_posts else 0
        if positivity_ratio > 0.7:
            regional_sentiment['content_health'] = 'excellent'
        elif positivity_ratio > 0.5:
            regional_sentiment['content_health'] = 'good'
        elif positivity_ratio > 0.3:
            regional_sentiment['content_health'] = 'fair'
        else:
            regional_sentiment['content_health'] = 'poor'

    context = {
        'region': region,
        'assigned_areas': assigned_areas,
        'pending_reports': pending_reports,
        'reviewing_reports': reviewing_reports,
        'pending_kyc': pending_kyc,
        'recent_reports': recent_reports,
        'kyc_queue': kyc_queue,
        'recent_actions': recent_actions,
        'today_reports_resolved': today_reports_resolved,
        'today_kyc_processed': today_kyc_processed,
        'total_users_region': regional_users.count(),
        'celebrities_region': regional_users.filter(user_type='celebrity').count(),
        'fans_region': regional_users.filter(user_type='fan').count(),
        'pending_alerts': pending_alerts,
        'critical_alerts': critical_alerts,
        'regional_sentiment': regional_sentiment,
    }

    return render(request, 'subadmin/dashboard.html', context)


@login_required
@user_passes_test(is_subadmin)
def reports_management(request):
    """Manage reports with enhanced sentiment analysis - filtered by target content author's country"""
    subadmin_profile = request.user.subadmin_profile

    # Filter reports
    status_filter = request.GET.get('status', 'pending')
    report_type = request.GET.get('type', 'all')

    # Get assigned countries for this SubAdmin
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    # Get all reports and filter by country (not region)
    all_reports = Report.objects.all()

    # Filter reports where the target content author is from this SubAdmin's assigned countries
    regional_report_ids = []
    for report in all_reports:
        # Check if target user is from assigned countries
        if report.target_user and report.target_user.country in assigned_countries:
            regional_report_ids.append(report.id)
            continue

        # If no target_user, check the content author's country
        if report.report_type == 'post' and report.target_object_id:
            try:
                from apps.posts.models import Post
                post = Post.objects.get(id=report.target_object_id)
                if post.author.country in assigned_countries:
                    regional_report_ids.append(report.id)
            except:
                pass
        elif report.report_type == 'event' and report.target_object_id:
            try:
                from apps.events.models import Event
                event = Event.objects.get(id=report.target_object_id)
                if event.organizer.country in assigned_countries:
                    regional_report_ids.append(report.id)
            except:
                pass
        elif report.report_type == 'merchandise' and report.target_object_id:
            try:
                from apps.merchandise.models import Merchandise
                merch = Merchandise.objects.get(id=report.target_object_id)
                if merch.seller.country in assigned_countries:
                    regional_report_ids.append(report.id)
            except:
                pass

    reports = Report.objects.filter(id__in=regional_report_ids)
    
    if status_filter != 'all':
        reports = reports.filter(status=status_filter)
    
    if report_type != 'all':
        reports = reports.filter(report_type=report_type)
    
    reports = reports.select_related('reported_by', 'target_user', 'reviewed_by')
    
    # Add enhanced sentiment analysis for pending reports
    sentiment_analyzer = SentimentAnalyzer()
    engagement_predictor = EngagementPredictor()
    
    for report in reports:
        if report.status == 'pending' and report.description:
            # Analyze report content with enhanced sentiment analysis
            sentiment_result = sentiment_analyzer.get_content_insights(report.description)
            report.sentiment_score = sentiment_result['sentiment']['score']
            report.sentiment_label = sentiment_result['sentiment']['label']
            report.sentiment_confidence = sentiment_result['sentiment']['confidence']
            report.toxicity_score = sentiment_result['toxicity']['toxicity_score']
            report.severity = sentiment_result['toxicity']['severity']
            report.emotion_analysis = sentiment_result['emotions']
            report.spam_analysis = sentiment_result['spam']
            
            # Get reported content if available
            if report.report_type == 'post' and report.target_object_id:
                try:
                    post = Post.objects.get(id=report.target_object_id)
                    post_sentiment = sentiment_analyzer.get_content_insights(post.content)
                    report.content_sentiment = post_sentiment
                    report.reported_content = post.content[:200]
                    
                    # Predict engagement for reported content
                    if post.author:
                        author_stats = {
                            'followers_count': post.author.total_followers or 0,
                            'avg_likes': getattr(post.author, 'avg_likes', 0)
                        }
                        engagement_pred = engagement_predictor.predict_post_engagement(post.content, author_stats)
                        report.engagement_prediction = engagement_pred
                except Post.DoesNotExist:
                    pass
            elif report.report_type == 'comment' and report.target_object_id:
                try:
                    comment = Comment.objects.get(id=report.target_object_id)
                    comment_sentiment = sentiment_analyzer.get_content_insights(comment.content)
                    report.content_sentiment = comment_sentiment
                    report.reported_content = comment.content
                except Comment.DoesNotExist:
                    pass
    
    # Get total count before sorting
    total_reports = reports.count()

    # Enhanced sorting for pending reports
    if status_filter == 'pending':
        reports = sorted(reports, key=lambda x: (
            getattr(x, 'toxicity_score', 0) * 0.4 +
            (1 - getattr(x, 'sentiment_confidence', 0)) * 0.3 +
            (1 if getattr(x, 'severity', 'low') == 'high' else 0) * 0.3
        ), reverse=True)

    # Pagination
    paginator = Paginator(reports, 20)
    page = request.GET.get('page', 1)
    reports_page = paginator.get_page(page)

    context = {
        'reports': reports_page,
        'status_filter': status_filter,
        'report_type': report_type,
        'total_reports': total_reports,
    }
    
    return render(request, 'subadmin/reports_management.html', context)


@login_required
@user_passes_test(is_subadmin)
def review_report(request, report_id):
    """Detailed report review with enhanced sentiment analysis actions"""
    report = get_object_or_404(Report, id=report_id)
    
    # Check if report is in subadmin's assigned countries
    subadmin_profile = request.user.subadmin_profile
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    # Check if target user is from assigned countries
    if report.target_user and report.target_user.country not in assigned_countries:
        messages.error(request, 'This report is outside your assigned countries')
        return redirect('subadmin_reports')
    
    # Enhanced sentiment analysis
    sentiment_analyzer = SentimentAnalyzer()
    engagement_predictor = EngagementPredictor()
    sentiment_result = sentiment_analyzer.get_content_insights(report.description)
    
    # Get reported content
    reported_content = None
    content_sentiment = None
    content_engagement = None
    
    if report.report_type == 'post' and report.target_object_id:
        try:
            post = Post.objects.get(id=report.target_object_id)
            reported_content = post
            content_sentiment = sentiment_analyzer.get_content_insights(post.content)
            
            # Predict engagement for context
            if post.author:
                author_stats = {
                    'followers_count': post.author.total_followers or 0,
                    'avg_likes': getattr(post.author, 'avg_likes', 0)
                }
                content_engagement = engagement_predictor.predict_post_engagement(post.content, author_stats)
        except Post.DoesNotExist:
            pass
    elif report.report_type == 'comment' and report.target_object_id:
        try:
            comment = Comment.objects.get(id=report.target_object_id)
            reported_content = comment
            content_sentiment = sentiment_analyzer.get_content_insights(comment.content)
        except Comment.DoesNotExist:
            pass
    
    # Get user history with sentiment analysis
    if report.target_user:
        previous_violations = Report.objects.filter(
            target_user=report.target_user,
            status='resolved'
        ).count()
        
        previous_warnings = ModerationAction.objects.filter(
            target_user=report.target_user,
            action_type='warning'
        ).count()
        
        # Analyze user's recent content sentiment
        user_recent_posts = Post.objects.filter(
            author=report.target_user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )[:10]
        
        user_sentiment_profile = {
            'avg_sentiment': 0,
            'toxicity_trend': 'stable',
            'content_quality': 'good'
        }
        
        if user_recent_posts:
            sentiment_scores = []
            toxicity_scores = []
            
            for post in user_recent_posts:
                if post.content:
                    insights = sentiment_analyzer.get_content_insights(post.content)
                    sentiment_scores.append(insights['sentiment']['score'])
                    toxicity_scores.append(insights['toxicity']['toxicity_score'])
            
            if sentiment_scores:
                user_sentiment_profile['avg_sentiment'] = round(sum(sentiment_scores) / len(sentiment_scores), 3)
                avg_toxicity = sum(toxicity_scores) / len(toxicity_scores) if toxicity_scores else 0
                
                if avg_toxicity > 0.6:
                    user_sentiment_profile['content_quality'] = 'poor'
                elif avg_toxicity > 0.3:
                    user_sentiment_profile['content_quality'] = 'fair'
                else:
                    user_sentiment_profile['content_quality'] = 'good'
    else:
        previous_violations = 0
        previous_warnings = 0
        user_sentiment_profile = {}
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        with transaction.atomic():
            # Update report status
            report.status = 'reviewing' if action == 'review' else 'resolved'
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.review_notes = request.POST.get('notes', '')
            
            # Take action based on decision with sentiment context
            if action == 'delete_content':
                # Delete the reported content
                if reported_content:
                    if isinstance(reported_content, Post):
                        reported_content.is_active = False
                        reported_content.save()
                        report.action_taken = 'Post deleted'
                    elif isinstance(reported_content, Comment):
                        reported_content.is_deleted = True
                        reported_content.save()
                        report.action_taken = 'Comment deleted'
                
                # Notify user with sentiment context
                if report.target_user:
                    Notification.objects.create(
                        recipient=report.target_user,
                        notification_type='warning',
                        message=f'Your {report.report_type} was removed for violating community guidelines. Content analysis: {sentiment_result["sentiment"]["label"]} sentiment detected.',
                        target_id=str(report.id)
                    )
            
            elif action == 'warn_user':
                # Issue warning with sentiment context
                if report.target_user:
                    ModerationAction.objects.create(
                        action_type='warning',
                        target_user=report.target_user,
                        report=report,
                        reason=f'{report.get_reason_display()}: {report.description[:200]} (Sentiment: {sentiment_result["sentiment"]["label"]})',
                        performed_by=request.user
                    )
                    
                    # Deduct points based on severity
                    points_deducted = 20
                    if sentiment_result['toxicity']['severity'] == 'high':
                        points_deducted = 30
                    elif sentiment_result['toxicity']['severity'] == 'critical':
                        points_deducted = 50
                    
                    report.target_user.deduct_points(points_deducted, 'Warning for violation')
                    
                    # Update user warnings count
                    report.target_user.warnings_count += 1
                    report.target_user.save()
                    
                    # Notify user
                    Notification.objects.create(
                        recipient=report.target_user,
                        notification_type='warning',
                        message=f'You have received a warning for violating community guidelines. Content analysis detected {sentiment_result["toxicity"]["severity"]} level issues.',
                        target_id=str(report.id)
                    )
                    
                    report.action_taken = 'Warning issued'
            
            elif action == 'suspend_user':
                # Temporary suspension with sentiment-based duration
                if report.target_user:
                    base_duration = int(request.POST.get('suspension_days', 7))
                    
                    # Adjust duration based on sentiment analysis
                    if sentiment_result['toxicity']['severity'] == 'high':
                        base_duration = max(base_duration, 14)
                    elif sentiment_result['toxicity']['severity'] == 'critical':
                        base_duration = max(base_duration, 30)
                    
                    ModerationAction.objects.create(
                        action_type='temporary_ban',
                        target_user=report.target_user,
                        report=report,
                        reason=f'{report.get_reason_display()}: {report.description[:200]} (Toxicity: {sentiment_result["toxicity"]["toxicity_score"]:.2f})',
                        duration_days=base_duration,
                        performed_by=request.user
                    )
                    
                    # Ban user
                    report.target_user.ban_user(
                        reason=f'Suspended for {report.get_reason_display()} - High toxicity content',
                        duration_days=base_duration
                    )
                    
                    # Deduct points
                    report.target_user.deduct_points(100, f'Suspended for {base_duration} days')
                    
                    # Update subadmin stats
                    subadmin_profile.users_banned += 1
                    subadmin_profile.save()
                    
                    report.action_taken = f'{base_duration}-day suspension'
            
            elif action == 'ban_user':
                # Permanent ban for severe cases
                if report.target_user:
                    ModerationAction.objects.create(
                        action_type='permanent_ban',
                        target_user=report.target_user,
                        report=report,
                        reason=f'{report.get_reason_display()}: {report.description[:200]} (Critical toxicity: {sentiment_result["toxicity"]["toxicity_score"]:.2f})',
                        performed_by=request.user
                    )
                    
                    # Ban user permanently
                    report.target_user.ban_user(
                        reason=f'Permanently banned for {report.get_reason_display()} - Critical violation'
                    )
                    
                    # Update subadmin stats
                    subadmin_profile.users_banned += 1
                    subadmin_profile.save()
                    
                    report.action_taken = 'Permanent ban'
            
            elif action == 'dismiss':
                # Dismiss report with sentiment justification
                report.status = 'dismissed'
                report.action_taken = 'Report dismissed'
                if sentiment_result['sentiment']['label'] == 'positive':
                    report.review_notes += " | Dismissed: Content appears positive and constructive"
            
            report.save()
            
            # Update subadmin metrics
            subadmin_profile.reports_resolved += 1
            subadmin_profile.save()
            
            # Notify reporter of decision with sentiment context
            Notification.objects.create(
                recipient=report.reported_by,
                notification_type='system',
                message=f'Your report has been reviewed. Action: {report.action_taken}. Content analysis: {sentiment_result["sentiment"]["label"]} sentiment.',
                target_id=str(report.id)
            )
            
            messages.success(request, f'Report has been {report.status}')
            return redirect('subadmin_reports')
    
    context = {
        'report': report,
        'sentiment_result': sentiment_result,
        'reported_content': reported_content,
        'content_sentiment': content_sentiment,
        'content_engagement': content_engagement,
        'previous_violations': previous_violations,
        'previous_warnings': previous_warnings,
        'user_sentiment_profile': user_sentiment_profile,
    }
    
    return render(request, 'subadmin/review_report.html', context)

@login_required
@login_required
@user_passes_test(is_subadmin)
def kyc_verification(request):
    """KYC verification queue for celebrities - include all pending and resubmission cases"""
    subadmin_profile = request.user.subadmin_profile

    # Filter celebrities by country
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    # Get celebrities from assigned countries
    regional_users = User.objects.filter(
        user_type='celebrity',
        country__in=assigned_countries
    )

    # Get ALL pending KYC applications (including those needing resubmission)
    # Only exclude approved and permanently rejected cases
    pending_kyc = CelebrityProfile.objects.filter(
        user__in=regional_users,
        verification_status__in=['pending', 'rejected']  # Include both pending and rejected (for resubmission)
    ).select_related('user').order_by('-created_at')

    # Get recent verifications by this SubAdmin
    recent_verifications = CelebrityProfile.objects.filter(
        verified_by=request.user,
        verification_status__in=['approved', 'rejected'],
        verification_date__gte=timezone.now() - timedelta(days=7)
    ).select_related('user').order_by('-verification_date')[:10]

    # Stats
    total_pending = pending_kyc.count()
    verified_today = CelebrityProfile.objects.filter(
        verified_by=request.user,
        verification_status='approved',
        verification_date__date=timezone.now().date()
    ).count()

    context = {
        'pending_kyc': pending_kyc,
        'recent_verifications': recent_verifications,
        'total_pending': total_pending,
        'verified_today': verified_today,
    }

    return render(request, 'subadmin/kyc_verification.html', context)

@login_required
@user_passes_test(is_subadmin)
def verify_celebrity(request, celebrity_id):
    """Verify individual celebrity KYC with proper document handling"""
    celebrity_profile = get_object_or_404(CelebrityProfile, id=celebrity_id)
    
    # Check if celebrity is in subadmin's assigned countries
    subadmin_profile = request.user.subadmin_profile
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)
    
    if celebrity_profile.user.country not in assigned_countries:
        messages.error(request, 'This celebrity is outside your assigned countries')
        return redirect('subadmin_kyc')
    
    # Get KYC documents - use the user instance, not the profile
    kyc_docs = KYCDocument.objects.filter(celebrity=celebrity_profile.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        with transaction.atomic():
            if action == 'approve':
                # Approve KYC
                celebrity_profile.verification_status = 'approved'
                celebrity_profile.verification_date = timezone.now()
                celebrity_profile.verified_by = request.user
                celebrity_profile.verification_notes = notes
                celebrity_profile.save()

                # Update user verification
                user = celebrity_profile.user
                user.is_verified = True
                user.verification_status = 'verified'
                user.verification_badge = True
                user.save()
                
                # Award points for verification
                user.add_points(100, 'Profile verified')
                
                # Create notification
                Notification.objects.create(
                    recipient=user,
                    notification_type='system',
                    message='Congratulations! Your celebrity profile has been verified.',
                    target_id=str(celebrity_profile.id)
                )
                
                # Update subadmin metrics
                subadmin_profile.kyc_handled += 1
                subadmin_profile.save()
                
                messages.success(request, f'{user.username} has been verified successfully')
                
            elif action == 'reject':
                # Reject KYC - but keep them in the queue for resubmission
                celebrity_profile.verification_status = 'rejected'
                celebrity_profile.verification_notes = notes
                celebrity_profile.needs_resubmission = True  # New field
                celebrity_profile.save()
                
                # Update user verification
                user = celebrity_profile.user
                user.verification_status = 'rejected'
                user.save()
                
                # Create notification with resubmission instructions
                Notification.objects.create(
                    recipient=user,
                    notification_type='system',
                    message=f'Your verification was rejected. Reason: {notes}. Please upload additional documents and resubmit.',
                    target_id=str(celebrity_profile.id)
                )
                
                # Update subadmin metrics
                subadmin_profile.kyc_handled += 1
                subadmin_profile.save()
                
                messages.warning(request, f'{user.username} verification has been rejected')
            
            elif action == 'request_more':
                # Request more documents - keep status as pending but mark for resubmission
                celebrity_profile.verification_status = 'pending'
                celebrity_profile.verification_notes = notes
                celebrity_profile.needs_resubmission = True  # New field
                celebrity_profile.save()
                
                # Create notification
                Notification.objects.create(
                    recipient=celebrity_profile.user,
                    notification_type='system',
                    message=f'Please provide additional documents: {notes}',
                    target_id=str(celebrity_profile.id)
                )
                
                messages.info(request, 'Additional documents requested')
            
            return redirect('subadmin_kyc')
    
    context = {
        'celebrity': celebrity_profile,
        'kyc_docs': kyc_docs,
        'user': celebrity_profile.user,
    }
    
    return render(request, 'subadmin/verify_celebrity.html', context)

@login_required
@user_passes_test(is_subadmin)
def activity_reports(request):
    """Generate and view activity reports for admin"""
    subadmin_profile = request.user.subadmin_profile
    
    # Date range filter
    date_from = request.GET.get('from', (timezone.now() - timedelta(days=30)).date())
    date_to = request.GET.get('to', timezone.now().date())
    
    if isinstance(date_from, str):
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    if isinstance(date_to, str):
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Get statistics for the period
    reports_resolved = Report.objects.filter(
        reviewed_by=request.user,
        reviewed_at__date__gte=date_from,
        reviewed_at__date__lte=date_to,
        status__in=['resolved', 'dismissed']
    ).count()
    
    kyc_processed = CelebrityProfile.objects.filter(
        verified_by=request.user,
        verification_date__date__gte=date_from,
        verification_date__date__lte=date_to
    ).count()
    
    moderation_actions = ModerationAction.objects.filter(
        performed_by=request.user,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    
    warnings_issued = moderation_actions.filter(action_type='warning').count()
    temp_bans = moderation_actions.filter(action_type='temporary_ban').count()
    perm_bans = moderation_actions.filter(action_type='permanent_ban').count()
    
    # Get detailed actions
    detailed_actions = moderation_actions.select_related('target_user', 'report').order_by('-created_at')
    
    # Regional statistics
    regional_users = User.objects.filter(
        Q(country__in=subadmin_profile.assigned_areas) | Q(city=subadmin_profile.region)
    )
    
    new_users = regional_users.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    ).count()
    
    active_users = regional_users.filter(
        last_active__date__gte=date_from,
        last_active__date__lte=date_to
    ).count()
    
    # Sentiment analysis overview
    reports_in_period = Report.objects.filter(
        reviewed_by=request.user,
        reviewed_at__date__gte=date_from,
        reviewed_at__date__lte=date_to
    )
    
    sentiment_analyzer = SentimentAnalyzer()
    toxicity_scores = []
    
    for report in reports_in_period[:100]:  # Sample for performance
        if report.description:
            result = sentiment_analyzer.detect_toxicity(report.description)
            toxicity_scores.append(result['toxicity_score'])
    
    avg_toxicity = sum(toxicity_scores) / len(toxicity_scores) if toxicity_scores else 0

    # Convert detailed_actions to list of dicts for JSON serialization
    actions_list = []
    for action in detailed_actions[:20]:
        actions_list.append({
            'action_type': action.action_type,
            'target_user': action.target_user.username if action.target_user else 'N/A',
            'reason': action.reason or 'N/A',
            'created_at': action.created_at.strftime('%Y-%m-%d %H:%M'),
        })

    report_data = {
        'period': f'{date_from} to {date_to}',
        'region': subadmin_profile.region,
        'assigned_areas': subadmin_profile.assigned_areas,
        'reports_resolved': reports_resolved,
        'kyc_processed': kyc_processed,
        'warnings_issued': warnings_issued,
        'temp_bans': temp_bans,
        'perm_bans': perm_bans,
        'new_users': new_users,
        'active_users': active_users,
        'avg_toxicity': round(avg_toxicity, 2),
        'detailed_actions': actions_list,
    }
    
    # Generate report if requested
    if request.GET.get('generate') == 'true':
        # Create activity report for admin
        activity_report = SubAdminActivityReport.objects.create(
            subadmin=request.user,
            region=subadmin_profile.region,
            period_start=date_from,
            period_end=date_to,
            reports_data=report_data,
            submitted_at=timezone.now()
        )
        
        # Notify admin
        admins = User.objects.filter(user_type='admin')
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notification_type='system',
                message=f'SubAdmin Activity Report submitted by {request.user.username} for {subadmin_profile.region}',
                target_id=str(activity_report.id)
            )
        
        messages.success(request, 'Activity report has been generated and sent to admin')
    
    context = {
        'report_data': report_data,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'subadmin/activity_reports.html', context)


@login_required
@user_passes_test(is_subadmin)
def user_management(request):
    """Manage users in assigned countries"""
    subadmin_profile = request.user.subadmin_profile

    # Get assigned countries
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    regional_users = User.objects.filter(
        country__in=assigned_countries
    ).exclude(user_type__in=['admin', 'subadmin'])

    # Filters
    user_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    search = request.GET.get('search', '')

    if user_type != 'all':
        regional_users = regional_users.filter(user_type=user_type)

    # Fix status filtering to properly handle all cases
    if status == 'banned':
        # Permanently banned users (no banned_until date)
        regional_users = regional_users.filter(is_banned=True, banned_until__isnull=True)
    elif status == 'suspended':
        # Temporarily banned users (have banned_until date)
        regional_users = regional_users.filter(is_banned=True, banned_until__isnull=False)
    elif status == 'active':
        # Active users (not banned and account is active)
        regional_users = regional_users.filter(is_active=True, is_banned=False)
    elif status == 'inactive':
        # Inactive users (is_active=False but not banned)
        regional_users = regional_users.filter(is_active=False, is_banned=False)

    if search:
        regional_users = regional_users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    # Order by recent activity (use last_active instead of last_seen)
    regional_users = regional_users.order_by('-last_active')

    # Pagination
    paginator = Paginator(regional_users, 50)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)

    context = {
        'users': users_page,
        'total_users': regional_users.count(),
        'user_type_filter': user_type,
        'status_filter': status,
        'search_query': search,
    }

    return render(request, 'subadmin/user_management.html', context)


@login_required
@user_passes_test(is_subadmin)
def user_profile_view(request, user_id):
    """View detailed user profile with violations and moderation history"""
    subadmin_profile = request.user.subadmin_profile

    # Get the user
    user = get_object_or_404(User, id=user_id)

    # Check if user is in subadmin's assigned countries
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    if user.country not in assigned_countries:
        messages.error(request, 'You do not have permission to view this user.')
        return redirect('subadmin_users')

    # Get user's violations and moderation actions
    violations = ModerationAction.objects.filter(
        target_user=user
    ).select_related('performed_by', 'report').order_by('-created_at')

    # Get user's reports (reports made by this user)
    reports_made = Report.objects.filter(reported_by=user).order_by('-created_at')[:10]

    # Get reports against this user
    reports_against = Report.objects.filter(target_user=user).order_by('-created_at')[:10]

    # Get user's posts with flagged content
    flagged_posts = Post.objects.filter(
        author=user,
        is_active=False
    ).order_by('-created_at')[:10]

    # Get user's activity stats
    total_posts = Post.objects.filter(author=user).count()
    total_comments = Comment.objects.filter(author=user).count()
    total_reports_made = reports_made.count()
    total_reports_against = reports_against.count()

    context = {
        'profile_user': user,
        'violations': violations,
        'reports_made': reports_made,
        'reports_against': reports_against,
        'flagged_posts': flagged_posts,
        'total_posts': total_posts,
        'total_comments': total_comments,
        'total_reports_made': total_reports_made,
        'total_reports_against': total_reports_against,
    }

    return render(request, 'subadmin/user_profile_detail.html', context)


@login_required
@user_passes_test(is_subadmin)
@require_http_methods(["POST"])
def quick_action(request):
    """Handle quick actions via AJAX"""
    action_type = request.POST.get('action')
    target_id = request.POST.get('target_id')
    
    try:
        if action_type == 'warn_user':
            user = User.objects.get(id=target_id)
            reason = request.POST.get('reason', 'Community guideline violation')
            
            # Create warning
            ModerationAction.objects.create(
                action_type='warning',
                target_user=user,
                reason=reason,
                performed_by=request.user
            )
            
            # Deduct points
            user.deduct_points(10, 'Warning issued')
            
            # Update warnings count
            user.warnings_count += 1
            user.save()
            
            # Notify user
            Notification.objects.create(
                recipient=user,
                notification_type='warning',
                message=f'Warning: {reason}'
            )
            
            return JsonResponse({'status': 'success', 'message': 'Warning issued'})
        
        elif action_type == 'delete_post':
            post = Post.objects.get(id=target_id)
            post.is_active = False
            post.save()
            
            # Notify author
            Notification.objects.create(
                recipient=post.author,
                notification_type='system',
                message='Your post was removed for violating guidelines'
            )
            
            return JsonResponse({'status': 'success', 'message': 'Post deleted'})
        
        elif action_type == 'approve_kyc':
            celebrity = CelebrityProfile.objects.get(id=target_id)
            celebrity.verification_status = 'approved'
            celebrity.verification_date = timezone.now()
            celebrity.verified_by = request.user
            celebrity.save()

            # Update user
            celebrity.user.is_verified = True
            celebrity.user.verification_status = 'verified'
            celebrity.user.save()
            
            return JsonResponse({'status': 'success', 'message': 'KYC approved'})
        
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# Additional helper views for SubAdmin

@login_required
@user_passes_test(is_subadmin)
def regional_analytics(request):
    """Regional analytics dashboard"""
    import json
    from django.db.models.functions import TruncDate

    subadmin_profile = request.user.subadmin_profile

    # Date filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
    else:
        date_from = (timezone.now() - timedelta(days=30)).date()

    if date_to:
        date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        date_to = timezone.now().date()

    # Get regional users by country
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    regional_users = User.objects.filter(country__in=assigned_countries)

    # Calculate analytics
    total_users = regional_users.count()
    total_celebrities = regional_users.filter(user_type='celebrity').count()
    total_fans = regional_users.filter(user_type='fan').count()

    # Reports handled in date range
    reports_handled = Report.objects.filter(
        reviewed_by=request.user,
        reviewed_at__date__gte=date_from,
        reviewed_at__date__lte=date_to,
        status__in=['resolved', 'dismissed']
    ).count()

    # KYC processed in date range
    kyc_processed = CelebrityProfile.objects.filter(
        verified_by=request.user,
        verification_date__date__gte=date_from,
        verification_date__date__lte=date_to
    ).count()

    # Moderation actions in date range
    moderation_actions = ModerationAction.objects.filter(
        performed_by=request.user,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    ).count()

    # Chart data - User growth
    growth_data = []
    growth_labels = []
    current_date = date_from
    while current_date <= date_to:
        count = regional_users.filter(created_at__date__lte=current_date).count()
        growth_data.append(count)
        growth_labels.append(current_date.strftime('%b %d'))
        current_date += timedelta(days=max(1, (date_to - date_from).days // 10))

    # Moderation summary data - filter by regional users
    regional_reports = Report.objects.filter(
        Q(target_user__in=regional_users) | Q(reported_by__in=regional_users)
    )

    resolved = regional_reports.filter(reviewed_by=request.user, status='resolved').count()
    dismissed = regional_reports.filter(reviewed_by=request.user, status='dismissed').count()
    pending = regional_reports.filter(status='pending').count()
    reviewing = regional_reports.filter(reviewed_by=request.user, status='reviewing').count()
    moderation_data = [resolved, dismissed, pending, reviewing]

    # Report type distribution
    report_types = Report.objects.filter(
        Q(target_user__in=regional_users) | Q(reported_by__in=regional_users)
    ).values('report_type').annotate(count=models.Count('id'))

    report_type_labels = []
    report_type_data = []
    for rt in report_types:
        report_type_labels.append(rt['report_type'].title())
        report_type_data.append(rt['count'])

    context = {
        'region': subadmin_profile.region,
        'total_users': total_users,
        'total_celebrities': total_celebrities,
        'total_fans': total_fans,
        'reports_handled': reports_handled,
        'kyc_processed': kyc_processed,
        'moderation_actions': moderation_actions,
        'date_from': date_from,
        'date_to': date_to,
        'growth_labels': json.dumps(growth_labels),
        'growth_data': json.dumps(growth_data),
        'moderation_data': json.dumps(moderation_data),
        'report_type_labels': json.dumps(report_type_labels),
        'report_type_data': json.dumps(report_type_data),
    }

    return render(request, 'subadmin/regional_analytics.html', context)


@login_required
@user_passes_test(is_subadmin)
def moderation_queue(request):
    """Content moderation alert queue for SubAdmins"""
    from apps.subadmin.models import ContentModerationAlert

    subadmin_profile = request.user.subadmin_profile

    # Get assigned countries
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    # Filter alerts
    status_filter = request.GET.get('status', 'pending')
    severity_filter = request.GET.get('severity', 'all')
    alert_type_filter = request.GET.get('type', 'all')

    # Get alerts from assigned region
    alerts = ContentModerationAlert.objects.filter(
        Q(assigned_to=request.user) |
        Q(content_author__country__in=assigned_countries, assigned_to__isnull=True)
    ).select_related('content_author', 'assigned_to')

    # Apply filters
    if status_filter != 'all':
        alerts = alerts.filter(status=status_filter)

    if severity_filter != 'all':
        alerts = alerts.filter(severity=severity_filter)

    if alert_type_filter != 'all':
        alerts = alerts.filter(alert_type=alert_type_filter)

    # Order by severity and date
    alerts = alerts.order_by('-severity', '-created_at')

    # Statistics
    total_pending = ContentModerationAlert.objects.filter(
        Q(assigned_to=request.user) |
        Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
        status='pending'
    ).count()

    total_resolved = ContentModerationAlert.objects.filter(
        assigned_to=request.user,
        status='resolved'
    ).count()

    critical_alerts = ContentModerationAlert.objects.filter(
        Q(assigned_to=request.user) |
        Q(content_author__country__in=assigned_countries, assigned_to__isnull=True),
        severity='critical',
        status='pending'
    ).count()

    # Pagination
    paginator = Paginator(alerts, 20)
    page = request.GET.get('page', 1)
    alerts_page = paginator.get_page(page)

    context = {
        'alerts': alerts_page,
        'status_filter': status_filter,
        'severity_filter': severity_filter,
        'alert_type_filter': alert_type_filter,
        'total_pending': total_pending,
        'total_resolved': total_resolved,
        'critical_alerts': critical_alerts,
    }

    return render(request, 'subadmin/moderation_queue.html', context)


@login_required
@user_passes_test(is_subadmin)
def review_alert(request, alert_id):
    """Review and take action on a content moderation alert"""
    from apps.subadmin.models import ContentModerationAlert

    alert = get_object_or_404(ContentModerationAlert, id=alert_id)

    # Check if alert is assigned to this subadmin or in their region
    subadmin_profile = request.user.subadmin_profile
    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    if alert.assigned_to and alert.assigned_to != request.user:
        if alert.content_author.country not in assigned_countries:
            messages.error(request, 'This alert is not assigned to you')
            return redirect('moderation_queue')

    # Get the content
    content_obj = None
    if alert.content_type == 'post':
        try:
            content_obj = Post.objects.get(id=alert.content_id)
        except Post.DoesNotExist:
            pass

    # Get user's violation history
    previous_alerts = ContentModerationAlert.objects.filter(
        content_author=alert.content_author,
        status='resolved',
        created_at__lt=alert.created_at
    ).order_by('-created_at')[:5]

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')

        with transaction.atomic():
            # Assign to current user if not assigned
            if not alert.assigned_to:
                alert.assigned_to = request.user

            # Update alert status
            alert.status = 'reviewing' if action == 'review' else 'resolved'
            alert.reviewed_at = timezone.now()
            alert.moderator_notes = notes

            # Take action
            if action == 'none':
                alert.action_taken = 'none'
                alert.status = 'dismissed'

            elif action == 'warned':
                # Warn user
                ModerationAction.objects.create(
                    action_type='warning',
                    target_user=alert.content_author,
                    reason=f'Toxic content detected: {alert.alert_type}',
                    performed_by=request.user
                )

                alert.content_author.warnings_count += 1
                alert.content_author.deduct_points(20, 'Warning for toxic content')
                alert.content_author.save()

                Notification.objects.create(
                    recipient=alert.content_author,
                    notification_type='warning',
                    message=f'Warning: Your content was flagged for {alert.get_alert_type_display().lower()}. {notes}'
                )

                alert.action_taken = 'warned'

            elif action == 'content_removed':
                # Remove content
                if content_obj and alert.content_type == 'post':
                    content_obj.is_active = False
                    content_obj.save()

                alert.content_author.deduct_points(50, 'Content removed')

                Notification.objects.create(
                    recipient=alert.content_author,
                    notification_type='warning',
                    message=f'Your {alert.content_type} was removed for violating guidelines. Reason: {notes}'
                )

                alert.action_taken = 'content_removed'

            elif action == 'user_suspended':
                # Suspend user
                duration_days = int(request.POST.get('suspension_days', 7))

                ModerationAction.objects.create(
                    action_type='temporary_ban',
                    target_user=alert.content_author,
                    reason=f'Suspended for {alert.get_alert_type_display()}: {notes}',
                    duration_days=duration_days,
                    performed_by=request.user
                )

                alert.content_author.ban_user(
                    reason=f'Suspended for {alert.get_alert_type_display()}',
                    duration_days=duration_days
                )

                alert.content_author.deduct_points(100, f'Suspended for {duration_days} days')

                # Remove content too
                if content_obj and alert.content_type == 'post':
                    content_obj.is_active = False
                    content_obj.save()

                Notification.objects.create(
                    recipient=alert.content_author,
                    notification_type='warning',
                    message=f'Your account has been suspended for {duration_days} days. Reason: {notes}'
                )

                alert.action_taken = 'user_suspended'
                subadmin_profile.users_banned += 1

            elif action == 'user_banned':
                # Permanently ban user
                ModerationAction.objects.create(
                    action_type='permanent_ban',
                    target_user=alert.content_author,
                    reason=f'Banned for {alert.get_alert_type_display()}: {notes}',
                    performed_by=request.user
                )

                alert.content_author.ban_user(
                    reason=f'Permanently banned for {alert.get_alert_type_display()}'
                )

                # Remove content too
                if content_obj and alert.content_type == 'post':
                    content_obj.is_active = False
                    content_obj.save()

                Notification.objects.create(
                    recipient=alert.content_author,
                    notification_type='warning',
                    message=f'Your account has been permanently banned. Reason: {notes}'
                )

                alert.action_taken = 'user_banned'
                subadmin_profile.users_banned += 1

            alert.resolved_at = timezone.now()
            alert.save()

            # Update subadmin metrics
            subadmin_profile.reports_resolved += 1
            subadmin_profile.save()

            messages.success(request, f'Alert resolved with action: {alert.get_action_taken_display()}')
            return redirect('moderation_queue')

    context = {
        'alert': alert,
        'content': content_obj,
        'previous_alerts': previous_alerts,
    }

    return render(request, 'subadmin/review_alert.html', context)


@login_required
@user_passes_test(is_subadmin)
def submit_activity_report(request):
    """Submit activity report to admin for review"""
    subadmin_profile = request.user.subadmin_profile

    if request.method == 'POST':
        # Get date range
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')

        if not period_start or not period_end:
            messages.error(request, 'Please select both start and end dates')
            return redirect('subadmin_dashboard')

        period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end, '%Y-%m-%d').date()

        # Get assigned countries
        assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
        if subadmin_profile.region:
            assigned_countries.append(subadmin_profile.region)

        # Calculate statistics for the period
        from apps.reports.models import Report, ModerationAction
        from apps.celebrities.models import CelebrityProfile
        from apps.subadmin.models import SubAdminActivityReport, ContentModerationAlert

        reports_resolved = Report.objects.filter(
            reviewed_by=request.user,
            reviewed_at__date__gte=period_start,
            reviewed_at__date__lte=period_end,
            status__in=['resolved', 'dismissed']
        ).count()

        kyc_processed = CelebrityProfile.objects.filter(
            verified_by=request.user,
            verification_date__date__gte=period_start,
            verification_date__date__lte=period_end
        ).count()

        moderation_actions = ModerationAction.objects.filter(
            performed_by=request.user,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )

        warnings_issued = moderation_actions.filter(action_type='warning').count()
        suspensions = moderation_actions.filter(action_type='temporary_ban').count()
        bans = moderation_actions.filter(action_type='permanent_ban').count()

        # Get AI moderation stats
        ai_alerts_resolved = ContentModerationAlert.objects.filter(
            assigned_to=request.user,
            resolved_at__date__gte=period_start,
            resolved_at__date__lte=period_end,
            status='resolved'
        )

        avg_toxicity = ai_alerts_resolved.aggregate(Avg('toxicity_score'))['toxicity_score__avg'] or 0
        avg_spam = ai_alerts_resolved.aggregate(Avg('spam_score'))['spam_score__avg'] or 0

        # Build detailed report data
        reports_data = {
            'period': f'{period_start} to {period_end}',
            'region': subadmin_profile.region,
            'assigned_areas': assigned_countries,
            'reports_resolved': reports_resolved,
            'kyc_processed': kyc_processed,
            'warnings_issued': warnings_issued,
            'suspensions_issued': suspensions,
            'bans_issued': bans,
            'ai_alerts_resolved': ai_alerts_resolved.count(),
            'avg_toxicity_score': round(avg_toxicity, 2),
            'avg_spam_score': round(avg_spam, 2),
            'summary': request.POST.get('summary', ''),
            'challenges': request.POST.get('challenges', ''),
            'achievements': request.POST.get('achievements', ''),
        }

        # Create activity report
        activity_report = SubAdminActivityReport.objects.create(
            subadmin=request.user,
            region=subadmin_profile.region,
            period_start=period_start,
            period_end=period_end,
            reports_data=reports_data,
            reports_resolved=reports_resolved,
            kyc_processed=kyc_processed,
            warnings_issued=warnings_issued,
            suspensions_issued=suspensions,
            bans_issued=bans,
            avg_toxicity_score=avg_toxicity,
            avg_spam_score=avg_spam,
            status='pending'
        )

        # Notify all admins
        admins = User.objects.filter(user_type='admin', is_active=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notification_type='system',
                message=f'SubAdmin Activity Report submitted by {request.user.username} for {subadmin_profile.region}',
                target_id=str(activity_report.id)
            )

        messages.success(request, 'Activity report submitted successfully! Admin will review it soon.')
        return redirect('subadmin_dashboard')

    # GET request - show form
    # Calculate default date range (last 30 days)
    today = timezone.now().date()
    default_start = today - timedelta(days=30)

    # Get previous reports
    previous_reports = SubAdminActivityReport.objects.filter(
        subadmin=request.user
    ).order_by('-submitted_at')[:5]

    context = {
        'default_start': default_start,
        'default_end': today,
        'previous_reports': previous_reports,
    }

    return render(request, 'subadmin/submit_report.html', context)


@login_required
@user_passes_test(is_subadmin)
def review_comment_report(request, report_id):
    """Review a comment report"""
    from apps.posts.models import CommentReport
    from apps.notifications.models import Notification

    report = get_object_or_404(CommentReport, id=report_id)

    # Check if SubAdmin has access to this region
    subadmin_profile = request.user.subadmin_profile
    comment_author_region = report.comment.author.region if hasattr(report.comment.author, 'region') else 'Global'

    assigned_countries = subadmin_profile.assigned_areas if subadmin_profile.assigned_areas else []
    if subadmin_profile.region:
        assigned_countries.append(subadmin_profile.region)

    if comment_author_region not in assigned_countries and request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to review this report.')
        return redirect('subadmin_reports')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')

        # Update report
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.action_notes = notes

        if action == 'remove_comment':
            report.action_taken = 'comment_removed'
            report.status = 'resolved'
            report.comment.is_active = False
            report.comment.is_blocked = True
            report.comment.save(update_fields=['is_active', 'is_blocked'])

            # Notify comment author
            Notification.objects.create(
                recipient=report.comment.author,
                notification_type='moderation',
                message=f'Your comment has been removed due to policy violations.'
            )

        elif action == 'warn_user':
            report.action_taken = 'warned'
            report.status = 'resolved'

            # Notify comment author
            Notification.objects.create(
                recipient=report.comment.author,
                notification_type='warning',
                message=f'Warning: Your comment violates our community guidelines. {notes}'
            )

        elif action == 'dismiss':
            report.action_taken = 'no_action'
            report.status = 'dismissed'

        elif action == 'suspend_user':
            report.action_taken = 'user_suspended'
            report.status = 'resolved'

            # Suspend user
            report.comment.author.is_active = False
            report.comment.author.save(update_fields=['is_active'])

            # Notify user
            Notification.objects.create(
                recipient=report.comment.author,
                notification_type='suspension',
                message=f'Your account has been suspended. Reason: {notes}'
            )

        report.save()

        # Notify reporter
        Notification.objects.create(
            recipient=report.reported_by,
            notification_type='report_update',
            message=f'Your comment report has been reviewed. Action taken: {report.get_action_taken_display()}'
        )

        messages.success(request, f'Comment report {report.get_status_display()}.')
        return redirect('subadmin_reports')

    # Analyze comment sentiment
    from algorithms.sentiment import SentimentAnalyzer
    analyzer = SentimentAnalyzer()
    insights = analyzer.get_content_insights(report.comment.content)

    context = {
        'report': report,
        'insights': insights,
    }

    return render(request, 'subadmin/review_comment_report.html', context)