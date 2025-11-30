# apps/posts/api_views.py - AJAX endpoints with algorithm integration

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

from apps.posts.models import Post, Comment
from apps.accounts.models import User


@login_required
@require_http_methods(["POST"])
def analyze_content_api(request):
    """
    API endpoint to analyze post content before publishing
    Returns sentiment, engagement prediction, and content warnings
    """
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'error': 'Content is required'
            }, status=400)
        
        # Import analysis modules
        from algorithms.sentiment import SentimentAnalyzer, EngagementPredictor
        from algorithms.integration import moderate_post_content
        
        analyzer = SentimentAnalyzer()
        predictor = EngagementPredictor()
        
        # Get comprehensive analysis
        insights = analyzer.get_content_insights(content)
        
        # Get author stats for engagement prediction
        author_stats = {
            'followers_count': request.user.followers.count() if hasattr(request.user, 'followers') else 0
        }
        engagement = predictor.predict_post_engagement(content, author_stats)
        
        # Get moderation result
        moderation = moderate_post_content(content)
        
        # Calculate readability score (simple version)
        words = len(content.split())
        sentences = content.count('.') + content.count('!') + content.count('?')
        readability = "Excellent" if 50 <= words <= 150 else "Good" if words < 200 else "Too Long"
        
        return JsonResponse({
            'success': True,
            'sentiment': {
                'label': insights['sentiment']['label'],
                'score': insights['sentiment']['score'],
                'confidence': insights['sentiment']['confidence']
            },
            'toxicity': {
                'is_toxic': insights['toxicity']['is_toxic'],
                'score': insights['toxicity']['toxicity_score'],
                'severity': insights['toxicity']['severity'],
                'toxic_words': insights['toxicity']['toxic_words']
            },
            'spam': {
                'is_spam': insights['spam']['is_spam'],
                'score': insights['spam']['spam_score'],
                'indicators': insights['spam']['spam_indicators']
            },
            'emotions': {
                'primary': insights['emotions']['primary_emotion'],
                'all': insights['emotions']['all_emotions']
            },
            'engagement': {
                'engagement_score': round(engagement['engagement_score']),
                'predicted_likes': engagement['predicted_likes'],
                'predicted_comments': engagement['predicted_comments'],
                'viral_potential': round(engagement['viral_potential'] * 100)
            },
            'moderation': {
                'should_block': moderation['should_block'],
                'reason': moderation['reason'] if moderation['should_block'] else None
            },
            'readability': readability,
            'word_count': words,
            'character_count': len(content)
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_suggested_users_api(request):
    """
    Get suggested users to follow based on user interests
    Uses MatchingEngine algorithm
    """
    try:
        from algorithms.matching import MatchingEngine
        from apps.accounts.models import UserFollowing
        
        matcher = MatchingEngine()
        
        # Get users to recommend
        if request.user.user_type == 'fan':
            # Suggest celebrities
            suggestions = matcher.match_fan_to_celebrity(request.user, limit=5)
            
            users_data = []
            for celebrity_profile, score in suggestions:
                user = celebrity_profile.user
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'name': user.get_full_name(),
                    'avatar': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else '/static/images/default-avatar.png',
                    'is_verified': celebrity_profile.is_verified,
                    'followers_count': user.followers.count() if hasattr(user, 'followers') else 0,
                    'match_score': round(score, 2),
                    'categories': celebrity_profile.categories or []
                })
        else:
            # Suggest similar users
            suggestions = matcher.find_compatible_users(request.user, limit=5)
            
            users_data = []
            for user, score in suggestions:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'name': user.get_full_name(),
                    'avatar': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else '/static/images/default-avatar.png',
                    'is_verified': hasattr(user, 'celebrity_profile') and user.celebrity_profile.is_verified,
                    'followers_count': user.followers.count() if hasattr(user, 'followers') else 0,
                    'match_score': round(score, 2)
                })
        
        return JsonResponse({
            'success': True,
            'users': users_data
        })
        
    except ImportError:
        # Fallback: return popular users
        from apps.accounts.models import User
        
        popular_users = User.objects.filter(
            is_active=True,
            user_type='celebrity'
        ).exclude(
            id=request.user.id
        ).order_by('-followers_count')[:5]
        
        users_data = [{
            'id': user.id,
            'username': user.username,
            'name': user.get_full_name(),
            'avatar': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else '/static/images/default-avatar.png',
            'is_verified': hasattr(user, 'celebrity_profile') and user.celebrity_profile.is_verified,
            'followers_count': user.followers.count() if hasattr(user, 'followers') else 0
        } for user in popular_users]
        
        return JsonResponse({
            'success': True,
            'users': users_data
        })


@login_required
@require_http_methods(["GET"])
def get_trending_hashtags_api(request):
    """
    Get trending hashtags using TrendingEngine
    """
    try:
        from algorithms.recommendation import TrendingEngine
        
        days = int(request.GET.get('days', 7))
        limit = int(request.GET.get('limit', 20))
        
        trending = TrendingEngine.calculate_trending_hashtags(days=days, limit=limit)
        
        return JsonResponse({
            'success': True,
            'hashtags': trending
        })
        
    except ImportError:
        # Fallback: return common hashtags
        return JsonResponse({
            'success': True,
            'hashtags': [
                {'hashtag': '#mantra', 'count': 1250},
                {'hashtag': '#celebrity', 'count': 890},
                {'hashtag': '#fanclub', 'count': 678}
            ]
        })


