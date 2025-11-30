# apps/celebrities/utils.py
"""
Utility functions for celebrity management
"""

from django.utils.text import slugify


def get_or_create_default_fanclub(celebrity_user):
    """
    Get or create the default fanclub for a celebrity.
    Every celebrity automatically gets a default fanclub when their account is created.
    """
    from apps.fanclubs.models import FanClub

    # Try to get existing default fanclub
    fanclub = FanClub.objects.filter(
        celebrity=celebrity_user,
        club_type='default',
        is_official=True
    ).first()

    if not fanclub:
        # Create default fanclub
        celebrity_name = celebrity_user.get_full_name() or celebrity_user.username
        fanclub = FanClub.objects.create(
            celebrity=celebrity_user,
            name=f"{celebrity_name} Official Fan Club",
            description=f"Welcome to the official fan club of {celebrity_name}! Join to connect with other fans and get exclusive updates.",
            welcome_message=f"Welcome to {celebrity_name}'s official fan club! We're excited to have you here.",
            club_type='default',
            is_official=True,
            is_active=True,
            visibility='public',
            requires_approval=False,
            allow_member_posts=True,
            allow_member_invites=True,
        )

        # Add the celebrity as the first member
        fanclub.add_member(celebrity_user)

    return fanclub


def ensure_celebrity_has_fanclub(celebrity_user):
    """
    Ensure celebrity has a default fanclub.
    Can be called during signup or profile setup.
    """
    if celebrity_user.user_type == 'celebrity':
        return get_or_create_default_fanclub(celebrity_user)
    return None
