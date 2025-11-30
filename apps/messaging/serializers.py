# apps/messaging/serializers.py

from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_username',
                 'content', 'attachment', 'is_read', 'created_at']
        read_only_fields = ['sender']


class ConversationSerializer(serializers.ModelSerializer):
    participants_info = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'participants_info', 
                 'last_message', 'unread_count', 'created_at', 'updated_at']
    
    def get_participants_info(self, obj):
        from apps.accounts.serializers import UserSerializer
        return UserSerializer(obj.participants.all(), many=True).data
    
    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(
                is_read=False
            ).exclude(sender=request.user).count()
        return 0