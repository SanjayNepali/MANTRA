# apps/accounts/utils.py

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from apps.accounts.models import User, UserFollowing
import random
import string

def generate_verification_code(length=6):
    """Generate a random verification code"""
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(user, code):
    """Send verification email to user"""
    subject = 'MANTRA - Verify Your Email'
    
    html_message = render_to_string('emails/verification.html', {
        'user': user,
        'code': code,
    })
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_welcome_email(user):
    """Send welcome email to new user"""
    subject = f'Welcome to MANTRA, {user.username}!'
    
    template = 'emails/welcome_fan.html' if user.user_type == 'fan' else 'emails/welcome_celebrity.html'
    
    html_message = render_to_string(template, {
        'user': user,
    })
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_password_reset_email(user, reset_link):
    """Send password reset email"""
    subject = 'MANTRA - Password Reset Request'
    
    html_message = render_to_string('emails/password_reset.html', {
        'user': user,
        'reset_link': reset_link,
    })
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def calculate_user_engagement_score(user):
    """Calculate user engagement score"""
    from apps.posts.models import Post, Like, Comment
    from datetime import timedelta
    from django.utils import timezone
    
    # Get activity from last 30 days
    last_month = timezone.now() - timedelta(days=30)
    
    posts_count = Post.objects.filter(
        author=user,
        created_at__gte=last_month
    ).count()
    
    likes_count = Like.objects.filter(
        user=user,
        created_at__gte=last_month
    ).count()
    
    comments_count = Comment.objects.filter(
        author=user,
        created_at__gte=last_month
    ).count()
    
    # Calculate score (weighted)
    score = (posts_count * 10) + (comments_count * 5) + (likes_count * 2)
    
    return score


def get_user_recommendations(user, limit=10):
    """Get recommended users to follow"""
    from django.db.models import Count, Q
    
    # Get users that user's followings follow (collaborative filtering)
    following_ids = user.following.values_list('following_id', flat=True)
    
    recommended_users = User.objects.filter(
        followers__follower__in=following_ids
    ).exclude(
        Q(id=user.id) | Q(followers__follower=user)
    ).annotate(
        mutual_count=Count('followers')
    ).order_by('-mutual_count', '-points')[:limit]
    
    # If not enough recommendations, add top users
    if recommended_users.count() < limit:
        top_users = User.objects.filter(
            user_type='celebrity',
            is_verified=True,
            is_active=True
        ).exclude(
            Q(id=user.id) | Q(followers__follower=user)
        ).order_by('-points')[:limit - recommended_users.count()]
        
        recommended_users = list(recommended_users) + list(top_users)
    
    return recommended_users


def check_mutual_follow(user1, user2):
    """Check if two users follow each other"""
    return UserFollowing.objects.filter(
        follower=user1, following=user2
    ).exists() and UserFollowing.objects.filter(
        follower=user2, following=user1
    ).exists()


def get_user_statistics(user):
    """Get comprehensive user statistics"""
    from apps.posts.models import Post, Like, Comment
    from apps.fanclubs.models import FanClubMembership
    from apps.messaging.models import Message
    
    stats = {
        'followers_count': user.followers.count(),
        'following_count': user.following.count(),
        'posts_count': Post.objects.filter(author=user).count(),
        'likes_received': Like.objects.filter(post__author=user).count(),
        'comments_received': Comment.objects.filter(post__author=user).count(),
        'fanclubs_joined': FanClubMembership.objects.filter(user=user).count(),
        'messages_sent': Message.objects.filter(sender=user).count(),
        'points': user.points,
        'rank': user.rank,
        'engagement_score': calculate_user_engagement_score(user),
    }
    
    if user.user_type == 'celebrity':
        from apps.celebrities.models import CelebrityProfile
        try:
            celeb_profile = user.celebrity_profile
            stats['subscribers_count'] = celeb_profile.subscribers.count()
            stats['total_earnings'] = celeb_profile.total_earnings
        except CelebrityProfile.DoesNotExist:
            pass
    
    return stats