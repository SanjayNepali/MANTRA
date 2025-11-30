# algorithms/recommendation.py

import re
import numpy as np
from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Count, Q, F, Avg
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from apps.accounts.models import User, UserFollowing
from apps.celebrities.models import CelebrityProfile
from apps.fans.models import FanProfile
from apps.posts.models import Post, PostView, Like
from apps.events.models import Event, EventBooking
from apps.merchandise.models import Merchandise


class RecommendationEngine:
    """Advanced recommendation engine for MANTRA platform with Django integration"""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100)

    def get_user_recommendations(self, user, recommendation_type='all', limit=10):
        """
        Get personalized recommendations for a user

        Args:
            user: User object (Fan or Celebrity)
            recommendation_type: 'celebrities', 'posts', 'events', 'merchandise', 'fans', 'all'
            limit: Number of recommendations to return

        Returns:
            Dictionary with recommended items
        """
        recommendations = {}

        if user.user_type == 'fan':
            if recommendation_type in ['celebrities', 'all']:
                recommendations['celebrities'] = self._recommend_celebrities_for_fan(user, limit)
            if recommendation_type in ['posts', 'all']:
                recommendations['posts'] = self._recommend_posts_for_user(user, limit)
            if recommendation_type in ['events', 'all']:
                recommendations['events'] = self._recommend_events_for_fan(user, limit)
            if recommendation_type in ['merchandise', 'all']:
                recommendations['merchandise'] = self._recommend_merchandise_for_fan(user, limit)
            if recommendation_type in ['fans', 'all']:
                recommendations['similar_fans'] = self._recommend_similar_fans(user, limit)

        elif user.user_type == 'celebrity':
            if recommendation_type in ['fans', 'all']:
                recommendations['potential_fans'] = self._recommend_fans_for_celebrity(user, limit)

        return recommendations

    def _recommend_celebrities_for_fan(self, fan, limit=10):
        """Recommend celebrities based on fan's interests and activity"""
        try:
            fan_profile = fan.fan_profile
        except ObjectDoesNotExist:
            # If no fan profile, return popular celebrities
            return list(CelebrityProfile.objects.select_related('user').filter(
                verification_status='approved'
            ).order_by('-user__points')[:limit])

        # Get celebrities fan is already following
        following_ids = UserFollowing.objects.filter(
            follower=fan
        ).values_list('following_id', flat=True)

        # Get fan's interests
        fan_interests = set(fan_profile.interests or [])

        # Get celebrities with matching categories
        celebrities = CelebrityProfile.objects.select_related('user').exclude(
            user_id__in=following_ids
        ).filter(verification_status='approved')

        # Score celebrities based on matching interests and popularity
        scored_celebrities = []
        for celebrity in celebrities:
            score = 0

            # Match categories with fan interests
            celebrity_categories = set(celebrity.categories or [])
            matching_interests = fan_interests & celebrity_categories
            score += len(matching_interests) * 10

            # Factor in celebrity popularity
            # Count actual followers
            followers_count = UserFollowing.objects.filter(following=celebrity.user).count()
            score += followers_count / 10

            # Factor in engagement rate if available
            if hasattr(celebrity, 'engagement_rate') and celebrity.engagement_rate:
                score += celebrity.engagement_rate * 5

            scored_celebrities.append((celebrity, score))

        # Sort by score and return top N
        scored_celebrities.sort(key=lambda x: x[1], reverse=True)
        return [celeb for celeb, score in scored_celebrities[:limit]]

    def _recommend_posts_for_user(self, user, limit=10):
        """Recommend posts based on user's interests and following"""
        # Get users that this user follows
        following_ids = list(UserFollowing.objects.filter(
            follower=user
        ).values_list('following_id', flat=True))

        if not following_ids:
            # If not following anyone, return trending posts
            return list(Post.objects.filter(
                is_active=True
            ).select_related('author').order_by('-likes_count', '-created_at')[:limit])

        # Get posts from followed users
        recent_posts = Post.objects.filter(
            author_id__in=following_ids,
            is_active=True
        ).select_related('author').order_by('-created_at')[:100]

        # Get posts user has already seen/liked
        seen_post_ids = set(PostView.objects.filter(user=user).values_list('post_id', flat=True))
        liked_post_ids = set(Like.objects.filter(user=user, post__isnull=False).values_list('post_id', flat=True))
        already_interacted = seen_post_ids | liked_post_ids

        # Filter out already seen posts
        unseen_posts = [p for p in recent_posts if p.id not in already_interacted]

        if len(unseen_posts) < limit:
            # Add some trending posts to fill the gap
            trending = Post.objects.filter(
                is_active=True
            ).exclude(id__in=already_interacted).select_related('author').order_by('-likes_count')[:limit]
            unseen_posts = list(unseen_posts) + list(trending)

        # If user has fan profile with interests, use content-based filtering
        try:
            if hasattr(user, 'fan_profile') and user.fan_profile.interests:
                unseen_posts = self._score_posts_by_content(user, unseen_posts)
        except ObjectDoesNotExist:
            pass

        return unseen_posts[:limit]

    def _score_posts_by_content(self, user, posts):
        """Score posts based on content similarity with user interests"""
        if not posts:
            return []

        try:
            fan_interests = ' '.join(user.fan_profile.interests or [])
            if not fan_interests.strip():
                return sorted(posts, key=lambda p: p.likes_count, reverse=True)
                
            post_contents = [p.content or p.caption or '' for p in posts]

            # Add fan interests as first document
            all_docs = [fan_interests] + post_contents

            # Calculate TF-IDF similarity
            tfidf_matrix = self.vectorizer.fit_transform(all_docs)

            # Calculate similarity between fan interests and each post
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

            # Combine content similarity with engagement metrics
            scored_posts = []
            for i, post in enumerate(posts):
                content_score = similarities[i]
                engagement_score = (post.likes_count * 0.5 + post.comments_count * 1.0) / 100
                final_score = content_score * 0.7 + engagement_score * 0.3
                scored_posts.append((post, final_score))

            # Sort by final score
            scored_posts.sort(key=lambda x: x[1], reverse=True)
            return [post for post, score in scored_posts]

        except Exception as e:
            # If anything fails, return posts sorted by engagement
            return sorted(posts, key=lambda p: p.likes_count, reverse=True)

    def _recommend_events_for_fan(self, fan, limit=10):
        """Recommend events based on fan's interests and location"""
        now = timezone.now()
        upcoming_events = Event.objects.filter(
            start_datetime__gte=now,
            status='published'
        ).select_related('celebrity').annotate(
            attendees_count=Count('registrations')
        ).order_by('start_datetime')

        # Exclude events already booked by this fan
        registered_event_ids = EventBooking.objects.filter(
            user=fan
        ).values_list('event_id', flat=True)
        upcoming_events = upcoming_events.exclude(id__in=registered_event_ids)

        # Score events
        try:
            if hasattr(fan, 'fan_profile') and fan.fan_profile.interests:
                fan_interests = set(fan.fan_profile.interests or [])
                scored_events = []
                following_ids = set(UserFollowing.objects.filter(
                    follower=fan
                ).values_list('following_id', flat=True))

                for event in upcoming_events[:50]:
                    score = 0
                    event_categories = set(event.categories or [])
                    matching_interests = fan_interests & event_categories
                    score += len(matching_interests) * 10

                    # Factor in popularity
                    score += (event.attendees_count or 0) / 10

                    # Bonus if fan follows the event’s celebrity
                    if event.celebrity_id in following_ids:
                        score += 20

                    scored_events.append((event, score))

                scored_events.sort(key=lambda x: x[1], reverse=True)
                return [event for event, score in scored_events[:limit]]
        except ObjectDoesNotExist:
            pass

        return list(upcoming_events[:limit])


    def _recommend_merchandise_for_fan(self, fan, limit=10):
        """Recommend merchandise based on fan's interests and followed celebrities"""
        # Get celebrities fan follows
        following_ids = list(UserFollowing.objects.filter(
            follower=fan
        ).values_list('following_id', flat=True))

        # Get merchandise from followed celebrities
        if following_ids:
            merchandise = Merchandise.objects.filter(
                celebrity_id__in=following_ids,
                status='available',
                stock_quantity__gt=0
            ).select_related('celebrity').order_by('-created_at')[:limit * 2]
        else:
            # Return popular merchandise
            merchandise = Merchandise.objects.filter(
                status='available',
                stock_quantity__gt=0
            ).select_related('celebrity').order_by('-total_sold')[:limit * 2]

        # Score merchandise
        scored_items = []
        for item in merchandise:
            score = 0

            # Prefer featured items
            if item.is_featured:
                score += 20

            # Prefer exclusive items
            if item.is_exclusive:
                score += 15

            # Factor in popularity
            score += item.total_sold / 10

            # Factor in discount
            if item.discount_percentage:
                score += item.discount_percentage / 5

            scored_items.append((item, score))

        scored_items.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored_items[:limit]]

    def _recommend_similar_fans(self, fan, limit=10):
        """Recommend similar fans based on interests and activity"""
        try:
            fan_profile = fan.fan_profile
        except ObjectDoesNotExist:
            return []

        fan_interests = set(fan_profile.interests or [])
        
        if not fan_interests:
            return []

        # Get fans user is already following
        following_ids = set(UserFollowing.objects.filter(
            follower=fan
        ).values_list('following_id', flat=True))

        # Get other fans with profiles
        other_fans = User.objects.filter(
            user_type='fan',
            is_active=True
        ).exclude(
            Q(id=fan.id) | Q(id__in=following_ids)
        ).prefetch_related('fan_profile')[:200]

        # Score fans based on shared interests
        scored_fans = []
        for other_fan in other_fans:
            try:
                other_profile = other_fan.fan_profile
                other_interests = set(other_profile.interests or [])
                matching_interests = fan_interests & other_interests

                if matching_interests:
                    score = len(matching_interests) * 10

                    # Factor in mutual connections
                    mutual_following = UserFollowing.objects.filter(
                        follower=fan,
                        following__in=UserFollowing.objects.filter(
                            follower=other_fan
                        ).values_list('following_id', flat=True)
                    ).count()
                    score += mutual_following * 5

                    scored_fans.append((other_fan, score))
            except ObjectDoesNotExist:
                continue

        scored_fans.sort(key=lambda x: x[1], reverse=True)
        return [fan_obj for fan_obj, score in scored_fans[:limit]]

    def _recommend_fans_for_celebrity(self, celebrity, limit=10):
        """Recommend potential fans for a celebrity to engage with"""
        try:
            celebrity_profile = celebrity.celebrity_profile
        except ObjectDoesNotExist:
            return []

        celebrity_categories = set(celebrity_profile.categories or [])
        
        if not celebrity_categories:
            return []

        # Get current followers
        current_follower_ids = set(UserFollowing.objects.filter(
            following=celebrity
        ).values_list('follower_id', flat=True))

        # Get active fans who might be interested
        potential_fans = User.objects.filter(
            user_type='fan',
            is_active=True
        ).exclude(
            id__in=current_follower_ids
        ).prefetch_related('fan_profile')[:200]

        # Score fans based on interest match
        scored_fans = []
        for fan in potential_fans:
            try:
                fan_profile = fan.fan_profile
                fan_interests = set(fan_profile.interests or [])
                matching_interests = celebrity_categories & fan_interests

                if matching_interests:
                    score = len(matching_interests) * 10

                    # Factor in fan's activity level
                    if hasattr(fan_profile, 'activity_score') and fan_profile.activity_score:
                        score += fan_profile.activity_score / 10

                    scored_fans.append((fan, score))
            except ObjectDoesNotExist:
                continue

        scored_fans.sort(key=lambda x: x[1], reverse=True)
        return [fan for fan, score in scored_fans[:limit]]

    def get_collaborative_filtering_recommendations(self, user, item_type='post', limit=10):
        """
        Collaborative filtering based on similar users' preferences

        Args:
            user: User object
            item_type: 'post', 'celebrity', 'event', 'merchandise'
            limit: Number of recommendations
        """
        # Get users similar to this user (based on following patterns)
        user_following = set(UserFollowing.objects.filter(
            follower=user
        ).values_list('following_id', flat=True))

        if not user_following:
            return []

        # Find users with similar following patterns
        similar_users = []
        all_users = User.objects.filter(
            user_type=user.user_type,
            is_active=True
        ).exclude(id=user.id)[:200]

        for other_user in all_users:
            other_following = set(UserFollowing.objects.filter(
                follower=other_user
            ).values_list('following_id', flat=True))

            # Calculate Jaccard similarity
            if other_following:
                intersection = user_following & other_following
                union = user_following | other_following
                if len(union) > 0:
                    similarity = len(intersection) / len(union)

                    if similarity > 0.1:  # Minimum threshold
                        similar_users.append((other_user, similarity))

        # Sort by similarity
        similar_users.sort(key=lambda x: x[1], reverse=True)
        similar_user_ids = [u.id for u, _ in similar_users[:20]]

        # Get items liked/followed by similar users but not by current user
        recommended_items = []
        
        if item_type == 'post':
            # Get posts liked by similar users
            liked_post_ids = set(Like.objects.filter(
                user=user,
                post__isnull=False
            ).values_list('post_id', flat=True))
            
            similar_user_likes = Like.objects.filter(
                user_id__in=similar_user_ids,
                post__isnull=False
            ).exclude(
                post_id__in=liked_post_ids
            ).values('post_id').annotate(
                like_count=Count('id')
            ).order_by('-like_count')[:limit]
            
            post_ids = [item['post_id'] for item in similar_user_likes]
            recommended_items = list(Post.objects.filter(
                id__in=post_ids,
                is_active=True
            ).select_related('author'))
            
        elif item_type == 'celebrity':
            # Get celebrities followed by similar users
            similar_user_following = UserFollowing.objects.filter(
                follower_id__in=similar_user_ids,
                following__user_type='celebrity'
            ).exclude(
                following_id__in=user_following
            ).values('following_id').annotate(
                follow_count=Count('id')
            ).order_by('-follow_count')[:limit]
            
            celeb_ids = [item['following_id'] for item in similar_user_following]
            recommended_items = list(User.objects.filter(
                id__in=celeb_ids,
                user_type='celebrity',
                is_active=True
            ))
            
        elif item_type == 'event':
            # Get events attended by similar users
            user_events = set(EventBooking.objects.filter(
                user=user
            ).values_list('event_id', flat=True))
            
            similar_user_events = EventBooking.objects.filter(
                user_id__in=similar_user_ids
            ).exclude(
                event_id__in=user_events
            ).values('event_id').annotate(
                booking_count=Count('id')
            ).order_by('-booking_count')[:limit]
            
            event_ids = [item['event_id'] for item in similar_user_events]
            recommended_items = list(Event.objects.filter(
                id__in=event_ids,
                status='published',
                start_datetime__gte=timezone.now()
            ).select_related('celebrity'))


        return recommended_items[:limit]


