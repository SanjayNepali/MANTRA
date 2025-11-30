# algorithms/string_matching.py

from difflib import SequenceMatcher
import re

class StringMatcher:
    """Advanced string matching for search and recommendations"""
    
    @staticmethod
    def fuzzy_match(query, text, threshold=0.6):
        """Fuzzy string matching"""
        query = query.lower().strip()
        text = text.lower().strip()
        
        # Direct substring match
        if query in text or text in query:
            return 1.0
        
        # Calculate similarity ratio
        ratio = SequenceMatcher(None, query, text).ratio()
        
        return ratio if ratio >= threshold else 0.0
    
    @staticmethod
    def tokenized_match(query, text):
        """Token-based matching for better search"""
        query_tokens = set(query.lower().split())
        text_tokens = set(text.lower().split())
        
        # Calculate Jaccard similarity
        intersection = query_tokens & text_tokens
        union = query_tokens | text_tokens
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    @staticmethod
    def search_rank(query, items, key_func, threshold=0.3):
        """
        Rank items based on search query
        items: list of items to search
        key_func: function to extract searchable text from item
        """
        results = []
        
        for item in items:
            text = key_func(item)
            
            # Calculate different similarity scores
            fuzzy_score = StringMatcher.fuzzy_match(query, text)
            token_score = StringMatcher.tokenized_match(query, text)
            
            # Combined score (weighted average)
            combined_score = 0.7 * fuzzy_score + 0.3 * token_score
            
            if combined_score >= threshold:
                results.append((item, combined_score))
        
        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results