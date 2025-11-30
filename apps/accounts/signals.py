# apps/accounts/signals.py

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import User, UserFollowing, UserPreferences

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Create user preferences when a new user is created"""
    if created:
        UserPreferences.objects.get_or_create(user=instance)


@receiver(pre_save, sender=User)
def update_user_rank(sender, instance, **kwargs):
    """Update user rank before saving if points changed"""
    if instance.pk:
        try:
            old_user = User.objects.get(pk=instance.pk)
            if old_user.points != instance.points:
                # Points changed, update rank
                from django.conf import settings
                
                if instance.user_type == 'fan':
                    ranks = settings.MANTRA_SETTINGS['FAN_RANKS']
                elif instance.user_type == 'celebrity':
                    ranks = settings.MANTRA_SETTINGS['CELEBRITY_RANKS']
                else:
                    return
                
                for rank_code, rank_name, min_points in reversed(ranks):
                    if instance.points >= min_points:
                        instance.rank = rank_name
                        break
        except User.DoesNotExist:
            pass


@receiver(post_save, sender=UserFollowing)
def handle_new_follow(sender, instance, created, **kwargs):
    """Handle actions when a new follow occurs"""
    if created:
        # Create notification for the followed user
        from apps.notifications.models import Notification
        Notification.objects.create(
            recipient=instance.following,
            sender=instance.follower,
            notification_type='follow',
            message=f'{instance.follower.username} started following you'
        )

        # Update follower/following counts
        update_follow_counts(instance.follower, instance.following)


@receiver(post_delete, sender=UserFollowing)
def handle_unfollow(sender, instance, **kwargs):
    """Handle actions when an unfollow occurs"""
    # Update follower/following counts after unfollow
    update_follow_counts(instance.follower, instance.following)


def update_follow_counts(follower, following):
    """Update follower and following counts for both users"""
    # Update following user's total_followers
    following.total_followers = following.followers.count()
    following.save(update_fields=['total_followers'])


@receiver(post_save, sender=User)
def create_default_fanclub_for_celebrity(sender, instance, created, **kwargs):
    """Create a default official fanclub when a celebrity user is created"""
    if created and instance.user_type == 'celebrity':
        # Import here to avoid circular imports
        from apps.fanclubs.models import FanClub
        from django.utils.text import slugify

        # Create default official fanclub
        fanclub_name = f"{instance.username}'s Official Fanclub"
        fanclub_description = f"Welcome to the official fanclub for {instance.get_full_name() or instance.username}!"

        FanClub.objects.get_or_create(
            celebrity=instance,
            is_official=True,
            defaults={
                'name': fanclub_name,
                'slug': slugify(fanclub_name),
                'description': fanclub_description,
                'club_type': 'official',
                'is_active': True,
                'is_private': False,
            }
        )