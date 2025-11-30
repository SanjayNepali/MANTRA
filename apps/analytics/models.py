# apps/analytics/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Avg
import uuid

class PlatformAnalytics(models.Model):
    """Platform-wide analytics"""
    
    date = models.DateField(unique=True)
    
    # User metrics
    total_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    
    # Content metrics
    total_posts = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_likes = models.IntegerField(default=0)
    
    # Financial metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subscription_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    event_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    merchandise_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Engagement metrics
    average_session_duration = models.IntegerField(default=0)  # in seconds
    page_views = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date']),
        ]
    
    def __str__(self):
        return f"Analytics for {self.date}"
    
    @classmethod
    def generate_daily_analytics(cls, date=None):
        """Generate analytics for a specific date"""
        if not date:
            date = timezone.now().date()
        
        from apps.accounts.models import User
        from apps.posts.models import Post, Like, Comment
        from apps.payments.models import PaymentTransaction
        
        # User metrics
        total_users = User.objects.filter(created_at__date__lte=date).count()
        new_users = User.objects.filter(created_at__date=date).count()
        active_users = User.objects.filter(last_active__date=date).count()
        
        # Content metrics
        total_posts = Post.objects.filter(created_at__date=date).count()
        total_comments = Comment.objects.filter(created_at__date=date).count()
        total_likes = Like.objects.filter(created_at__date=date).count()
        
        # Financial metrics
        payments = PaymentTransaction.objects.filter(
            created_at__date=date,
            status='completed'
        )
        
        total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or 0
        subscription_revenue = payments.filter(
            payment_type='subscription'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        event_revenue = payments.filter(
            payment_type='event'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        merchandise_revenue = payments.filter(
            payment_type='merchandise'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Create or update analytics
        analytics, created = cls.objects.update_or_create(
            date=date,
            defaults={
                'total_users': total_users,
                'new_users': new_users,
                'active_users': active_users,
                'total_posts': total_posts,
                'total_comments': total_comments,
                'total_likes': total_likes,
                'total_revenue': total_revenue,
                'subscription_revenue': subscription_revenue,
                'event_revenue': event_revenue,
                'merchandise_revenue': merchandise_revenue,
            }
        )
        
        return analytics


class UserEngagementMetrics(models.Model):
    """User engagement metrics"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='engagement_metrics'
    )
    
    # Activity metrics
    total_posts = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_likes_given = models.IntegerField(default=0)
    total_likes_received = models.IntegerField(default=0)
    
    # Engagement scores
    engagement_score = models.FloatField(default=0)
    influence_score = models.FloatField(default=0)
    
    # Time metrics
    total_time_spent = models.IntegerField(default=0)  # in seconds
    average_session_duration = models.IntegerField(default=0)
    
    # Network metrics
    followers_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)
    mutual_connections = models.IntegerField(default=0)
    
    last_calculated = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-engagement_score']
    
    def __str__(self):
        return f"Metrics for {self.user.username}"
    
    def calculate_engagement_score(self):
        """Calculate user engagement score"""
        # Weighted formula for engagement
        score = (
            self.total_posts * 10 +
            self.total_comments * 5 +
            self.total_likes_given * 2 +
            self.total_likes_received * 3 +
            self.followers_count * 1
        )
        
        # Normalize to 0-100 scale
        self.engagement_score = min(100, score / 100)
        self.save()
    
    def calculate_influence_score(self):
        """Calculate influence score"""
        if self.followers_count == 0:
            self.influence_score = 0
        else:
            # Based on follower ratio and engagement
            ratio = self.followers_count / (self.following_count + 1)
            engagement_factor = self.engagement_score / 100
            
            self.influence_score = min(100, ratio * engagement_factor * 50)
        
        self.save()