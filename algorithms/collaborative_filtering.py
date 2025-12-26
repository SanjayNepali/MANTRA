# algorithms/collaborative_filtering.py

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

class CollaborativeFilter:
    """Collaborative filtering for personalized recommendations"""
    
    def __init__(self, k_neighbors=10):
        self.k_neighbors = k_neighbors
        self.model = None
        self.user_item_matrix = None
    
    def fit(self, user_item_interactions):
        """
        Fit the collaborative filtering model
        user_item_interactions: sparse matrix or list of (user, item, rating)
        """
        if isinstance(user_item_interactions, list):
            # Convert to sparse matrix
            rows = [x[0] for x in user_item_interactions]
            cols = [x[1] for x in user_item_interactions]
            data = [x[2] for x in user_item_interactions]
            
            n_users = max(rows) + 1
            n_items = max(cols) + 1
            
            self.user_item_matrix = csr_matrix(
                (data, (rows, cols)),
                shape=(n_users, n_items)
            )
        else:
            self.user_item_matrix = user_item_interactions
        
        # Fit KNN model for item-based CF
        self.model = NearestNeighbors(
            n_neighbors=self.k_neighbors,
            algorithm='brute',
            metric='cosine'
        )
        self.model.fit(self.user_item_matrix.T)
    
    def predict_user_item_score(self, user_id, item_id):
        """Predict score for user-item pair"""
        if self.model is None:
            raise ValueError("Model not fitted")
        
        # Get similar items
        item_vector = self.user_item_matrix.T[item_id].toarray().flatten()
        distances, indices = self.model.kneighbors(
            item_vector.reshape(1, -1),
            n_neighbors=min(self.k_neighbors, self.user_item_matrix.shape[1] - 1)
        )
        
        # Calculate weighted average of ratings
        user_ratings = self.user_item_matrix[user_id, indices[0]].toarray()[0]
        weights = 1 - distances[0]  # Convert distance to similarity
        
        if weights.sum() > 0:
            predicted_score = np.dot(user_ratings, weights) / weights.sum()
        else:
            predicted_score = 0
        
        return predicted_score
    
    def recommend_items(self, user_id, n_recommendations=10):
        """Get top N recommendations for a user"""
        if self.model is None:
            raise ValueError("Model not fitted")
        
        # Get user's rated items
        user_ratings = self.user_item_matrix[user_id].toarray()[0]
        rated_items = np.where(user_ratings > 0)[0]
        
        # Get all items
        n_items = self.user_item_matrix.shape[1]
        all_items = set(range(n_items))
        unrated_items = list(all_items - set(rated_items))
        
        # Predict scores for unrated items
        predictions = []
        for item_id in unrated_items:
            score = self.predict_user_item_score(user_id, item_id)
            predictions.append((item_id, score))
        
        # Sort and return top N
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:n_recommendations]
    
    def find_similar_users(self, user_id, n_users=10):
        """Find similar users based on interaction patterns"""
        user_vector = self.user_item_matrix[user_id]
        
        # Calculate cosine similarity with all users
        similarities = []
        n_users_total = self.user_item_matrix.shape[0]
        
        for other_user_id in range(n_users_total):
            if other_user_id != user_id:
                other_vector = self.user_item_matrix[other_user_id]
                
                # Cosine similarity
                dot_product = user_vector.dot(other_vector.T).toarray()[0, 0]
                norm_user = np.sqrt(user_vector.dot(user_vector.T).toarray()[0, 0])
                norm_other = np.sqrt(other_vector.dot(other_vector.T).toarray()[0, 0])
                
                if norm_user > 0 and norm_other > 0:
                    similarity = dot_product / (norm_user * norm_other)
                    similarities.append((other_user_id, similarity))
        
        # Sort and return top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:n_users]