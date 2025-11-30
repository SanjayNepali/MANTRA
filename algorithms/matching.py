# algorithms/matching.py

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict


class MatchingEngine:
    """Advanced matching engine for fans, celebrities, and content"""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100)

    def match_fan_to_celebrity(self, fan, limit=10):
        """
        Match fan to celebrities based on interests, activity, and preferences

        Args:
            fan: Fan user object
            limit: Number of matches to return

        Returns:
            List of tuples: (celebrity, match_score)
        """
        from apps.accounts.models import User, UserFollowing
        from apps.celebrities.models import CelebrityProfile

        if not hasattr(fan, 'fan_profile'):
            return []

        fan_interests = set(fan.fan_profile.interests or [])

        # Get celebrities fan is not already following
        following_ids = UserFollowing.objects.filter(
            follower=fan
        ).values_list('following_id', flat=True)

        celebrities = CelebrityProfile.objects.select_related('user').exclude(
            user_id__in=following_ids
        ).filter(is_verified=True)

        # Calculate match scores
        matches = []
        for celebrity in celebrities:
            match_score = self._calculate_fan_celebrity_match_score(
                fan, celebrity, fan_interests
            )
            if match_score > 0:
                matches.append((celebrity, match_score))

        # Sort by match score
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:limit]

    def _calculate_fan_celebrity_match_score(self, fan, celebrity, fan_interests):
        """Calculate match score between fan and celebrity"""
        score = 0.0

        # Interest/Category matching (40% weight)
        celebrity_categories = set(celebrity.categories or [])
        matching_interests = fan_interests & celebrity_categories
        interest_score = len(matching_interests) * 10
        score += interest_score * 0.4

        # Celebrity popularity (20% weight)
        popularity_score = min(celebrity.points / 100, 100)
        score += popularity_score * 0.2

        # Engagement rate (20% weight)
        if hasattr(celebrity, 'engagement_rate'):
            engagement_score = celebrity.engagement_rate * 100
            score += engagement_score * 0.2

        # Content activity (20% weight)
        posts_count = celebrity.user.posts.count() if hasattr(celebrity.user, 'posts') else 0
        activity_score = min(posts_count / 10, 100)
        score += activity_score * 0.2

        return score

    def match_fan_to_fan_club(self, fan, limit=10):
        """
        Match fan to relevant fan clubs

        Args:
            fan: Fan user object
            limit: Number of matches to return

        Returns:
            List of tuples: (fan_club, match_score)
        """
        from apps.fanclubs.models import FanClub, FanClubMembership

        if not hasattr(fan, 'fan_profile'):
            return []

        fan_interests = set(fan.fan_profile.interests or [])

        # Get fan clubs fan is not already a member of
        member_club_ids = FanClubMembership.objects.filter(
            member=fan,
            status='active'
        ).values_list('fan_club_id', flat=True)

        fan_clubs = FanClub.objects.exclude(
            id__in=member_club_ids
        ).filter(is_active=True)

        # Calculate match scores
        matches = []
        for fan_club in fan_clubs:
            match_score = self._calculate_fan_fanclub_match_score(
                fan, fan_club, fan_interests
            )
            if match_score > 0:
                matches.append((fan_club, match_score))

        # Sort by match score
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:limit]

    def _calculate_fan_fanclub_match_score(self, fan, fan_club, fan_interests):
        """Calculate match score between fan and fan club"""
        score = 0.0

        # Interest matching (50% weight)
        club_tags = set(fan_club.tags or [])
        matching_interests = fan_interests & club_tags
        interest_score = len(matching_interests) * 15
        score += interest_score * 0.5

        # Club size (20% weight) - prefer active clubs
        member_count = fan_club.member_count
        if 10 <= member_count <= 1000:
            size_score = 100
        elif member_count < 10:
            size_score = 50  # Too small
        else:
            size_score = 70  # Very large
        score += size_score * 0.2

        # Club activity (30% weight)
        if fan_club.is_official:
            score += 50 * 0.3  # Bonus for official clubs

        return score

    def match_content_to_user(self, user, content_items, content_type='post', limit=10):
        """
        Match content items to user based on preferences and history

        Args:
            user: User object
            content_items: QuerySet of content items
            content_type: 'post', 'event', 'merchandise'
            limit: Number of matches to return

        Returns:
            List of tuples: (content_item, match_score)
        """
        if not hasattr(user, 'fan_profile'):
            # If no profile, return by popularity
            if content_type == 'post':
                return [(item, 0) for item in content_items.order_by('-likes_count')[:limit]]
            else:
                return [(item, 0) for item in content_items[:limit]]

        user_interests = user.fan_profile.interests or []

        # Calculate match scores
        matches = []
        for item in content_items:
            match_score = self._calculate_content_match_score(
                user_interests, item, content_type
            )
            matches.append((item, match_score))

        # Sort by match score
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:limit]

    def _calculate_content_match_score(self, user_interests, content_item, content_type):
        """Calculate match score between user interests and content"""
        score = 0.0
        user_interests_set = set(user_interests)

        if content_type == 'post':
            # Match based on post content and hashtags
            content_text = f"{content_item.content or ''} {content_item.caption or ''}"

            # Simple keyword matching
            for interest in user_interests:
                if interest.lower() in content_text.lower():
                    score += 20

            # Engagement score
            engagement = content_item.likes_count * 0.5 + content_item.comments_count * 1.0
            score += min(engagement / 10, 50)

        elif content_type == 'event':
            # Match based on event categories or interests
            interests_attr = getattr(content_item, "interests", None)
            if hasattr(interests_attr, "all"):
                event_categories = set(i.interest_type for i in interests_attr.all())
            else:
                event_categories = set(
                    getattr(content_item, "categories", None)
                    or [getattr(content_item, "event_type", None)]
                    or []
                )

            # Matching user interests
            matching_categories = user_interests_set & event_categories
            score += len(matching_categories) * 25

            # Popularity score — safe fallback if not annotated
            attendees_count = getattr(content_item, "attendees_count", None)
            if attendees_count is None:
                attendees_count = getattr(content_item, "tickets_sold", 0) or \
                                getattr(content_item, "total_tickets", 0) or 0
            score += min(attendees_count / 5, 30)


        elif content_type == 'merchandise':
            # Match based on category and celebrity
            # This is simplified - could be enhanced with actual categories
            score += content_item.total_sold / 10
            if content_item.is_featured:
                score += 20

        return score

    def find_compatible_users(self, user, user_type='fan', limit=10):
        """
        Find compatible users based on interests and activity

        Args:
            user: User object
            user_type: 'fan' or 'celebrity'
            limit: Number of matches to return

        Returns:
            List of tuples: (user, compatibility_score)
        """
        from apps.accounts.models import User, UserFollowing

        if not hasattr(user, 'fan_profile') and user_type == 'fan':
            return []

        user_interests = set(user.fan_profile.interests or []) if hasattr(user, 'fan_profile') else set()

        # Get users of specified type
        other_users = User.objects.filter(
            user_type=user_type,
            is_active=True
        ).exclude(id=user.id)

        # Exclude already following
        following_ids = UserFollowing.objects.filter(
            follower=user
        ).values_list('following_id', flat=True)
        other_users = other_users.exclude(id__in=following_ids)

        # Calculate compatibility scores
        compatible_users = []
        for other_user in other_users[:100]:  # Limit for performance
            compatibility_score = self._calculate_user_compatibility(
                user, other_user, user_interests, user_type
            )
            if compatibility_score > 0:
                compatible_users.append((other_user, compatibility_score))

        # Sort by compatibility score
        compatible_users.sort(key=lambda x: x[1], reverse=True)

        return compatible_users[:limit]

    def _calculate_user_compatibility(self, user1, user2, user1_interests, user_type):
        """Calculate compatibility score between two users"""
        score = 0.0

        if user_type == 'fan':
            if not hasattr(user2, 'fan_profile'):
                return 0.0

            user2_interests = set(user2.fan_profile.interests or [])

            # Interest overlap (60% weight)
            common_interests = user1_interests & user2_interests
            if user1_interests and user2_interests:
                jaccard_similarity = len(common_interests) / len(user1_interests | user2_interests)
                score += jaccard_similarity * 100 * 0.6

            # Activity level similarity (20% weight)
            user1_activity = user1.fan_profile.activity_score if hasattr(user1.fan_profile, 'activity_score') else 0
            user2_activity = user2.fan_profile.activity_score if hasattr(user2.fan_profile, 'activity_score') else 0

            # Prefer similar activity levels
            activity_diff = abs(user1_activity - user2_activity)
            activity_score = max(0, 100 - activity_diff)
            score += activity_score * 0.2

            # Mutual connections (20% weight)
            from apps.accounts.models import UserFollowing
            user1_following = set(UserFollowing.objects.filter(
                follower=user1
            ).values_list('following_id', flat=True))
            user2_following = set(UserFollowing.objects.filter(
                follower=user2
            ).values_list('following_id', flat=True))

            mutual_following = user1_following & user2_following
            mutual_score = min(len(mutual_following) * 10, 100)
            score += mutual_score * 0.2

        return score

    def match_celebrity_to_brands(self, celebrity, brands_list, limit=10):
        """
        Match celebrity to potential brand partnerships

        Args:
            celebrity: Celebrity user object
            brands_list: List of brand objects or dicts with brand info
            limit: Number of matches to return

        Returns:
            List of tuples: (brand, match_score)
        """
        if not hasattr(celebrity, 'celebrity_profile'):
            return []

        celebrity_categories = set(celebrity.celebrity_profile.categories or [])
        celebrity_followers = celebrity.total_followers

        matches = []
        for brand in brands_list:
            match_score = self._calculate_celebrity_brand_match(
                celebrity_categories, celebrity_followers, brand
            )
            matches.append((brand, match_score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]

    def _calculate_celebrity_brand_match(self, celebrity_categories, celebrity_followers, brand):
        """Calculate match score between celebrity and brand"""
        score = 0.0

        # Category alignment (50% weight)
        brand_categories = set(brand.get('categories', []))
        matching_categories = celebrity_categories & brand_categories
        category_score = len(matching_categories) * 20
        score += category_score * 0.5

        # Audience size match (30% weight)
        brand_target_audience_size = brand.get('target_audience_size', 0)
        if brand_target_audience_size > 0:
            size_ratio = min(celebrity_followers / brand_target_audience_size, 1.0)
            score += size_ratio * 100 * 0.3

        # Brand prestige (20% weight)
        brand_prestige = brand.get('prestige_score', 50)  # 0-100
        score += brand_prestige * 0.2

        return score

    def calculate_fan_celebrity_affinity(self, fan, celebrity):
        """
        Calculate affinity score between a fan and celebrity

        Args:
            fan: Fan user object
            celebrity: Celebrity user object

        Returns:
            float: Affinity score (0-100)
        """
        affinity_score = 0.0

        # Check if fan follows celebrity
        from apps.accounts.models import UserFollowing
        is_following = UserFollowing.objects.filter(
            follower=fan,
            following=celebrity
        ).exists()

        if is_following:
            affinity_score += 30

        # Check fan's interactions with celebrity's content
        from apps.posts.models import Like, Comment

        # Likes on celebrity's posts
        likes_count = Like.objects.filter(
            user=fan,
            post__author=celebrity
        ).count()
        affinity_score += min(likes_count * 2, 30)

        # Comments on celebrity's posts
        comments_count = Comment.objects.filter(
            author=fan,
            post__author=celebrity
        ).count()
        affinity_score += min(comments_count * 3, 30)

        # Interest alignment
        if hasattr(fan, 'fan_profile') and hasattr(celebrity, 'celebrity_profile'):
            fan_interests = set(fan.fan_profile.interests or [])
            celebrity_categories = set(celebrity.celebrity_profile.categories or [])
            matching = fan_interests & celebrity_categories
            affinity_score += len(matching) * 5

        return min(affinity_score, 100)

    def suggest_collaborations(self, celebrity1, celebrity2):
        """
        Suggest collaboration potential between two celebrities

        Args:
            celebrity1: First celebrity user object
            celebrity2: Second celebrity user object

        Returns:
            {
                'collaboration_score': float (0-100),
                'shared_audience': int,
                'category_overlap': list,
                'recommendation': str
            }
        """
        if not (hasattr(celebrity1, 'celebrity_profile') and hasattr(celebrity2, 'celebrity_profile')):
            return {
                'collaboration_score': 0,
                'shared_audience': 0,
                'category_overlap': [],
                'recommendation': 'Insufficient data'
            }

        collaboration_score = 0.0

        # Category overlap
        cat1 = set(celebrity1.celebrity_profile.categories or [])
        cat2 = set(celebrity2.celebrity_profile.categories or [])
        category_overlap = list(cat1 & cat2)
        collaboration_score += len(category_overlap) * 20

        # Audience size compatibility (similar sizes work better)
        followers1 = celebrity1.total_followers
        followers2 = celebrity2.total_followers

        if followers1 > 0 and followers2 > 0:
            ratio = min(followers1, followers2) / max(followers1, followers2)
            collaboration_score += ratio * 30

        # Engagement rate compatibility
        if hasattr(celebrity1.celebrity_profile, 'engagement_rate') and hasattr(celebrity2.celebrity_profile, 'engagement_rate'):
            avg_engagement = (celebrity1.celebrity_profile.engagement_rate + celebrity2.celebrity_profile.engagement_rate) / 2
            collaboration_score += avg_engagement * 20

        # Estimate shared audience
        from apps.accounts.models import UserFollowing
        celebrity1_followers = set(UserFollowing.objects.filter(
            following=celebrity1
        ).values_list('follower_id', flat=True)[:1000])  # Sample
        celebrity2_followers = set(UserFollowing.objects.filter(
            following=celebrity2
        ).values_list('follower_id', flat=True)[:1000])  # Sample

        shared_audience = len(celebrity1_followers & celebrity2_followers)
        collaboration_score += min(shared_audience / 10, 30)

        # Generate recommendation
        if collaboration_score > 70:
            recommendation = "Excellent collaboration potential!"
        elif collaboration_score > 50:
            recommendation = "Good collaboration opportunity"
        elif collaboration_score > 30:
            recommendation = "Moderate collaboration potential"
        else:
            recommendation = "Low collaboration potential"

        return {
            'collaboration_score': min(collaboration_score, 100),
            'shared_audience': shared_audience,
            'category_overlap': category_overlap,
            'recommendation': recommendation
        }