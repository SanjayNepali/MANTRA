# apps/posts/serializers.py

from rest_framework import serializers
from .models import Post, Comment, Like

class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = ['id', 'author', 'author_username', 'content', 'image', 'video',
                 'post_type', 'is_exclusive', 'likes_count', 'comments_count',
                 'views_count', 'is_liked', 'created_at']
        read_only_fields = ['author', 'likes_count', 'comments_count', 'views_count']
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(user=request.user, post=obj).exists()
        return False


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'author_username', 'content',
                 'parent', 'likes_count', 'created_at']
        read_only_fields = ['author', 'likes_count']