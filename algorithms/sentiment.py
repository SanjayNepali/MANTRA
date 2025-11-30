# algorithms/sentiment.py

from textblob import TextBlob
import re
from collections import Counter

try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.corpus import stopwords

    # Try to download required NLTK data (silently fail if offline)
    NLTK_AVAILABLE = True
    try:
        # Check if data already exists first
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True, raise_on_error=False)

        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True, raise_on_error=False)

        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon', quiet=True, raise_on_error=False)
    except Exception as e:
        # If downloads fail (e.g., no internet), continue with limited functionality
        pass

except ImportError:
    NLTK_AVAILABLE = False


class SentimentAnalyzer:
    """Advanced sentiment analysis and content moderation"""

    def __init__(self):
        if NLTK_AVAILABLE:
            try:
                self.sia = SentimentIntensityAnalyzer()
            except Exception as e:
                # If VADER lexicon is not available, fall back to TextBlob only
                self.sia = None
        else:
            self.sia = None

        # Toxicity detection keywords
        self.toxic_keywords = [
            'hate', 'kill', 'die', 'stupid', 'idiot', 'moron', 'dumb',
            'ugly', 'loser', 'pathetic', 'worthless', 'trash', 'garbage',
            'racist', 'sexist', 'homophobic', 'threat', 'violence', 'attack',
            # Add profanity
            'fuck', 'shit', 'ass', 'bitch', 'bastard', 'damn', 'hell',
            'crap', 'piss', 'dick', 'cock', 'pussy', 'whore', 'slut'
        ]
        self.aggressive_patterns = [
            r'fuck\s+(you|off|u)',
            r'shit\s+(head|face)',
            r'go\s+to\s+hell',
            r'suck\s+my\s+dick',
            r'kill\s+yourself',
            r'i\s+hate\s+you'
        ]

        # Spam detection patterns
        self.spam_patterns = [
            r'(click here|buy now|limited time|act now)',
            r'(\$\$\$|!!!+|\?{3,})',
            r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            r'(win \$|make money|get rich|free money)',
        ]

        # Emotion keywords
        self.emotion_keywords = {
            'joy': ['happy', 'joy', 'excited', 'love', 'wonderful', 'amazing', 'great', 'excellent', 'fantastic'],
            'sadness': ['sad', 'depressed', 'unhappy', 'cry', 'tears', 'disappointed', 'hurt', 'broken'],
            'anger': ['angry', 'mad', 'furious', 'rage', 'hate', 'annoyed', 'frustrated', 'outraged'],
            'fear': ['afraid', 'scared', 'terrified', 'fear', 'worry', 'anxious', 'nervous', 'panic'],
            'surprise': ['surprised', 'amazed', 'shocked', 'wow', 'unexpected', 'astonished', 'astounded'],
            'disgust': ['disgusting', 'gross', 'nasty', 'revolting', 'sick', 'yuck', 'awful']
        }

    def analyze_sentiment(self, text):
        """
        Analyze sentiment of text using multiple methods

        Returns:
            {
                'score': float (-1 to 1),
                'label': 'positive'/'negative'/'neutral',
                'confidence': float (0 to 1),
                'subjectivity': float (0 to 1)
            }
        """
        if not text or not text.strip():
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'subjectivity': 0.0
            }

        # Clean text
        cleaned_text = self._preprocess_text(text)

        # TextBlob analysis
        blob = TextBlob(cleaned_text)
        textblob_polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        # NLTK VADER analysis (if available)
        if self.sia:
            vader_scores = self.sia.polarity_scores(cleaned_text)
            vader_compound = vader_scores['compound']

            # Combine scores (weighted average)
            combined_score = (textblob_polarity * 0.5) + (vader_compound * 0.5)
        else:
            combined_score = textblob_polarity

        # Apply profanity repetition penalty
        profanity_penalty = self._calculate_profanity_penalty(text)
        combined_score = combined_score - profanity_penalty

        # Determine sentiment label
        if combined_score > 0.05:
            label = 'positive'
        elif combined_score < -0.05:
            label = 'negative'
        else:
            label = 'neutral'

        # Calculate confidence
        confidence = min(abs(combined_score), 1.0)

        return {
            'score': combined_score,
            'label': label,
            'confidence': confidence,
            'subjectivity': subjectivity
        }

    def detect_toxicity(self, text):
        """
        Detect toxic content in text

        Returns:
            {
                'is_toxic': bool,
                'toxicity_score': float (0 to 1),
                'toxic_words': list,
                'severity': 'low'/'medium'/'high',
                'repetition_factor': float
            }
        """
        if not text:
            return {
                'is_toxic': False,
                'toxicity_score': 0.0,
                'toxic_words': [],
                'severity': 'low',
                'repetition_factor': 0.0
            }

        text_lower = text.lower()
        toxic_words_found = []
        word_count_map = {}

        # Check for toxic keywords and count repetitions
        for keyword in self.toxic_keywords:
            # Count how many times each toxic word appears
            count = text_lower.count(keyword)
            if count > 0:
                toxic_words_found.append(keyword)
                word_count_map[keyword] = count

        # Calculate base toxicity score with repetition weighting
        toxicity_score = 0.0
        total_repetitions = sum(word_count_map.values())

        # Each unique toxic word adds 0.15, each repetition adds 0.1
        unique_toxic_words = len(toxic_words_found)
        toxicity_score += unique_toxic_words * 0.15

        # Exponential penalty for repetitions
        if total_repetitions > unique_toxic_words:
            extra_repetitions = total_repetitions - unique_toxic_words
            # Each extra repetition increases toxicity exponentially
            repetition_penalty = min(extra_repetitions * 0.12, 0.6)
            toxicity_score += repetition_penalty

        # Calculate repetition factor (for display)
        repetition_factor = total_repetitions / max(unique_toxic_words, 1) if unique_toxic_words > 0 else 0

        # Check for aggressive punctuation
        aggressive_punctuation = len(re.findall(r'[!?]{2,}', text))
        toxicity_score += aggressive_punctuation * 0.1

        # Check for ALL CAPS (shouting)
        words = text.split()
        if words:
            caps_ratio = sum(1 for word in words if word.isupper() and len(word) > 2) / len(words)
            toxicity_score += caps_ratio * 0.2

        # Cap at 1.0
        toxicity_score = min(toxicity_score, 1.0)

        # Determine if toxic (more sensitive threshold)
        is_toxic = toxicity_score > 0.4

        # Determine severity with adjusted thresholds
        if toxicity_score > 0.7 or total_repetitions > 10:
            severity = 'high'
        elif toxicity_score > 0.4 or total_repetitions > 5:
            severity = 'medium'
        else:
            severity = 'low'

        return {
            'is_toxic': is_toxic,
            'toxicity_score': toxicity_score,
            'toxic_words': toxic_words_found,
            'severity': severity,
            'repetition_factor': repetition_factor,
            'total_repetitions': total_repetitions
        }

    def detect_spam(self, text):
        """
        Detect spam content

        Returns:
            {
                'is_spam': bool,
                'spam_score': float (0 to 1),
                'spam_indicators': list
            }
        """
        if not text:
            return {
                'is_spam': False,
                'spam_score': 0.0,
                'spam_indicators': []
            }

        spam_score = 0.0
        spam_indicators = []

        # Check spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, text.lower()):
                spam_score += 0.25
                spam_indicators.append(f"Pattern: {pattern}")

        # Check for excessive links
        links = re.findall(r'http[s]?://\S+', text)
        if len(links) > 2:
            spam_score += 0.3
            spam_indicators.append(f"Excessive links: {len(links)}")

        # Check for excessive emojis
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            "]+", flags=re.UNICODE)
        emojis = emoji_pattern.findall(text)
        if len(emojis) > 10:
            spam_score += 0.2
            spam_indicators.append(f"Excessive emojis: {len(emojis)}")

        # Check for repeated characters
        if re.search(r'(.)\1{4,}', text):
            spam_score += 0.15
            spam_indicators.append("Repeated characters")

        # Check for excessive capitalization
        if text.isupper() and len(text) > 20:
            spam_score += 0.2
            spam_indicators.append("All caps")

        # Cap at 1.0
        spam_score = min(spam_score, 1.0)

        return {
            'is_spam': spam_score > 0.5,
            'spam_score': spam_score,
            'spam_indicators': spam_indicators
        }

    def extract_emotions(self, text):
        """
        Extract emotions from text

        Returns:
            {
                'primary_emotion': str,
                'emotion_scores': dict,
                'all_emotions': list
            }
        """
        if not text:
            return {
                'primary_emotion': 'neutral',
                'emotion_scores': {},
                'all_emotions': []
            }

        text_lower = text.lower()
        emotion_scores = {}

        # Calculate score for each emotion
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            emotion_scores[emotion] = score

        # Normalize scores
        total_score = sum(emotion_scores.values())
        if total_score > 0:
            normalized_scores = {
                emotion: score / total_score
                for emotion, score in emotion_scores.items()
            }
        else:
            normalized_scores = emotion_scores

        # Get primary emotion
        if emotion_scores:
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            if emotion_scores[primary_emotion] == 0:
                primary_emotion = 'neutral'
        else:
            primary_emotion = 'neutral'

        # Get all emotions with non-zero scores
        all_emotions = [
            emotion for emotion, score in normalized_scores.items()
            if score > 0
        ]

        return {
            'primary_emotion': primary_emotion,
            'emotion_scores': normalized_scores,
            'all_emotions': all_emotions
        }

    def get_content_insights(self, text):
        """
        Get comprehensive content analysis

        Returns complete analysis including sentiment, toxicity, spam, emotions
        """
        return {
            'sentiment': self.analyze_sentiment(text),
            'toxicity': self.detect_toxicity(text),
            'spam': self.detect_spam(text),
            'emotions': self.extract_emotions(text)
        }

    def _preprocess_text(self, text):
        """Preprocess text for analysis"""
        # Remove URLs
        text = re.sub(r'http\S+|www.\S+', '', text)

        # Remove mentions
        text = re.sub(r'@\w+', '', text)

        # Remove hashtags (keep the text)
        text = re.sub(r'#(\w+)', r'\1', text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        return text

    def _calculate_profanity_penalty(self, text):
        """
        Calculate sentiment penalty based on profanity repetition

        Returns:
            float: Penalty value (0 to 1.0) to subtract from sentiment score
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        penalty = 0.0
        total_profanity_count = 0

        # Count each profanity word
        for keyword in self.toxic_keywords:
            count = text_lower.count(keyword)
            if count > 0:
                total_profanity_count += count
                # Base penalty for presence
                penalty += 0.05
                # Additional penalty for repetition (exponential growth)
                if count > 1:
                    repetition_penalty = min((count - 1) * 0.08, 0.4)
                    penalty += repetition_penalty

        # Additional penalty for excessive profanity (spam-like behavior)
        if total_profanity_count > 10:
            penalty += 0.3
        elif total_profanity_count > 5:
            penalty += 0.15

        # Cap penalty at 1.0 (completely negative)
        return min(penalty, 1.0)


class EngagementPredictor:
    """Predict engagement for posts and content"""

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()

    def predict_post_engagement(self, post_content, author_stats=None):
        """
        Predict engagement metrics for a post

        Args:
            post_content: str - The post text
            author_stats: dict - Author's statistics (followers, avg_likes, etc.)

        Returns:
            {
                'predicted_likes': int,
                'predicted_comments': int,
                'predicted_shares': int,
                'engagement_score': float,
                'viral_potential': float (0 to 1)
            }
        """
        # Analyze content
        insights = self.sentiment_analyzer.get_content_insights(post_content)

        # Base engagement score
        engagement_score = 50.0

        # Factor in sentiment (positive content gets more engagement)
        if insights['sentiment']['label'] == 'positive':
            engagement_score += 20
        elif insights['sentiment']['label'] == 'negative':
            engagement_score -= 10

        # Factor in emotions (emotional content gets more engagement)
        if insights['emotions']['primary_emotion'] != 'neutral':
            engagement_score += 15

        # Penalize toxic content
        if insights['toxicity']['is_toxic']:
            engagement_score -= 30

        # Penalize spam
        if insights['spam']['is_spam']:
            engagement_score -= 40

        # Factor in content length
        word_count = len(post_content.split())
        if 20 <= word_count <= 100:
            engagement_score += 10  # Optimal length
        elif word_count > 200:
            engagement_score -= 10  # Too long

        # Check for hashtags
        hashtags = re.findall(r'#\w+', post_content)
        if 1 <= len(hashtags) <= 5:
            engagement_score += 10
        elif len(hashtags) > 5:
            engagement_score -= 5

        # Check for questions (increases engagement)
        if '?' in post_content:
            engagement_score += 10

        # Factor in author stats if provided
        if author_stats:
            follower_multiplier = 1 + (author_stats.get('followers_count', 0) / 10000)
            engagement_score *= min(follower_multiplier, 3.0)  # Cap multiplier at 3x

        # Calculate predicted metrics
        base_likes = max(0, int(engagement_score * 0.5))
        base_comments = max(0, int(engagement_score * 0.1))
        base_shares = max(0, int(engagement_score * 0.05))

        # Calculate viral potential
        viral_potential = min(engagement_score / 200, 1.0)

        return {
            'predicted_likes': base_likes,
            'predicted_comments': base_comments,
            'predicted_shares': base_shares,
            'engagement_score': engagement_score,
            'viral_potential': viral_potential
        }

    def analyze_hashtag_effectiveness(self, hashtags_list):
        """
        Analyze effectiveness of hashtags

        Args:
            hashtags_list: list of hashtags

        Returns:
            {
                'total_hashtags': int,
                'effectiveness_score': float,
                'recommendations': list
            }
        """
        hashtag_count = len(hashtags_list)

        # Optimal hashtag count is 3-5
        if 3 <= hashtag_count <= 5:
            effectiveness_score = 1.0
            recommendations = ["Great hashtag count!"]
        elif hashtag_count < 3:
            effectiveness_score = 0.6
            recommendations = ["Consider adding more hashtags (3-5 is optimal)"]
        elif hashtag_count > 10:
            effectiveness_score = 0.4
            recommendations = ["Too many hashtags - reduce to 3-5 for better engagement"]
        else:
            effectiveness_score = 0.8
            recommendations = ["Good hashtag count"]

        return {
            'total_hashtags': hashtag_count,
            'effectiveness_score': effectiveness_score,
            'recommendations': recommendations
        }

    def suggest_best_posting_time(self, user_timezone='UTC'):
        """
        Suggest best time to post based on general engagement patterns

        Args:
            user_timezone: str - User's timezone

        Returns:
            {
                'recommended_hours': list,
                'reason': str
            }
        """
        # General best times (in 24-hour format)
        best_times = {
            'weekday': [9, 12, 17, 20],  # 9am, 12pm, 5pm, 8pm
            'weekend': [10, 14, 19, 21]   # 10am, 2pm, 7pm, 9pm
        }

        from datetime import datetime
        now = datetime.now()
        is_weekend = now.weekday() >= 5

        recommended_hours = best_times['weekend'] if is_weekend else best_times['weekday']

        return {
            'recommended_hours': recommended_hours,
            'reason': 'Based on general engagement patterns',
            'day_type': 'weekend' if is_weekend else 'weekday'
        }