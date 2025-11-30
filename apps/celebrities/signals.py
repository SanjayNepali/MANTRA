# apps/celebrities/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.accounts.models import User
from .models import CelebrityProfile, Subscription, CelebrityAchievement

@receiver(post_save, sender=User)
def create_celebrity_profile(sender, instance, created, **kwargs):
    """Create celebrity profile when celebrity user is created"""
    if created and instance.user_type == 'celebrity':
        CelebrityProfile.objects.get_or_create(
            user=instance,
            defaults={'categories': [instance.category] if hasattr(instance, 'category') else []}
        )
        
        # Create default achievements
        create_default_achievements(instance)



def create_default_achievements(user):
    """Create default achievements for new celebrities"""
    profile = user.celebrity_profile
    
    achievements_data = [
        # Followers milestones
        {
            'title': 'First Fan',
            'description': 'Get your first follower',
            'icon': 'bx bx-user-plus',
            'achievement_type': 'followers',
            'threshold': 1,
            'points_reward': 10
        },
        {
            'title': 'Rising Star',
            'description': 'Reach 100 followers',
            'icon': 'bx bx-star',
            'achievement_type': 'followers',
            'threshold': 100,
            'points_reward': 50
        },
        {
            'title': 'Popular',
            'description': 'Reach 1,000 followers',
            'icon': 'bx bx-trending-up',
            'achievement_type': 'followers',
            'threshold': 1000,
            'points_reward': 100
        },
        {
            'title': 'Celebrity Status',
            'description': 'Reach 10,000 followers',
            'icon': 'bx bx-crown',
            'achievement_type': 'followers',
            'threshold': 10000,
            'points_reward': 500
        },
        # Earnings milestones
        {
            'title': 'First Dollar',
            'description': 'Earn your first dollar',
            'icon': 'bx bx-dollar',
            'achievement_type': 'earnings',
            'threshold': 1,
            'points_reward': 20
        },
        {
            'title': 'Business Minded',
            'description': 'Earn $100',
            'icon': 'bx bx-briefcase',
            'achievement_type': 'earnings',
            'threshold': 100,
            'points_reward': 100
        },
        # Posts milestones
        {
            'title': 'Content Creator',
            'description': 'Create 10 posts',
            'icon': 'bx bx-edit',
            'achievement_type': 'posts',
            'threshold': 10,
            'points_reward': 30
        },
        {
            'title': 'Prolific',
            'description': 'Create 100 posts',
            'icon': 'bx bx-book',
            'achievement_type': 'posts',
            'threshold': 100,
            'points_reward': 150
        },
    ]
    
    for data in achievements_data:
        CelebrityAchievement.objects.get_or_create(
            celebrity=user,
            achievement_type=data['achievement_type'],
            threshold=data['threshold'],
            defaults=data
        )


@receiver(pre_save, sender=Subscription)
def handle_subscription_expiry(sender, instance, **kwargs):
    """Check and update subscription status"""
    if instance.pk:
        if instance.status == 'active' and timezone.now() > instance.end_date:
            instance.status = 'expired'