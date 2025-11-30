# utils/helpers.py

import os
import random
import string
import hashlib
import hmac
import base64
import qrcode
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
from django.core.cache import cache
from django.db.models import Q, Count, Avg, Sum


def generate_unique_id(prefix='', length=12):
    """Generate a unique ID with optional prefix"""
    chars = string.ascii_letters + string.digits
    unique_id = ''.join(random.choice(chars) for _ in range(length))
    
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def generate_transaction_id():
    """Generate unique transaction ID for payments"""
    timestamp = timezone.now().strftime('%y%m%d-%H%M%S')
    return timestamp


def generate_esewa_signature(message, secret_key):
    """
    Generate HMAC SHA256 signature for eSewa v2 API

    Args:
        message (str): Message to sign (e.g., "total_amount=100,transaction_uuid=123,product_code=EPAYTEST")
        secret_key (str): eSewa secret key

    Returns:
        str: Base64 encoded signature

    Example:
        >>> generate_esewa_signature("total_amount=100,transaction_uuid=11-201-13,product_code=EPAYTEST", "8gBm/:&EnhH.1/q")
        '4Ov7pCI1zIOdwtV2BRMUNjz1upIlT/COTxfLhWvVurE='
    """
    # Create HMAC-SHA256 hash
    message_bytes = message.encode('utf-8')
    secret_bytes = secret_key.encode('utf-8')

    signature = hmac.new(secret_bytes, message_bytes, hashlib.sha256).digest()

    # Convert to base64
    signature_base64 = base64.b64encode(signature).decode('utf-8')

    return signature_base64


def generate_esewa_qr(payment_data):
    """Generate eSewa payment QR code"""
    # eSewa QR format
    qr_data = f"esewa://?amt={payment_data['amt']}&pid={payment_data['pid']}&scd={payment_data['scd']}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    import base64
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def calculate_engagement_rate(user, period_days=30):
    """Calculate user engagement rate"""
    from apps.posts.models import Post, Like, Comment
    
    start_date = timezone.now() - timedelta(days=period_days)
    
    if user.user_type == 'celebrity':
        posts = Post.objects.filter(author=user, created_at__gte=start_date)
        total_posts = posts.count()
        
        if total_posts == 0:
            return 0.0
            
        total_likes = posts.aggregate(Sum('likes_count'))['likes_count__sum'] or 0
        total_comments = posts.aggregate(Sum('comments_count'))['comments_count__sum'] or 0
        total_views = posts.aggregate(Sum('views_count'))['views_count__sum'] or 0
        
        # Engagement rate formula: ((likes + comments) / views) * 100
        total_engagement = total_likes + total_comments
        
        if total_views > 0:
            engagement_rate = (total_engagement / total_views) * 100
        else:
            engagement_rate = 0.0
            
    else:  # Fan engagement
        likes_given = Like.objects.filter(user=user, created_at__gte=start_date).count()
        comments_made = Comment.objects.filter(author=user, created_at__gte=start_date).count()
        posts_created = Post.objects.filter(author=user, created_at__gte=start_date).count()
        
        total_actions = likes_given + comments_made + posts_created
        days_active = (timezone.now() - user.date_joined).days or 1
        
        # Fan engagement rate: actions per day
        engagement_rate = total_actions / min(days_active, period_days)
    
    return round(engagement_rate, 2)


