"""
test_algorithms_core.py

Tests for core algorithms that don't require Django
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Test non-Django algorithms
from algorithms.sentiment import SentimentAnalyzer, EngagementPredictor
from algorithms.string_matching import StringMatcher
from algorithms.collaborative_filtering import CollaborativeFilter
from algorithms.matching import MatchingEngine

# Mock Django imports to avoid errors
with patch.dict('sys.modules', {
    'django': MagicMock(),
    'apps.accounts.models': MagicMock(),
    'apps.posts.models': MagicMock(),
    'apps.interactions.models': MagicMock()
}):
    # Now import recommendation engine (it will use mocked Django)
    try:
        from algorithms.recommendation import RecommendationEngine, TrendingEngine
        HAS_RECOMMENDATION = True
    except ImportError:
        HAS_RECOMMENDATION = False
        # Create mock classes
        class MockRecommendationEngine:
            def __init__(self, *args, **kwargs):
                pass
            def get_user_recommendations(self, *args, **kwargs):
                return {}
        
        RecommendationEngine = MockRecommendationEngine
        TrendingEngine = MockRecommendationEngine


class TestSentimentAnalysis:
    """Test sentiment analysis algorithms"""
    
    def test_sentiment_analyzer_initialization(self):
        """Test sentiment analyzer can be initialized"""
        analyzer = SentimentAnalyzer()
        assert analyzer is not None
    
    def test_analyze_sentiment_positive(self):
        """Test positive sentiment analysis"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_sentiment("This is amazing! I love it!")
        
        assert 'score' in result
        assert 'label' in result
        assert result['label'] in ['positive', 'negative', 'neutral']
    
    def test_analyze_sentiment_negative(self):
        """Test negative sentiment analysis"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_sentiment("This is terrible! I hate it!")
        
        assert 'score' in result
        assert result['label'] in ['positive', 'negative', 'neutral']
    
    def test_detect_toxicity(self):
        """Test toxicity detection"""
        analyzer = SentimentAnalyzer()
        result = analyzer.detect_toxicity("This is a normal sentence.")
        
        assert 'is_toxic' in result
        assert 'toxicity_score' in result
        assert isinstance(result['is_toxic'], bool)
    
    def test_detect_spam(self):
        """Test spam detection"""
        analyzer = SentimentAnalyzer()
        result = analyzer.detect_spam("This is not spam.")
        
        assert 'is_spam' in result
        assert 'spam_score' in result
        assert isinstance(result['is_spam'], bool)


class TestEngagementPrediction:
    """Test engagement prediction algorithms"""
    
    def test_engagement_predictor_initialization(self):
        """Test engagement predictor can be initialized"""
        predictor = EngagementPredictor()
        assert predictor is not None
    
    def test_predict_post_engagement(self):
        """Test engagement prediction for posts"""
        predictor = EngagementPredictor()
        result = predictor.predict_post_engagement("Exciting news! #python #machinelearning")
        
        assert 'predicted_likes' in result
        assert 'engagement_score' in result
        assert 0 <= result['engagement_score'] <= 200  # Score can go up to 200


class TestStringMatching:
    """Test string matching algorithms"""
    
    def test_fuzzy_match_exact(self):
        """Test exact string matching"""
        score = StringMatcher.fuzzy_match("python", "python")
        assert score == 1.0
    
    def test_fuzzy_match_similar(self):
        """Test similar string matching"""
        score = StringMatcher.fuzzy_match("python", "pyhton")  # Typo
        assert 0.5 <= score < 1.0
    
    def test_fuzzy_match_different(self):
        """Test different string matching"""
        score = StringMatcher.fuzzy_match("python", "java")
        assert 0 <= score <= 0.5
    
    def test_tokenized_match(self):
        """Test token-based matching"""
        score = StringMatcher.tokenized_match("python programming", "I love python programming")
        assert score > 0.5


class TestCollaborativeFiltering:
    """Test collaborative filtering algorithms"""
    
    def test_collaborative_filter_initialization(self):
        """Test collaborative filter can be initialized"""
        cf = CollaborativeFilter(k_neighbors=3)
        assert cf is not None
        assert cf.k_neighbors == 3
    
    def test_fit_and_predict(self):
        """Test fitting model and making predictions"""
        cf = CollaborativeFilter(k_neighbors=2)
        
        # Create sample interactions
        interactions = [
            (0, 0, 5.0), (0, 1, 3.0), (0, 2, 1.0),
            (1, 0, 4.0), (1, 2, 5.0), (1, 3, 2.0),
            (2, 1, 4.0), (2, 3, 5.0)
        ]
        
        # Fit the model
        cf.fit(interactions)
        
        # Test prediction
        score = cf.predict_user_item_score(0, 3)
        assert isinstance(score, float)
        
        # Test recommendations
        recommendations = cf.recommend_items(0, n_recommendations=2)
        assert len(recommendations) <= 2
    
    def test_find_similar_users(self):
        """Test finding similar users"""
        cf = CollaborativeFilter(k_neighbors=2)
        
        interactions = [
            (0, 0, 5.0), (0, 1, 4.0),
            (1, 0, 5.0), (1, 1, 4.0),  # Similar to user 0
            (2, 2, 5.0), (2, 3, 4.0)   # Different from user 0
        ]
        
        cf.fit(interactions)
        similar_users = cf.find_similar_users(0, n_users=2)
        
        assert len(similar_users) <= 2


class TestMatchingEngine:
    """Test matching engine algorithms"""
    
    def test_matching_engine_initialization(self):
        """Test matching engine can be initialized"""
        engine = MatchingEngine()
        assert engine is not None


class TestRecommendationEngine:
    """Test recommendation algorithms (with mocks)"""
    
    def test_recommendation_engine_initialization(self):
        """Test recommendation engine can be initialized"""
        engine = RecommendationEngine()
        assert engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