@login_required
@require_http_methods(["POST"])
def get_post_recommendations_api(request):
    """
    Get personalized post recommendations
    """
    try:
        data = json.loads(request.body)
        filter_type = data.get('filter', 'all')
        page = int(data.get('page', 1))
        per_page = int(data.get('per_page', 10))
        
        from algorithms.recommendation import RecommendationEngine
        
        engine = RecommendationEngine()
        
        if filter_type == 'collaborative':
            # Use collaborative filtering
            posts = engine.get_collaborative_filtering_recommendations(
                request.user,
                item_type='post',
                limit=per_page
            )
        else:
            # Use content-based recommendations
            recommendations = engine.get_user_recommendations(
                request.user,
                recommendation_type='posts',
                limit=per_page
            )
            posts = recommendations.get('posts', [])
        
        posts_data = [{
            'id': str(post.id),
            'content': post.content[:200],
            'author': {
                'username': post.author.username,
                'name': post.author.get_full_name(),
                'avatar': post.author.profile.avatar.url if hasattr(post.author, 'profile') and post.author.profile.avatar else '/static/images/default-avatar.png',
                'is_verified': hasattr(post.author, 'celebrity_profile') and post.author.celebrity_profile.is_verified
            },
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'created_at': post.created_at.isoformat(),
            'image': post.image.url if post.image else None,
            'tags': post.tags or []
        } for post in posts]
        
        return JsonResponse({
            'success': True,
            'posts': posts_data,
            'page': page,
            'has_more': len(posts) == per_page
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def calculate_engagement_prediction_api(request):
    """
    Calculate predicted engagement for a draft post
    """
    try:
        data = json.loads(request.body)
        content = data.get('content', '')
        
        if not content:
            return JsonResponse({
                'error': 'Content is required'
            }, status=400)
        
        from algorithms.sentiment import EngagementPredictor
        
        predictor = EngagementPredictor()
        
        # Get author stats
        author_stats = {
            'followers_count': request.user.followers.count() if hasattr(request.user, 'followers') else 0,
            'avg_likes': 50,  # You can calculate actual average
            'avg_comments': 10
        }
        
        prediction = predictor.predict_post_engagement(content, author_stats)
        
        # Get hashtag effectiveness
        hashtags = [tag.strip('#') for tag in content.split() if tag.startswith('#')]
        hashtag_analysis = predictor.analyze_hashtag_effectiveness(hashtags)
        
        # Get best posting time
        posting_time = predictor.suggest_best_posting_time()
        
        return JsonResponse({
            'success': True,
            'prediction': {
                'likes': prediction['predicted_likes'],
                'comments': prediction['predicted_comments'],
                'shares': prediction['predicted_shares'],
                'engagement_score': round(prediction['engagement_score']),
                'viral_potential': round(prediction['viral_potential'] * 100)
            },
            'hashtags': hashtag_analysis,
            'best_posting_time': posting_time,
            'recommendations': [
                f"Expected {prediction['predicted_likes']} likes",
                f"Viral potential: {round(prediction['viral_potential'] * 100)}%",
                f"Best time to post: {', '.join([f'{h}:00' for h in posting_time['recommended_hours']])}"
            ]
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def check_similar_posts_api(request):
    """
    Check for similar existing posts to avoid duplicates
    """
    try:
        data = json.loads(request.body)
        content = data.get('content', '')
        
        if not content:
            return JsonResponse({
                'error': 'Content is required'
            }, status=400)
        
        from algorithms.string_matching import StringMatcher
        
        # Get recent posts from user
        recent_posts = Post.objects.filter(
            author=request.user,
            is_active=True
        ).order_by('-created_at')[:50]
        
        # Find similar posts
        similar = StringMatcher.search_rank(
            content,
            recent_posts,
            lambda p: p.content,
            threshold=0.7
        )
        
        similar_posts = [{
            'id': str(post.id),
            'content': post.content[:100],
            'similarity': round(score * 100),
            'created_at': post.created_at.isoformat()
        } for post, score in similar[:5]]
        
        return JsonResponse({
            'success': True,
            'has_similar': len(similar_posts) > 0,
            'similar_posts': similar_posts
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_post_stats_api(request, pk):
    """
    Get detailed statistics for a post
    """
    try:
        post = Post.objects.get(pk=pk)
        
        # Calculate engagement rate
        total_engagement = post.likes_count + post.comments_count + post.shares_count
        engagement_rate = (total_engagement / max(post.views_count, 1)) * 100
        
        # Get hourly breakdown (if available)
        # This would require tracking engagement over time
        
        return JsonResponse({
            'success': True,
            'stats': {
                'views': post.views_count,
                'likes': post.likes_count,
                'comments': post.comments_count,
                'shares': post.shares_count,
                'saves': post.saves_count if hasattr(post, 'saves_count') else 0,
                'engagement_rate': round(engagement_rate, 2),
                'sentiment': {
                    'label': post.sentiment_label if hasattr(post, 'sentiment_label') else 'neutral',
                    'score': post.sentiment_score if hasattr(post, 'sentiment_score') else 0
                },
                'created_at': post.created_at.isoformat()
            }
        })
        
    except Post.DoesNotExist:
        return JsonResponse({
            'error': 'Post not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)