def get_trending_hashtags(limit=10, hours=24):
    """Get trending hashtags from recent posts"""
    from apps.posts.models import Post
    
    cache_key = f'trending_hashtags_{hours}_{limit}'
    cached = cache.get(cache_key)
    
    if cached:
        return cached
    
    start_time = timezone.now() - timedelta(hours=hours)
    
    # Extract hashtags from recent posts
    recent_posts = Post.objects.filter(
        created_at__gte=start_time,
        is_active=True
    ).values_list('content', flat=True)
    
    hashtag_counter = {}
    
    for content in recent_posts:
        # Find all hashtags in content
        import re
        hashtags = re.findall(r'#\w+', content)
        
        for tag in hashtags:
            tag_lower = tag.lower()
            hashtag_counter[tag_lower] = hashtag_counter.get(tag_lower, 0) + 1
    
    # Sort by frequency
    trending = sorted(hashtag_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    result = [{'tag': tag, 'count': count} for tag, count in trending]
    
    # Cache for 1 hour
    cache.set(cache_key, result, 3600)
    
    return result


def get_user_statistics(user):
    """Get comprehensive statistics for a user"""
    from apps.posts.models import Post, Like
    from apps.accounts.models import UserFollowing
    from apps.events.models import EventBooking
    from apps.merchandise.models import Order
    
    stats = {
        'total_posts': 0,
        'total_likes_received': 0,
        'total_likes_given': 0,
        'total_followers': 0,
        'total_following': 0,
        'engagement_rate': 0,
        'rank': user.rank,
        'points': user.points,
    }
    
    # Posts and likes
    if user.user_type in ['celebrity', 'fan']:
        user_posts = Post.objects.filter(author=user, is_active=True)
        stats['total_posts'] = user_posts.count()
        stats['total_likes_received'] = user_posts.aggregate(Sum('likes_count'))['likes_count__sum'] or 0
        stats['total_likes_given'] = Like.objects.filter(user=user).count()
    
    # Follow statistics
    stats['total_followers'] = UserFollowing.objects.filter(following=user, is_active=True).count()
    stats['total_following'] = UserFollowing.objects.filter(follower=user, is_active=True).count()
    
    # Celebrity-specific stats
    if user.user_type == 'celebrity' and hasattr(user, 'celebrity_profile'):
        stats['total_events'] = user.events_created.filter(is_active=True).count()
        stats['total_merchandise'] = user.merchandise_created.filter(is_active=True).count()
        stats['total_bookings'] = EventBooking.objects.filter(
            event__celebrity=user,
            payment_status='completed'
        ).count()
        stats['total_orders'] = Order.objects.filter(
            items__product__seller=user,
            payment_status='completed'
        ).distinct().count()
        
        # Subscription stats
        if hasattr(user.celebrity_profile, 'exclusive_fanclub'):
            stats['total_subscribers'] = user.celebrity_profile.exclusive_fanclub.members.count()
    
    # Calculate engagement rate
    stats['engagement_rate'] = calculate_engagement_rate(user)
    
    return stats


def format_number(num):
    """Format large numbers with K, M suffixes"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)


def generate_slug(text, model_class=None, slug_field='slug'):
    """Generate unique slug for a model"""
    slug = slugify(text)
    
    if model_class is None:
        return slug
    
    # Check if slug exists
    original_slug = slug
    counter = 1
    
    while model_class.objects.filter(**{slug_field: slug}).exists():
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    return slug


def resize_image(image, max_width=800, max_height=800, quality=85):
    """Resize image maintaining aspect ratio"""
    img = Image.open(image)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Calculate new dimensions
    width, height = img.size
    
    if width > max_width or height > max_height:
        ratio = min(max_width / width, max_height / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Save to BytesIO
    output = BytesIO()
    img.save(output, format='JPEG', quality=quality)
    output.seek(0)
    
    return ContentFile(output.getvalue())


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def send_notification(user, notification_type, title, message, related_object=None):
    """Send notification to user"""
    from apps.notifications.models import Notification
    
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_type=related_object.__class__.__name__ if related_object else None,
        related_object_id=related_object.id if related_object else None
    )
    
    # Send real-time notification via WebSocket
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user.id}',
        {
            'type': 'notification_message',
            'notification': {
                'id': str(notification.id),
                'title': title,
                'message': message,
                'type': notification_type,
                'created_at': notification.created_at.isoformat()
            }
        }
    )
    
    return notification


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = R * c
    return round(distance, 2)


def get_date_range(period):
    """Get start and end date for different periods"""
    today = timezone.now().date()
    
    if period == 'today':
        return today, today
    elif period == 'week':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end
    elif period == 'month':
        start = today.replace(day=1)
        next_month = start + timedelta(days=32)
        end = next_month.replace(day=1) - timedelta(days=1)
        return start, end
    elif period == 'year':
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
        return start, end
    else:
        # Default to last 30 days
        return today - timedelta(days=30), today