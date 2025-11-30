# apps/notifications/serializers.py

from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    icon = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'sender', 'sender_username', 'notification_type',
                 'message', 'description', 'target_id', 'target_url',
                 'is_read', 'created_at', 'icon', 'color']
    
    def get_icon(self, obj):
        return obj.get_icon()
    
    def get_color(self, obj):
        return obj.get_color()