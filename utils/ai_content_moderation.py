# utils/ai_content_moderation.py
"""
AI-powered content moderation utilities
Provides sentiment analysis and toxicity detection for user-generated content
"""

import re
from typing import Dict, List, Any


# Toxic words list (basic version - expand as needed)
TOXIC_WORDS = [
    'hate', 'stupid', 'idiot', 'dumb', 'kill', 'die', 'death',
    'fuck', 'shit', 'bitch', 'ass', 'damn', 'hell',
    'loser', 'failure', 'worthless', 'pathetic', 'disgusting'
]

# Negative words for sentiment analysis
NEGATIVE_WORDS = [
    'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate',
    'angry', 'sad', 'depressed', 'upset', 'disappointed',
    'frustrating', 'annoying', 'useless', 'broken', 'failed'
]

# Positive words for sentiment analysis
POSITIVE_WORDS = [
    'good', 'great', 'excellent', 'amazing', 'wonderful', 'love',
    'happy', 'excited', 'best', 'awesome', 'fantastic',
    'perfect', 'beautiful', 'brilliant', 'outstanding', 'superb'
]


def analyze_text_content(text: str) -> Dict[str, Any]:
    """Analyze text content for sentiment and toxicity"""
    if not text or not isinstance(text, str):
        return {
            'sentiment': {'label': 'neutral', 'score': 0.5},
            'toxicity': {'is_toxic': False, 'toxic_words': []},
            'text_stats': {'length': 0, 'word_count': 0}
        }
    
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    text_stats = {
        'length': len(text),
        'word_count': len(words)
    }
    
    # Toxicity detection
    toxic_words_found = [word for word in words if word in TOXIC_WORDS]
    is_toxic = len(toxic_words_found) > 0
    toxicity_score = min(len(toxic_words_found) / max(len(words), 1), 1.0)
    
    toxicity_result = {
        'is_toxic': is_toxic,
        'toxic_words': list(set(toxic_words_found)),
        'toxicity_score': toxicity_score
    }
    
    # Sentiment analysis
    positive_count = sum(1 for word in words if word in POSITIVE_WORDS)
    negative_count = sum(1 for word in words if word in NEGATIVE_WORDS)
    
    total_sentiment_words = positive_count + negative_count
    if total_sentiment_words == 0:
        sentiment_score = 0.5
        sentiment_label = 'neutral'
    else:
        sentiment_score = positive_count / total_sentiment_words
        
        if sentiment_score >= 0.7:
            sentiment_label = 'very_positive'
        elif sentiment_score >= 0.55:
            sentiment_label = 'positive'
        elif sentiment_score >= 0.45:
            sentiment_label = 'neutral'
        elif sentiment_score >= 0.3:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'very_negative'
    
    sentiment_result = {
        'label': sentiment_label,
        'score': sentiment_score,
        'positive_words': positive_count,
        'negative_words': negative_count
    }
    
    return {
        'sentiment': sentiment_result,
        'toxicity': toxicity_result,
        'text_stats': text_stats
    }
