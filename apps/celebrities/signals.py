# apps/celebrities/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction  # ADD THIS
from apps.accounts.models import User
from .models import CelebrityProfile, Subscription, CelebrityAchievement


@receiver(post_save, sender=User)
def create_celebrity_profile(sender, instance, created, **kwargs):
    """Create celebrity profile when celebrity user is created"""
    if created and instance.user_type == 'celebrity':
        with transaction.atomic():  # ADD TRANSACTION
            profile, _ = CelebrityProfile.objects.get_or_create(
                user=instance,
                defaults={'categories': [instance.category] if hasattr(instance, 'category') else []}
            )
            
            # Create default achievements
            create_default_achievements(instance)
            
            # Create official fanclub automatically
            create_official_fanclub(instance)


def create_official_fanclub(user):
    """Create official fanclub for celebrity - DUPLICATE PREVENTION"""
    from apps.fanclubs.models import FanClub, FanClubMembership
    
    # Check if official fanclub already exists
    existing_official = FanClub.objects.filter(
        celebrity=user,
        is_official=True
    ).first()
    
    if existing_official:
        return existing_official
    
    # Check by slug pattern too (extra safety)
    base_slug = slugify(f"{user.username}-official-fan-club")
    existing_by_slug = FanClub.objects.filter(
        celebrity=user,
        slug__startswith=base_slug
    ).first()
    
    if existing_by_slug:
        if not existing_by_slug.is_official:
            existing_by_slug.is_official = True
            existing_by_slug.save(update_fields=['is_official'])
        return existing_by_slug
    
    # Use transaction with select_for_update to prevent race conditions
    with transaction.atomic():
        # Double-check with row lock to prevent concurrent creation
        existing_check = FanClub.objects.select_for_update().filter(
            celebrity=user,
            is_official=True
        ).first()
        
        if existing_check:
            return existing_check
        
        fanclub_name = f"{user.get_full_name() or user.username}'s Official Fan Club"
        fanclub_slug = slugify(f"{user.username}-official-fan-club")
        
        # Ensure unique slug
        counter = 1
        original_slug = fanclub_slug
        while FanClub.objects.filter(slug=fanclub_slug).exists():
            fanclub_slug = f"{original_slug}-{counter}"
            counter += 1
        
        fanclub = FanClub.objects.create(
            celebrity=user,
            name=fanclub_name,
            slug=fanclub_slug,
            description=f"Official fan club for {user.get_full_name() or user.username}. Join to get exclusive updates and connect with other fans!",
            welcome_message=f"Welcome to {user.get_full_name() or user.username}'s official fan club! 🎉",
            club_type='default',
            is_official=True,
            is_active=True,
            is_private=False,
            visibility='public',
            requires_approval=False,
            allow_member_posts=False,  # Only celebrity can post
            allow_member_invites=True
        )
        
        # Auto-join celebrity as admin
        FanClubMembership.objects.create(
            user=user,
            fanclub=fanclub,
            role='admin',
            status='active'
        )
        
        return fanclub


def create_default_achievements(user):
    """Create default achievements for new celebrities"""
    achievements_data = [
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