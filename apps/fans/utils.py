# apps/fans/utils.py

from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import random
from .models import FanRecommendation, FanActivity
from apps.accounts.models import User

def generate_fan_recommendations(user):
    """Generate personalized recommendations for a fan"""
    from apps.accounts.models import UserFollowing, User
    from apps.celebrities.models import CelebrityProfile
    
    if user.user_type != 'fan':
        return
    
    # Check if recent recommendations exist
    recent_recommendations = FanRecommendation.objects.filter(
        fan=user,
        created_at__gte=timezone.now() - timedelta(days=1)
    ).count()
    
    if recent_recommendations >= 10:
        return
    
    # Get followed celebrities
    followed_ids = UserFollowing.objects.filter(
        follower=user
    ).values_list('following_id', flat=True)
    
    recommendations = []
    
    # 1. Collaborative filtering - celebrities followed by similar fans
    similar_fans = User.objects.filter(
        following__following_id__in=followed_ids,
        user_type='fan'
    ).exclude(id=user.id).distinct()[:20]
    
    for similar_fan in similar_fans:
        their_follows = UserFollowing.objects.filter(
            follower=similar_fan,
            following__user_type='celebrity'
        ).exclude(
            following_id__in=followed_ids
        ).values_list('following_id', flat=True)[:3]
        
        for celeb_id in their_follows:
            if celeb_id not in [r[0] for r in recommendations]:
                score = calculate_recommendation_score(user, celeb_id, 'collaborative')
                recommendations.append((celeb_id, score, 'Similar fans follow this celebrity'))
    
    # 2. Category-based recommendations
    if hasattr(user, 'fan_profile'):
        favorite_categories = user.fan_profile.favorite_categories or []
        
        category_celebs = User.objects.filter(
            user_type='celebrity',
            is_verified=True,
            celebrity_profile__category__in=favorite_categories
        ).exclude(
            id__in=followed_ids
        ).order_by('-points')[:5]
        
        for celeb in category_celebs:
            if celeb.id not in [r[0] for r in recommendations]:
                score = calculate_recommendation_score(user, celeb.id, 'category')
                recommendations.append((celeb.id, score, f'Popular in {celeb.celebrity_profile.get_category_display()}'))
    
    # 3. Trending celebrities
    trending = User.objects.filter(
        user_type='celebrity',
        is_verified=True
    ).exclude(
        id__in=followed_ids
    ).annotate(
        recent_followers=Count(
            'followers',
            filter=Q(followers__created_at__gte=timezone.now() - timedelta(days=7))
        )
    ).order_by('-recent_followers')[:5]
    
    for celeb in trending:
        if celeb.id not in [r[0] for r in recommendations]:
            score = calculate_recommendation_score(user, celeb.id, 'trending')
            recommendations.append((celeb.id, score, 'Trending this week'))
    
    # Create recommendation objects
    expires_at = timezone.now() + timedelta(days=7)
    
    for celeb_id, score, reason in recommendations[:15]:
        FanRecommendation.objects.get_or_create(
            fan=user,
            recommended_celebrity_id=celeb_id,
            defaults={
                'recommendation_score': score,
                'reason': reason,
                'expires_at': expires_at
            }
        )


def calculate_recommendation_score(user, celebrity_id, method):
    """Calculate recommendation score for a celebrity"""
    base_score = 50.0
    
    try:
        celebrity = User.objects.get(id=celebrity_id)
        
        # Adjust based on celebrity popularity
        if celebrity.points > 10000:
            base_score += 20
        elif celebrity.points > 5000:
            base_score += 10
        
        # Adjust based on method
        if method == 'collaborative':
            base_score += 30
        elif method == 'category':
            base_score += 25
        elif method == 'trending':
            base_score += 35
        
        # Random factor for diversity
        base_score += random.uniform(-10, 10)
        
    except User.DoesNotExist:
        pass
    
    return min(100, max(0, base_score))