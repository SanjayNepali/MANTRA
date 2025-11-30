from django import template
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def profile_picture_url(user, default='images/default-avatar.png'):
    """
    Safely get user profile picture URL or return default.

    Usage: {% profile_picture_url user %}
    Usage with custom default: {% profile_picture_url user 'path/to/default.png' %}
    """
    try:
        if user and hasattr(user, 'profile_picture') and user.profile_picture:
            return user.profile_picture.url
    except (ValueError, AttributeError):
        pass

    return static(default)


@register.filter
def has_profile_picture(user):
    """
    Check if user has a profile picture.

    Usage: {% if user|has_profile_picture %}
    """
    try:
        return user and hasattr(user, 'profile_picture') and user.profile_picture and bool(user.profile_picture.name)
    except (ValueError, AttributeError):
        return False
