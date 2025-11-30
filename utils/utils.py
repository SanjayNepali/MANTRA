# utils/utils.py

import json
import logging
import hashlib
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q, F, Count, Avg
import requests


logger = logging.getLogger(__name__)


class PointsManager:
    """Centralized points management system"""
    
    @staticmethod
    def award_points(user, action, related_object=None):
        """Award points based on action"""
        points_config = settings.MANTRA_SETTINGS['POINTS_RULES']
        
        if action not in points_config:
            return False
            
        points = points_config[action]
        reason_map = {
            'post_create': 'Created a new post',
            'post_like': 'Liked a post',
            'post_comment': 'Commented on a post',
            'follow': 'Followed someone',
            'subscription': 'Subscribed to exclusive content',
            'event_booking': 'Booked an event',
            'merchandise_purchase': 'Purchased merchandise',
        }
        
        reason = reason_map.get(action, action)
        user.add_points(points, reason)
        
        # Send notification
        from utils.helpers import send_notification
        send_notification(
            user,
            'points_earned',
            'Points Earned!',
            f'You earned {points} points for: {reason}'
        )
        
        return True
    
    @staticmethod
    def deduct_points(user, action, amount=None):
        """Deduct points for violations or purchases"""
        points_config = settings.MANTRA_SETTINGS['POINTS_RULES']
        
        if amount:
            points = amount
        else:
            points = abs(points_config.get(action, 0))
        
        reason_map = {
            'violation_minor': 'Minor policy violation',
            'violation_major': 'Major policy violation',
        }
        
        reason = reason_map.get(action, action)
        success = user.deduct_points(points, reason)
        
        if success:
            from utils.helpers import send_notification
            send_notification(
                user,
                'points_deducted',
                'Points Deducted',
                f'{points} points were deducted for: {reason}'
            )
        
        return success


class CacheManager:
    """Manage caching for various data"""
    
    @staticmethod
    def get_or_set(key, func, timeout=3600):
        """Get from cache or set if not exists"""
        data = cache.get(key)
        
        if data is None:
            data = func()
            cache.set(key, data, timeout)
        
        return data
    
    @staticmethod
    def invalidate_pattern(pattern):
        """Invalidate all cache keys matching pattern"""
        # This is a placeholder - actual implementation depends on cache backend
        # For Redis, we could use: cache._cache.get_client().delete(*cache._cache.get_client().keys(pattern))
        pass
    
    @staticmethod
    def get_user_cache_key(user, suffix):
        """Generate consistent cache key for user data"""
        return f"user_{user.id}_{suffix}"


class ContentModerationHelper:
    """Helper for content moderation features"""
    
    @staticmethod
    def check_spam_patterns(content):
        """Check content for spam patterns"""
        import re
        
        spam_indicators = [
            (r'(buy|sell|click|visit)\s+(now|here|this)', 0.3),
            (r'(\$|€|£)\d+', 0.2),
            (r'(http|https)://[^\s]+', 0.2),
            (r'(.)\1{10,}', 0.3),  # Repeated characters
            (r'[A-Z\s]{30,}', 0.2),  # All caps
            (r'(whatsapp|telegram|viber).*\d{5,}', 0.5),
        ]
        
        spam_score = 0
        
        for pattern, score in spam_indicators:
            if re.search(pattern, content, re.IGNORECASE):
                spam_score += score
        
        return min(spam_score, 1.0)
    
    @staticmethod
    def should_auto_moderate(sentiment_scores):
        """Determine if content should be auto-moderated"""
        threshold_settings = settings.SENTIMENT_ANALYSIS
        
        if sentiment_scores.get('toxicity', 0) > threshold_settings['AUTO_DELETE_THRESHOLD']:
            return 'delete'
        elif sentiment_scores.get('toxicity', 0) > threshold_settings['WARNING_THRESHOLD']:
            return 'warning'
        elif sentiment_scores.get('spam_score', 0) > threshold_settings['SPAM_THRESHOLD']:
            return 'review'
        
        return None


class NotificationManager:
    """Manage different types of notifications"""
    
    NOTIFICATION_TYPES = {
        'follow': {
            'title': 'New Follower',
            'template': '{user} started following you'
        },
        'like': {
            'title': 'New Like',
            'template': '{user} liked your post'
        },
        'comment': {
            'title': 'New Comment',
            'template': '{user} commented on your post'
        },
        'mention': {
            'title': 'You were mentioned',
            'template': '{user} mentioned you in a post'
        },
        'event_reminder': {
            'title': 'Event Reminder',
            'template': 'Your event "{event}" starts in {time}'
        },
        'subscription': {
            'title': 'New Subscriber',
            'template': '{user} subscribed to your exclusive content'
        },
        'order': {
            'title': 'New Order',
            'template': 'You have a new order for {product}'
        },
    }
    
    @classmethod
    def create_notification(cls, recipient, notification_type, **kwargs):
        """Create a notification with proper formatting"""
        from apps.notifications.models import Notification
        from utils.helpers import send_notification
        
        if notification_type not in cls.NOTIFICATION_TYPES:
            logger.error(f"Unknown notification type: {notification_type}")
            return None
        
        config = cls.NOTIFICATION_TYPES[notification_type]
        message = config['template'].format(**kwargs)
        
        return send_notification(
            recipient,
            notification_type,
            config['title'],
            message,
            kwargs.get('related_object')
        )


