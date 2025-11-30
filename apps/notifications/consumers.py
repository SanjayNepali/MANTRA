# apps/notifications/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f'notifications_{self.user.id}'
        
        # Join user notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send unread count on connect
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'unread_count': unread_count
        }))
    
    async def disconnect(self, close_code):
        # Leave notification group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'mark_read':
            notification_id = data.get('notification_id')
            await self.mark_notification_read(notification_id)
        elif action == 'mark_all_read':
            await self.mark_all_read()
        elif action == 'get_recent':
            await self.send_recent_notifications()
    
    async def send_notification(self, event):
        """Send notification to WebSocket"""
        notification = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification
        }))
    
    async def update_count(self, event):
        """Update unread count"""
        await self.send(text_data=json.dumps({
            'type': 'update_count',
            'unread_count': event['count']
        }))
    
    async def send_recent_notifications(self):
        """Send recent notifications to client"""
        notifications = await self.get_recent_notifications()
        
        await self.send(text_data=json.dumps({
            'type': 'recent_notifications',
            'notifications': notifications
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        from .models import Notification
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
        except Notification.DoesNotExist:
            pass
    
    @database_sync_to_async
    def mark_all_read(self):
        from .models import Notification
        from django.utils import timezone
        Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    @database_sync_to_async
    def get_recent_notifications(self):
        from .models import Notification
        notifications = Notification.objects.filter(
            recipient=self.user
        ).select_related('sender')[:20]
        
        return [{
            'id': str(n.id),
            'type': n.notification_type,
            'message': n.message,
            'description': n.description,
            'sender': {
                'username': n.sender.username if n.sender else 'System',
                'profile_picture': n.sender.profile_picture.url if n.sender and n.sender.profile_picture else None
            },
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'icon': n.get_icon(),
            'color': n.get_color(),
            'target_url': n.target_url
        } for n in notifications]