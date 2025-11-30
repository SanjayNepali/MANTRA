# algorithms/engagement.py

"""
Engagement Prediction Engine
Predicts engagement metrics for posts and content
"""

import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count


class EngagementPredictor:
    """Predict engagement for posts and content"""

    def __init__(self):
        self.weights = {
            'time_of_day': 0.15,
            'day_of_week': 0.10,
            'content_length': 0.10,
            'has_media': 0.20,
            'hashtag_count': 0.10,
            'author_followers': 0.15,
            'author_avg_engagement': 0.20
        }

    def predict_engagement(self, post):
        """
        Predict engagement score for a post

        Args:
            post: Post object

        Returns:
            dict: Engagement prediction with score and breakdown
        """
        try:
            score_breakdown = {}
            total_score = 0

            # Time of day score (peak hours: 6-9 AM, 12-2 PM, 7-10 PM)
            time_score = self._calculate_time_score(post.created_at)
            score_breakdown['time_of_day'] = time_score
            total_score += time_score * self.weights['time_of_day']

            # Day of week score (weekends typically higher engagement)
            day_score = self._calculate_day_score(post.created_at)
            score_breakdown['day_of_week'] = day_score
            total_score += day_score * self.weights['day_of_week']

            # Content length score (optimal 100-300 characters)
            length_score = self._calculate_length_score(post.content)
            score_breakdown['content_length'] = length_score
            total_score += length_score * self.weights['content_length']

            # Media presence score
            has_media = bool(post.image or post.video)
            media_score = 1.0 if has_media else 0.3
            score_breakdown['has_media'] = media_score
            total_score += media_score * self.weights['has_media']

            # Hashtag count score (optimal 3-5 hashtags)
            hashtag_score = self._calculate_hashtag_score(post.content)
            score_breakdown['hashtag_count'] = hashtag_score
            total_score += hashtag_score * self.weights['hashtag_count']

            # Author followers score
            followers_score = self._calculate_followers_score(post.author)
            score_breakdown['author_followers'] = followers_score
            total_score += followers_score * self.weights['author_followers']

            # Author average engagement score
            avg_engagement_score = self._calculate_author_engagement_score(post.author)
            score_breakdown['author_avg_engagement'] = avg_engagement_score
            total_score += avg_engagement_score * self.weights['author_avg_engagement']

            # Normalize to 0-100 scale
            total_score = min(100, max(0, total_score * 100))

            # Generate engagement estimate
            engagement_estimate = self._estimate_engagement_metrics(
                total_score,
                post.author
            )

            return {
                'score': round(total_score, 2),
                'rating': self._get_rating(total_score),
                'breakdown': score_breakdown,
                'estimate': engagement_estimate,
                'recommendations': self._generate_recommendations(score_breakdown)
            }

        except Exception as e:
            print(f"Error predicting engagement: {e}")
            return {
                'score': 50.0,
                'rating': 'moderate',
                'breakdown': {},
                'estimate': {},
                'recommendations': []
            }

    def _calculate_time_score(self, timestamp):
        """Calculate score based on time of day"""
        hour = timestamp.hour

        # Peak times
        if 6 <= hour <= 9 or 12 <= hour <= 14 or 19 <= hour <= 22:
            return 1.0
        # Good times
        elif 9 <= hour <= 12 or 14 <= hour <= 19:
            return 0.7
        # Off-peak times
        else:
            return 0.4

    def _calculate_day_score(self, timestamp):
        """Calculate score based on day of week"""
        day = timestamp.weekday()

        # Weekend (Saturday=5, Sunday=6)
        if day >= 5:
            return 1.0
        # Friday
        elif day == 4:
            return 0.9
        # Monday-Thursday
        else:
            return 0.7

    def _calculate_length_score(self, content):
        """Calculate score based on content length"""
        length = len(content)

        if 100 <= length <= 300:
            return 1.0
        elif 50 <= length < 100 or 300 < length <= 500:
            return 0.7
        elif length < 50:
            return 0.4
        else:
            return 0.5

    def _calculate_hashtag_score(self, content):
        """Calculate score based on hashtag count"""
        hashtag_count = content.count('#')

        if 3 <= hashtag_count <= 5:
            return 1.0
        elif 1 <= hashtag_count <= 2 or 6 <= hashtag_count <= 8:
            return 0.7
        elif hashtag_count == 0:
            return 0.3
        else:
            return 0.4

    def _calculate_followers_score(self, author):
        """Calculate score based on author's follower count"""
        try:
            follower_count = author.followers.count()

            if follower_count >= 10000:
                return 1.0
            elif follower_count >= 5000:
                return 0.9
            elif follower_count >= 1000:
                return 0.7
            elif follower_count >= 100:
                return 0.5
            else:
                return 0.3
        except:
            return 0.5

    def _calculate_author_engagement_score(self, author):
        """Calculate score based on author's historical engagement"""
        try:
            from apps.posts.models import Post

            # Get author's recent posts
            recent_posts = Post.objects.filter(
                author=author,
                is_active=True,
                created_at__gte=timezone.now() - timedelta(days=30)
            )

            if not recent_posts.exists():
                return 0.5

            # Calculate average engagement rate
            avg_metrics = recent_posts.aggregate(
                avg_likes=Avg('likes_count'),
                avg_comments=Avg('comments_count'),
                avg_shares=Avg('shares_count')
            )

            avg_engagement = (
                (avg_metrics['avg_likes'] or 0) +
                (avg_metrics['avg_comments'] or 0) * 2 +  # Comments weighted higher
                (avg_metrics['avg_shares'] or 0) * 3      # Shares weighted highest
            )

            # Normalize based on typical engagement
            if avg_engagement >= 500:
                return 1.0
            elif avg_engagement >= 200:
                return 0.8
            elif avg_engagement >= 100:
                return 0.6
            elif avg_engagement >= 50:
                return 0.4
            else:
                return 0.3
        except:
            return 0.5

    def _estimate_engagement_metrics(self, score, author):
        """Estimate engagement metrics based on score"""
        try:
            from apps.posts.models import Post

            # Get baseline from author's recent posts
            recent_posts = Post.objects.filter(
                author=author,
                is_active=True,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).aggregate(
                avg_likes=Avg('likes_count'),
                avg_comments=Avg('comments_count'),
                avg_shares=Avg('shares_count')
            )

            baseline_likes = recent_posts['avg_likes'] or 10
            baseline_comments = recent_posts['avg_comments'] or 2
            baseline_shares = recent_posts['avg_shares'] or 1

            # Apply score multiplier
            multiplier = score / 50  # 50 is average score

            return {
                'likes': int(baseline_likes * multiplier),
                'comments': int(baseline_comments * multiplier),
                'shares': int(baseline_shares * multiplier),
                'reach': int((baseline_likes * 10) * multiplier)
            }
        except:
            return {
                'likes': int(score * 2),
                'comments': int(score * 0.4),
                'shares': int(score * 0.2),
                'reach': int(score * 20)
            }

    def _get_rating(self, score):
        """Get text rating from score"""
        if score >= 80:
            return 'excellent'
        elif score >= 65:
            return 'good'
        elif score >= 50:
            return 'moderate'
        elif score >= 35:
            return 'low'
        else:
            return 'poor'

    def _generate_recommendations(self, breakdown):
        """Generate recommendations based on score breakdown"""
        recommendations = []

        if breakdown.get('time_of_day', 0) < 0.7:
            recommendations.append({
                'type': 'timing',
                'message': 'Post during peak hours (6-9 AM, 12-2 PM, or 7-10 PM) for better engagement',
                'priority': 'high'
            })

        if breakdown.get('day_of_week', 0) < 0.7:
            recommendations.append({
                'type': 'timing',
                'message': 'Weekend posts typically get higher engagement',
                'priority': 'medium'
            })

        if breakdown.get('content_length', 0) < 0.7:
            recommendations.append({
                'type': 'content',
                'message': 'Aim for 100-300 characters for optimal engagement',
                'priority': 'high'
            })

        if breakdown.get('has_media', 0) < 0.7:
            recommendations.append({
                'type': 'content',
                'message': 'Add images or videos to increase engagement',
                'priority': 'high'
            })

        if breakdown.get('hashtag_count', 0) < 0.7:
            recommendations.append({
                'type': 'content',
                'message': 'Use 3-5 relevant hashtags for better discoverability',
                'priority': 'medium'
            })

        return recommendations

    def predict_best_time_to_post(self, author):
        """
        Predict best time to post for given author

        Args:
            author: User object

        Returns:
            dict: Best posting times with scores
        """
        try:
            from apps.posts.models import Post

            # Analyze author's historical posts
            posts = Post.objects.filter(
                author=author,
                is_active=True,
                created_at__gte=timezone.now() - timedelta(days=90)
            ).order_by('-created_at')

            if not posts.exists():
                # Default recommendations
                return {
                    'best_times': [
                        {'time': '08:00', 'day': 'weekday', 'score': 85},
                        {'time': '13:00', 'day': 'weekday', 'score': 80},
                        {'time': '20:00', 'day': 'weekend', 'score': 90}
                    ]
                }

            # Analyze engagement by time
            time_engagement = {}
            for post in posts:
                hour = post.created_at.hour
                engagement = (
                    post.likes_count +
                    post.comments_count * 2 +
                    post.shares_count * 3
                )

                if hour not in time_engagement:
                    time_engagement[hour] = []
                time_engagement[hour].append(engagement)

            # Calculate average engagement per hour
            hour_scores = {}
            for hour, engagements in time_engagement.items():
                avg_engagement = np.mean(engagements)
                hour_scores[hour] = avg_engagement

            # Get top 3 hours
            top_hours = sorted(hour_scores.items(), key=lambda x: x[1], reverse=True)[:3]

            best_times = []
            for hour, score in top_hours:
                best_times.append({
                    'time': f'{hour:02d}:00',
                    'day': 'weekend' if hour >= 19 or hour <= 9 else 'weekday',
                    'score': min(100, int(score / 10))
                })

            return {'best_times': best_times}

        except Exception as e:
            print(f"Error predicting best time: {e}")
            return {
                'best_times': [
                    {'time': '08:00', 'day': 'weekday', 'score': 85},
                    {'time': '13:00', 'day': 'weekday', 'score': 80},
                    {'time': '20:00', 'day': 'weekend', 'score': 90}
                ]
            }