class TrendingEngine:
    """Engine for calculating trending content"""

    @staticmethod
    def calculate_trending_hashtags(days=7, limit=20):
        """Calculate trending hashtags"""
        # Get recent posts
        since = timezone.now() - timedelta(days=days)
        recent_posts = Post.objects.filter(
            created_at__gte=since,
            is_active=True
        ).values_list('content', 'title')

        # Extract hashtags
        hashtag_pattern = r'#(\w+)'
        hashtags = []

        for content, title in recent_posts:
            text = f"{content or ''} {title or ''}"
            found_hashtags = re.findall(hashtag_pattern, text.lower())
            hashtags.extend(found_hashtags)

        # Count hashtags
        hashtag_counts = Counter(hashtags)

        # Return top trending
        trending = [
            {'hashtag': f'#{tag}', 'count': count}
            for tag, count in hashtag_counts.most_common(limit)
        ]

        return trending

    @staticmethod
    def calculate_trending_posts(days=3, limit=20):
        """Calculate trending posts based on recent engagement"""
        since = timezone.now() - timedelta(days=days)

        trending_posts = Post.objects.filter(
            created_at__gte=since,
            is_active=True
        ).select_related('author').annotate(
            engagement_score=F('likes_count') * 1.0 + F('comments_count') * 2.0 + F('shares_count') * 3.0
        ).order_by('-engagement_score')[:limit]

        return list(trending_posts)

    @staticmethod
    def calculate_trending_celebrities(days=7, limit=20):
        """Calculate trending celebrities based on recent growth and engagement"""
        from apps.accounts.models import UserFollowing

        trending = CelebrityProfile.objects.filter(
            verification_status='approved',
            user__is_active=True
        ).select_related('user').annotate(
            followers_count=Count('user__followers', distinct=True),
            posts_count=Count('user__posts', distinct=True)
        ).annotate(
            engagement=F('followers_count') + F('posts_count')
        ).order_by('-engagement', '-total_subscribers')[:limit]

        return list(trending)

    @staticmethod
    def calculate_trending_events(days=14, limit=20):
        """Calculate trending events based on registrations"""
        now = timezone.now()
        upcoming = now + timedelta(days=days)

        trending_events = (
            Event.objects.filter(
                start_datetime__gte=now,
                start_datetime__lte=upcoming,
                status='published'
            )
            .annotate(attendees_count=Count('registrations'))
            .select_related('celebrity')
            .order_by('-attendees_count', 'start_datetime')[:limit]
        )

        return list(trending_events)
