# algorithms/utils.py

import numpy as np
from datetime import datetime, timedelta
import re
from difflib import SequenceMatcher


def calculate_trending_score(item_data):
    """
    Calculate trending score for an item
    item_data: dict with keys: views, likes, comments, created_at
    """
    now = datetime.now()
    age_hours = (now - item_data['created_at']).total_seconds() / 3600
    
    # Prevent division by zero
    age_hours = max(age_hours, 0.1)
    
    # Calculate engagement
    engagement = (
        item_data.get('views', 0) * 0.1 +
        item_data.get('likes', 0) * 0.5 +
        item_data.get('comments', 0) * 0.7
    )
    
    # Time decay factor (newer items get higher score)
    time_decay = 1 / (1 + age_hours / 24)  # Decay over days
    
    # Trending score
    trending_score = engagement * time_decay
    
    return trending_score

def calculate_user_similarity(user1_data, user2_data):
    """
    Calculate similarity between two users
    user_data: dict with user attributes and interactions
    """
    # Extract feature vectors
    features1 = extract_user_features(user1_data)
    features2 = extract_user_features(user2_data)
    
    # Cosine similarity
    dot_product = np.dot(features1, features2)
    norm1 = np.linalg.norm(features1)
    norm2 = np.linalg.norm(features2)
    
    if norm1 > 0 and norm2 > 0:
        similarity = dot_product / (norm1 * norm2)
    else:
        similarity = 0
    
    return similarity

def extract_user_features(user_data):
    """Extract feature vector from user data"""
    features = []
    
    # Activity features
    features.append(user_data.get('posts_count', 0) / 100)
    features.append(user_data.get('likes_given', 0) / 1000)
    features.append(user_data.get('comments_count', 0) / 500)
    
    # Engagement features
    features.append(user_data.get('followers_count', 0) / 1000)
    features.append(user_data.get('following_count', 0) / 500)
    
    # Normalize to [0, 1]
    features = np.array(features)
    features = np.clip(features, 0, 1)
    
    return features

def detect_spam_pattern(text, user_history=None):
    """Detect potential spam patterns in text"""
    spam_indicators = 0
    
    # Check for excessive links
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    if len(urls) > 2:
        spam_indicators += 2
    
    # Check for repetitive text
    words = text.split()
    if len(words) > 10:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.5:
            spam_indicators += 1
    
    # Check for excessive caps
    if len(text) > 10:
        caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
        if caps_ratio > 0.7:
            spam_indicators += 1
    
    # Check user history for repetitive posts
    if user_history:
        similar_posts = sum(1 for post in user_history if similarity(text, post) > 0.8)
        if similar_posts > 3:
            spam_indicators += 2
    
    return spam_indicators > 2

def similarity(text1, text2):
    """Simple text similarity"""
    return SequenceMatcher(None, text1, text2).ratio()