class PaymentProcessor:
    """Handle payment processing for eSewa"""
    
    @staticmethod
    def initiate_esewa_payment(amount, product_id, success_url, failure_url):
        """Initiate eSewa payment"""
        from utils.helpers import generate_transaction_id
        
        transaction_id = generate_transaction_id()
        
        payment_data = {
            'amt': amount,
            'pdc': 0,
            'psc': 0,
            'txAmt': 0,
            'tAmt': amount,
            'pid': transaction_id,
            'scd': getattr(settings, 'ESEWA_MERCHANT_CODE', 'EPAYTEST'),
            'su': success_url,
            'fu': failure_url,
        }
        
        # For development, we'll simulate the payment
        # In production, this would redirect to eSewa payment gateway
        
        return {
            'transaction_id': transaction_id,
            'payment_url': 'https://uat.esewa.com.np/epay/main',
            'payment_data': payment_data,
            'qr_code': None  # Will be generated separately
        }
    
    @staticmethod
    def verify_esewa_payment(reference_id, amount):
        """Verify eSewa payment"""
        # In production, this would make API call to eSewa to verify
        # For development, we'll simulate verification
        
        verification_url = 'https://uat.esewa.com.np/epay/transrec'
        data = {
            'amt': amount,
            'rid': reference_id,
            'pid': reference_id,
            'scd': getattr(settings, 'ESEWA_MERCHANT_CODE', 'EPAYTEST')
        }
        
        # Simulated response for development
        return {
            'verified': True,
            'transaction_id': reference_id,
            'amount': amount
        }


class AnalyticsTracker:
    """Track various analytics events"""
    
    @staticmethod
    def track_event(event_name, user, properties=None):
        """Track an analytics event"""
        from apps.analytics.models import AnalyticsEvent
        
        event = AnalyticsEvent.objects.create(
            event_name=event_name,
            user=user,
            properties=properties or {},
            timestamp=timezone.now()
        )
        
        # Update real-time analytics cache
        cache_key = f'analytics_{event_name}_{timezone.now().date()}'
        count = cache.get(cache_key, 0)
        cache.set(cache_key, count + 1, 86400)  # 24 hours
        
        return event
    
    @staticmethod
    def get_user_activity_summary(user, days=30):
        """Get user activity summary"""
        from apps.analytics.models import AnalyticsEvent
        
        start_date = timezone.now() - timedelta(days=days)
        
        events = AnalyticsEvent.objects.filter(
            user=user,
            timestamp__gte=start_date
        ).values('event_name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'total_events': sum(e['count'] for e in events),
            'events_breakdown': list(events),
            'most_common_action': events[0]['event_name'] if events else None
        }


class PermissionChecker:
    """Check various permissions throughout the system"""
    
    @staticmethod
    def can_message(sender, recipient):
        """Check if sender can message recipient"""
        from apps.accounts.models import UserFollowing
        
        # Check if both users follow each other
        following = UserFollowing.objects.filter(
            follower=sender,
            following=recipient,
            is_active=True
        ).exists()
        
        followed_back = UserFollowing.objects.filter(
            follower=recipient,
            following=sender,
            is_active=True
        ).exists()
        
        return following and followed_back
    
    @staticmethod
    def can_view_exclusive_content(viewer, celebrity):
        """Check if viewer can see celebrity's exclusive content"""
        if viewer == celebrity:
            return True
            
        if hasattr(celebrity, 'celebrity_profile'):
            exclusive_fanclub = celebrity.celebrity_profile.exclusive_fanclub
            if exclusive_fanclub and viewer in exclusive_fanclub.members.all():
                # Check if subscription is active
                from apps.fanclubs.models import FanClubMembership
                membership = FanClubMembership.objects.filter(
                    fanclub=exclusive_fanclub,
                    fan=viewer,
                    is_active=True
                ).first()
                
                return membership and membership.expires_at > timezone.now()
        
        return False
    
    @staticmethod
    def can_moderate_content(user, content):
        """Check if user can moderate specific content"""
        if user.is_superuser or user.user_type == 'admin':
            return True
            
        if user.user_type == 'subadmin':
            # SubAdmins can moderate content from their assigned regions
            if hasattr(user, 'subadmin_profile'):
                content_author = getattr(content, 'author', None) or getattr(content, 'user', None)
                if content_author and content_author.country in user.subadmin_profile.assigned_countries:
                    return True
        
        return False


class RankCalculator:
    """Calculate and update user ranks"""
    
    @staticmethod
    def update_all_ranks():
        """Update ranks for all users"""
        from apps.accounts.models import User
        
        # Update fan ranks
        fans = User.objects.filter(user_type='fan')
        for fan in fans:
            fan.update_rank()
        
        # Update celebrity ranks
        celebrities = User.objects.filter(user_type='celebrity')
        for celebrity in celebrities:
            celebrity.update_rank()
        
        logger.info(f"Updated ranks for {fans.count()} fans and {celebrities.count()} celebrities")
    
    @staticmethod
    def get_rank_progress(user):
        """Get user's progress to next rank"""
        ranks = settings.MANTRA_SETTINGS[
            'FAN_RANKS' if user.user_type == 'fan' else 'CELEBRITY_RANKS'
        ]
        
        current_points = user.points
        current_rank = None
        next_rank = None
        
        for i, (code, name, min_points) in enumerate(ranks):
            if current_points >= min_points:
                current_rank = (code, name, min_points)
                if i + 1 < len(ranks):
                    next_rank = ranks[i + 1]
            else:
                break
        
        if current_rank and next_rank:
            progress = ((current_points - current_rank[2]) / 
                       (next_rank[2] - current_rank[2])) * 100
            return {
                'current_rank': current_rank[1],
                'next_rank': next_rank[1],
                'current_points': current_points,
                'points_needed': next_rank[2] - current_points,
                'progress': min(progress, 100)
            }
        
        return {
            'current_rank': current_rank[1] if current_rank else 'Unranked',
            'next_rank': None,
            'current_points': current_points,
            'points_needed': 0,
            'progress': 100
        }