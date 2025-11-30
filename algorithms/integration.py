# algorithms/integration.py - Complete implementation

from .recommendation import RecommendationEngine, TrendingEngine
from .sentiment import SentimentAnalyzer, EngagementPredictor
from .matching import MatchingEngine
from .collaborative_filtering import CollaborativeFilter
from django.core.cache import cache
import hashlib


def notify_subadmin_of_flagged_content(post, flag_reason, severity):
    """
    Notify subadmins when content is flagged for review

    Args:
        post: The flagged Post object
        flag_reason: Reason for flagging
        severity: 'low', 'medium', or 'high'
    """
    try:
        from django.contrib.auth import get_user_model
        from apps.subadmin.models import Notification

        User = get_user_model()

        # Get subadmins for the user's country
        if hasattr(post.author, 'country'):
            subadmins = User.objects.filter(
                user_type='subadmin',
                country=post.author.country,
                is_active=True
            )
        else:
            # If no country, notify all subadmins
            subadmins = User.objects.filter(
                user_type='subadmin',
                is_active=True
            )

        # Create notification for each subadmin
        for subadmin in subadmins:
            Notification.objects.create(
                user=subadmin,
                notification_type='content_flagged',
                title=f"Content Flagged - {severity.upper()} Priority",
                message=f"Post by {post.author.username} has been flagged: {flag_reason}",
                link=f"/posts/{post.id}/",
                priority=severity,
                metadata={
                    'post_id': str(post.id),
                    'author_id': str(post.author.id),
                    'author_username': post.author.username,
                    'flag_reason': flag_reason,
                    'severity': severity,
                    'content_preview': post.content[:100]
                }
            )

        return True
    except Exception as e:
        # Log error but don't fail the post creation
        print(f"Error notifying subadmins: {e}")
        return False

def get_user_recommendations(user, recommendation_type='all', limit=10, use_cache=True):
    """Get cached recommendations for a user"""
    # Create cache key
    cache_key = f"recommendations_{user.id}_{recommendation_type}_{limit}"
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached
    
    # Generate fresh recommendations
    engine = RecommendationEngine()
    recommendations = engine.get_user_recommendations(user, recommendation_type, limit)
    
    # Cache for 30 minutes
    cache.set(cache_key, recommendations, 1800)
    
    return recommendations

def moderate_post_content(content):
    """Enhanced content moderation with flagging system"""
    # Hash content for cache key
    content_hash = hashlib.md5(content.encode()).hexdigest()
    cache_key = f"moderation_{content_hash}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    analyzer = SentimentAnalyzer()
    analysis = analyzer.get_content_insights(content)

    should_flag = False
    flag_reason = None
    severity = 'low'

    # Enhanced flagging rules (no longer blocking, just flagging)
    if analysis['toxicity']['is_toxic'] and analysis['toxicity']['severity'] == 'high':
        should_flag = True
        severity = 'high'
        flag_reason = f"High toxicity content detected (score: {analysis['toxicity']['toxicity_score']:.2f})"
    elif analysis['toxicity']['is_toxic'] and analysis['toxicity']['severity'] == 'medium':
        should_flag = True
        severity = 'medium'
        flag_reason = f"Moderate toxicity content detected (score: {analysis['toxicity']['toxicity_score']:.2f})"

    if analysis['spam']['is_spam'] and analysis['spam']['spam_score'] > 0.8:
        should_flag = True
        severity = 'high' if severity != 'high' else severity
        flag_reason = f"High spam score detected ({analysis['spam']['spam_score']:.2f})"

    if analysis['sentiment']['score'] < -0.8 and analysis['sentiment']['confidence'] > 0.7:
        should_flag = True
        if severity == 'low':
            severity = 'medium'
        flag_reason = f"Extremely negative content (sentiment: {analysis['sentiment']['score']:.2f})"

    # Check for repetition-based toxicity
    if analysis['toxicity'].get('total_repetitions', 0) > 10:
        should_flag = True
        severity = 'high'
        flag_reason = f"Excessive profanity repetition ({analysis['toxicity']['total_repetitions']} times)"

    result = {
        'should_block': False,  # Never block, always allow posting
        'should_flag': should_flag,
        'flag_reason': flag_reason,
        'flag_severity': severity,
        'reason': flag_reason,  # Keep for backwards compatibility
        'sentiment': analysis['sentiment']['label'],
        'toxicity_score': analysis['toxicity']['toxicity_score'],
        'spam_score': analysis['spam']['spam_score'],
        'analysis': analysis
    }

    # Cache for 1 hour
    cache.set(cache_key, result, 3600)

    return result

def calculate_user_influence_score(user):
    """Calculate influence score for celebrities"""
    if user.user_type != 'celebrity':
        return 0
    
    from apps.posts.models import Post
    from apps.accounts.models import UserFollowing
    from django.db.models import Count, Avg
    
    # Factors for influence score
    followers_count = UserFollowing.objects.filter(following=user).count()

    post_stats = Post.objects.filter(
        author=user,
        is_active=True
    ).aggregate(
        total_posts=Count('id'),
        avg_likes=Avg('likes_count'),
        avg_comments=Avg('comments_count')
    )
    
    # Calculate score (0-100)
    score = 0
    
    # Followers weight (40%)
    if followers_count > 10000:
        score += 40
    elif followers_count > 5000:
        score += 30
    elif followers_count > 1000:
        score += 20
    elif followers_count > 100:
        score += 10
    
    # Engagement weight (30%)
    avg_engagement = (post_stats['avg_likes'] or 0) + (post_stats['avg_comments'] or 0)
    if avg_engagement > 1000:
        score += 30
    elif avg_engagement > 500:
        score += 20
    elif avg_engagement > 100:
        score += 10
    
    # Activity weight (30%)
    if post_stats['total_posts'] > 100:
        score += 30
    elif post_stats['total_posts'] > 50:
        score += 20
    elif post_stats['total_posts'] > 10:
        score += 10
    
    return min(score, 100)