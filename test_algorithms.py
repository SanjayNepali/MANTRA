# test_algorithms.py
"""
Comprehensive test suite for MANTRA platform algorithms
Tests collaborative filtering, recommendations, sentiment analysis, and matching
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.test import TestCase
from scipy.sparse import csr_matrix

# Import algorithms
from algorithms.collaborative_filtering import CollaborativeFilter
from algorithms.sentiment import SentimentAnalyzer, EngagementPredictor
from algorithms.matching import MatchingEngine
from algorithms.recommendation import RecommendationEngine, TrendingEngine
from algorithms.string_matching import StringMatcher
from algorithms.utils import calculate_trending_score, calculate_user_similarity


class TestCollaborativeFiltering(TestCase):
    """Test collaborative filtering algorithm"""
    
    def setUp(self):
        """Setup test data"""
        self.cf = CollaborativeFilter(k_neighbors=3)
        
        # Create sample user-item interactions
        # Format: (user_id, item_id, rating)
        self.interactions = [
            (0, 0, 5.0), (0, 1, 3.0), (0, 2, 4.0),
            (1, 0, 3.0), (1, 1, 5.0), (1, 3, 4.0),
            (2, 1, 4.0), (2, 2, 5.0), (2, 3, 3.0),
            (3, 0, 4.0), (3, 2, 3.0), (3, 3, 5.0),
        ]
    
    def test_fit_with_list(self):
        """Test fitting model with list of interactions"""
        self.cf.fit(self.interactions)
        
        assert self.cf.model is not None
        assert self.cf.user_item_matrix is not None
        assert self.cf.user_item_matrix.shape == (4, 4)
    
    def test_fit_with_sparse_matrix(self):
        """Test fitting model with sparse matrix"""
        # Create sparse matrix directly
        rows = [x[0] for x in self.interactions]
        cols = [x[1] for x in self.interactions]
        data = [x[2] for x in self.interactions]
        
        matrix = csr_matrix((data, (rows, cols)), shape=(4, 4))
        
        self.cf.fit(matrix)
        assert self.cf.model is not None
    
    def test_recommend_items(self):
        """Test item recommendations"""
        self.cf.fit(self.interactions)
        
        # Get recommendations for user 0
        recommendations = self.cf.recommend_items(user_id=0, n_recommendations=2)
        
        assert len(recommendations) <= 2
        assert all(isinstance(r, tuple) for r in recommendations)
        assert all(len(r) == 2 for r in recommendations)
        
        # Check that recommended items are not already rated
        rated_items = {0, 1, 2}
        recommended_items = {r[0] for r in recommendations}
        assert len(rated_items & recommended_items) == 0
    
    def test_find_similar_users(self):
        """Test finding similar users"""
        self.cf.fit(self.interactions)
        
        similar_users = self.cf.find_similar_users(user_id=0, n_users=2)
        
        assert len(similar_users) <= 2
        assert all(isinstance(u, tuple) for u in similar_users)
        
        # Similar users should not include the target user
        assert all(u[0] != 0 for u in similar_users)
        
        # Similarity scores should be between 0 and 1
        assert all(0 <= u[1] <= 1 for u in similar_users)
    
    def test_predict_score_range(self):
        """Test that predicted scores are in valid range"""
        self.cf.fit(self.interactions)
        
        # Predict score for unrated item
        score = self.cf.predict_user_item_score(user_id=0, item_id=3)
        
        assert isinstance(score, (int, float, np.number))
        # Score should be non-negative (may be 0 if no similar items)
        assert score >= 0


class TestSentimentAnalysis(TestCase):
    """Test sentiment analysis and content moderation"""
    
    def setUp(self):
        self.analyzer = SentimentAnalyzer()
    
    def test_positive_sentiment(self):
        """Test detection of positive sentiment"""
        text = "I love this amazing product! It's absolutely wonderful and fantastic!"
        
        result = self.analyzer.analyze_sentiment(text)
        
        assert result['label'] == 'positive'
        assert result['score'] > 0
        assert 0 <= result['confidence'] <= 1
    
    def test_negative_sentiment(self):
        """Test detection of negative sentiment"""
        text = "This is terrible, awful, and completely disappointing. I hate it."
        
        result = self.analyzer.analyze_sentiment(text)
        
        assert result['label'] == 'negative'
        assert result['score'] < 0
    
    def test_neutral_sentiment(self):
        """Test detection of neutral sentiment"""
        text = "The product arrived on Tuesday. It is blue."
        
        result = self.analyzer.analyze_sentiment(text)
        
        assert result['label'] == 'neutral'
        assert abs(result['score']) <= 0.05
    
    def test_toxicity_detection_clean(self):
        """Test that clean content is not flagged as toxic"""
        text = "Great post! Thanks for sharing this helpful information."
        
        result = self.analyzer.detect_toxicity(text)
        
        assert result['is_toxic'] == False
        assert result['toxicity_score'] < 0.4
    
    def test_toxicity_detection_toxic(self):
        """Test detection of toxic content"""
        text = "You are stupid idiot moron worthless trash"
        
        result = self.analyzer.detect_toxicity(text)
        
        assert result['is_toxic'] == True
        assert result['toxicity_score'] >= 0.4
        assert len(result['toxic_words']) > 0
    
    def test_toxicity_repetition_penalty(self):
        """Test that repeated profanity increases toxicity"""
        text_single = "This is shit"
        text_repeated = "This is shit shit shit shit shit shit shit shit"
        
        result_single = self.analyzer.detect_toxicity(text_single)
        result_repeated = self.analyzer.detect_toxicity(text_repeated)
        
        # Repeated profanity should have higher toxicity
        assert result_repeated['toxicity_score'] > result_single['toxicity_score']
        assert result_repeated['total_repetitions'] > result_single['total_repetitions']
    
    def test_toxicity_severity_levels(self):
        """Test different severity levels"""
        low_toxic = "This is annoying"
        medium_toxic = "You're an idiot stupid moron"
        high_toxic = "fuck you fuck you fuck you fuck you fuck you fuck you fuck you"
        
        result_low = self.analyzer.detect_toxicity(low_toxic)
        result_medium = self.analyzer.detect_toxicity(medium_toxic)
        result_high = self.analyzer.detect_toxicity(high_toxic)
        
        # Check severity progression
        assert result_low['severity'] in ['low', 'medium']
        assert result_medium['severity'] in ['medium', 'high']
        assert result_high['severity'] == 'high'
    
    def test_spam_detection_clean(self):
        """Test that normal content is not flagged as spam"""
        text = "Check out my latest blog post about Python programming!"
        
        result = self.analyzer.detect_spam(text)
        
        assert result['is_spam'] == False
    
    def test_spam_detection_spam(self):
        """Test detection of spam content"""
        text = "BUY NOW!!! CLICK HERE!!! LIMITED TIME OFFER!!! http://spam.com http://more-spam.com"
        
        result = self.analyzer.detect_spam(text)
        
        assert result['is_spam'] == True
        assert result['spam_score'] > 0.5
        assert len(result['spam_indicators']) > 0
    
    def test_emotion_extraction(self):
        """Test emotion extraction"""
        happy_text = "I'm so happy and excited! This is wonderful and joyful!"
        sad_text = "I'm sad and depressed. This is disappointing and hurtful."
        
        happy_result = self.analyzer.extract_emotions(happy_text)
        sad_result = self.analyzer.extract_emotions(sad_text)
        
        assert happy_result['primary_emotion'] == 'joy'
        assert sad_result['primary_emotion'] == 'sadness'
        assert 'joy' in happy_result['all_emotions']
        assert 'sadness' in sad_result['all_emotions']
    
    def test_content_insights_comprehensive(self):
        """Test comprehensive content analysis"""
        text = "This is an amazing product that I absolutely love!"
        
        insights = self.analyzer.get_content_insights(text)
        
        # Check all components are present
        assert 'sentiment' in insights
        assert 'toxicity' in insights
        assert 'spam' in insights
        assert 'emotions' in insights
        
        # Verify structure
        assert 'score' in insights['sentiment']
        assert 'label' in insights['sentiment']
        assert 'is_toxic' in insights['toxicity']
        assert 'is_spam' in insights['spam']
        assert 'primary_emotion' in insights['emotions']
    
    def test_empty_text_handling(self):
        """Test handling of empty or None text"""
        result_empty = self.analyzer.analyze_sentiment("")
        result_none = self.analyzer.analyze_sentiment(None)
        
        assert result_empty['label'] == 'neutral'
        assert result_none['label'] == 'neutral'


class TestEngagementPredictor(TestCase):
    """Test engagement prediction"""
    
    def setUp(self):
        self.predictor = EngagementPredictor()
    
    def test_predict_engagement_basic(self):
        """Test basic engagement prediction"""
        content = "Check out this awesome #python #coding #tutorial post!"
        
        prediction = self.predictor.predict_post_engagement(
            content,
            author_stats={'followers_count': 1000}
        )
        
        assert 'predicted_likes' in prediction
        assert 'predicted_comments' in prediction
        assert 'predicted_shares' in prediction
        assert 'engagement_score' in prediction
        assert 'viral_potential' in prediction
        
        # Check ranges
        assert 0 <= prediction['viral_potential'] <= 1
        assert prediction['engagement_score'] >= 0
    
    def test_positive_content_bonus(self):
        """Test that positive content gets engagement bonus"""
        positive = "This is amazing, wonderful, and fantastic!"
        negative = "This is terrible, awful, and horrible."
        
        pred_positive = self.predictor.predict_post_engagement(positive)
        pred_negative = self.predictor.predict_post_engagement(negative)
        
        # Positive should have higher engagement score
        assert pred_positive['engagement_score'] > pred_negative['engagement_score']
    
    def test_toxic_content_penalty(self):
        """Test that toxic content gets penalized"""
        clean = "Great tutorial on Python programming!"
        toxic = "You stupid idiot moron worthless piece of trash"
        
        pred_clean = self.predictor.predict_post_engagement(clean)
        pred_toxic = self.predictor.predict_post_engagement(toxic)
        
        # Toxic should have lower engagement
        assert pred_toxic['engagement_score'] < pred_clean['engagement_score']
    
    def test_hashtag_effectiveness(self):
        """Test hashtag effectiveness analysis"""
        optimal = ['#python', '#coding', '#tutorial', '#programming']
        too_few = ['#python']
        too_many = ['#tag' + str(i) for i in range(15)]
        
        result_optimal = self.predictor.analyze_hashtag_effectiveness(optimal)
        result_few = self.predictor.analyze_hashtag_effectiveness(too_few)
        result_many = self.predictor.analyze_hashtag_effectiveness(too_many)
        
        # Optimal should have best score
        assert result_optimal['effectiveness_score'] > result_few['effectiveness_score']
        assert result_optimal['effectiveness_score'] > result_many['effectiveness_score']
    
    def test_content_length_impact(self):
        """Test impact of content length on engagement"""
        short = "Hi"  # Too short
        optimal = "This is a well-written post with good length that engages readers effectively."
        too_long = "word " * 250  # Way too long
        
        pred_short = self.predictor.predict_post_engagement(short)
        pred_optimal = self.predictor.predict_post_engagement(optimal)
        pred_long = self.predictor.predict_post_engagement(too_long)
        
        # Optimal length should perform best
        assert pred_optimal['engagement_score'] >= pred_short['engagement_score']
        assert pred_optimal['engagement_score'] >= pred_long['engagement_score']


class TestMatchingEngine(TestCase):
    """Test matching algorithms"""
    
    def setUp(self):
        self.matcher = MatchingEngine()
    
    def test_calculate_fan_celebrity_match_score(self):
        """Test fan-celebrity matching score calculation"""
        # Mock objects
        class MockFan:
            fan_profile = type('obj', (object,), {'interests': ['music', 'sports']})()
        
        class MockCelebrity:
            categories = ['music', 'entertainment']
            points = 5000
            user = type('obj', (object,), {'posts': type('obj', (object,), {'count': lambda: 50})()})()
        
        fan = MockFan()
        celebrity = MockCelebrity()
        fan_interests = set(['music', 'sports'])
        
        score = self.matcher._calculate_fan_celebrity_match_score(
            fan, celebrity, fan_interests
        )
        
        assert isinstance(score, (int, float))
        assert score >= 0
    
    def test_content_match_scoring(self):
        """Test content matching score"""
        user_interests = ['python', 'coding', 'technology']
        
        class MockPost:
            content = "Learn Python programming with this amazing tutorial!"
            caption = ""
            likes_count = 100
            comments_count = 20
        
        post = MockPost()
        
        score = self.matcher._calculate_content_match_score(
            user_interests, post, 'post'
        )
        
        assert isinstance(score, (int, float))
        assert score > 0  # Should match due to 'python' keyword


class TestRecommendationEngine(TestCase):
    """Test recommendation engine"""
    
    def setUp(self):
        self.engine = RecommendationEngine()
    
    def test_score_posts_by_content(self):
        """Test content-based post scoring"""
        class MockUser:
            fan_profile = type('obj', (object,), {
                'interests': ['python', 'programming', 'coding']
            })()
        
        class MockPost:
            def __init__(self, content, likes):
                self.content = content
                self.caption = ""
                self.likes_count = likes
                self.comments_count = 0
        
        user = MockUser()
        posts = [
            MockPost("Learn Python programming basics", 50),
            MockPost("Cooking recipes for dinner", 100),
            MockPost("Advanced Python machine learning tutorial", 30),
        ]
        
        scored_posts = self.engine._score_posts_by_content(user, posts)
        
        # Python-related posts should rank higher
        assert scored_posts[0].content in [posts[0].content, posts[2].content]


class TestTrendingEngine(TestCase):
    """Test trending calculation"""
    
    def test_trending_score_calculation(self):
        """Test trending score calculation"""
        from algorithms.utils import calculate_trending_score
        
        # Recent post with high engagement
        recent_high = {
            'views': 1000,
            'likes': 100,
            'comments': 50,
            'created_at': datetime.now() - timedelta(hours=2)
        }
        
        # Old post with high engagement
        old_high = {
            'views': 1000,
            'likes': 100,
            'comments': 50,
            'created_at': datetime.now() - timedelta(days=7)
        }
        
        # Recent post with low engagement
        recent_low = {
            'views': 100,
            'likes': 10,
            'comments': 5,
            'created_at': datetime.now() - timedelta(hours=2)
        }
        
        score_recent_high = calculate_trending_score(recent_high)
        score_old_high = calculate_trending_score(old_high)
        score_recent_low = calculate_trending_score(recent_low)
        
        # Recent high engagement should score highest
        assert score_recent_high > score_old_high
        assert score_recent_high > score_recent_low


class TestStringMatching(TestCase):
    """Test string matching algorithms"""
    
    def test_fuzzy_match_exact(self):
        """Test exact string matching"""
        result = StringMatcher.fuzzy_match("python", "python")
        assert result == 1.0
    
    def test_fuzzy_match_partial(self):
        """Test partial string matching"""
        result = StringMatcher.fuzzy_match("python", "python programming")
        assert result > 0.5
    
    def test_fuzzy_match_no_match(self):
        """Test non-matching strings"""
        result = StringMatcher.fuzzy_match("python", "javascript")
        assert result < 0.6
    
    def test_tokenized_match(self):
        """Test token-based matching"""
        query = "learn python programming"
        text = "programming with python tutorial"
        
        result = StringMatcher.tokenized_match(query, text)
        
        assert result > 0.3  # Should have some overlap
    
    def test_search_rank(self):
        """Test search ranking"""
        query = "python tutorial"
        
        items = [
            "Complete Python Tutorial for Beginners",
            "JavaScript Programming Guide",
            "Advanced Python Machine Learning",
            "Cooking Recipes"
        ]
        
        results = StringMatcher.search_rank(
            query, items, key_func=lambda x: x, threshold=0.2
        )
        
        # Should return Python-related items
        assert len(results) >= 2
        # Top result should contain 'python'
        assert 'python' in results[0][0].lower()


class TestUtilityFunctions(TestCase):
    """Test utility functions"""
    
    def test_calculate_user_similarity(self):
        """Test user similarity calculation"""
        from algorithms.utils import calculate_user_similarity
        
        user1 = {
            'posts_count': 50,
            'likes_given': 1000,
            'comments_count': 200,
            'followers_count': 500,
            'following_count': 300
        }
        
        user2 = {
            'posts_count': 45,
            'likes_given': 900,
            'comments_count': 180,
            'followers_count': 450,
            'following_count': 280
        }
        
        user3 = {
            'posts_count': 5,
            'likes_given': 50,
            'comments_count': 10,
            'followers_count': 20,
            'following_count': 30
        }
        
        # Similar users should have higher similarity
        sim_12 = calculate_user_similarity(user1, user2)
        sim_13 = calculate_user_similarity(user1, user3)
        
        assert sim_12 > sim_13


# Integration Tests
class TestAlgorithmIntegration(TestCase):
    """Test algorithm integration and edge cases"""
    
    def test_empty_input_handling(self):
        """Test that algorithms handle empty inputs gracefully"""
        analyzer = SentimentAnalyzer()
        
        # Empty text
        result = analyzer.analyze_sentiment("")
        assert result['label'] == 'neutral'
        
        # None text
        result = analyzer.analyze_sentiment(None)
        assert result['label'] == 'neutral'
    
    def test_extreme_values(self):
        """Test handling of extreme values"""
        predictor = EngagementPredictor()
        
        # Very long content
        long_content = "word " * 1000
        result = predictor.predict_post_engagement(long_content)
        assert result is not None
        
        # Content with special characters
        special_content = "!!!@@@###$$$%%%^^^&&&***"
        result = predictor.predict_post_engagement(special_content)
        assert result is not None
    
    def test_unicode_handling(self):
        """Test handling of unicode and non-ASCII characters"""
        analyzer = SentimentAnalyzer()
        
        # Emoji text
        emoji_text = "This is great! 😊🎉👍"
        result = analyzer.analyze_sentiment(emoji_text)
        assert result is not None
        
        # Non-ASCII characters
        unicode_text = "Namaste नमस्ते こんにちは"
        result = analyzer.analyze_sentiment(unicode_text)
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])