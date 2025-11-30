# apps/messaging/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from asgiref.sync import async_to_sync

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat with enhanced features"""

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        # Check if user has access to this conversation
        if not await self.user_has_access():
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Update user online status
        await self.update_online_status(True)

        await self.accept()

        # Send connection status with user info
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat',
            'user_id': str(self.user.id),
            'participants': await self.get_conversation_participants()
        }))

        # Notify other participants that user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'status': 'online'
            }
        )

    async def disconnect(self, close_code):
        # Update user offline status
        await self.update_online_status(False)

        # Notify other participants that user is offline
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'status': 'offline'
            }
        )

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')

        if message_type == 'message':
            await self.handle_message(text_data_json)
        elif message_type == 'typing':
            await self.handle_typing(text_data_json)
        elif message_type == 'read':
            await self.handle_read_receipt(text_data_json)
        elif message_type == 'delete_message':
            await self.handle_delete_message(text_data_json)
        elif message_type == 'edit_message':
            await self.handle_edit_message(text_data_json)

    async def handle_message(self, data):
        message_content = data['message']

        # Analyze message sentiment (if AI moderation is enabled)
        sentiment_score = await self.analyze_message_sentiment(message_content)

        # Check if message should be blocked
        if sentiment_score and sentiment_score.get('toxicity', 0) > 0.8:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message contains inappropriate content and cannot be sent.'
            }))
            return

        # Save message to database
        message = await self.save_message(message_content, sentiment_score)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'content': message.content,
                    'sender': {
                        'id': str(message.sender.id),
                        'username': message.sender.username,
                        'full_name': message.sender.get_full_name(),
                        'profile_picture': message.sender.profile_picture.url if message.sender.profile_picture else None,
                        'is_verified': message.sender.is_verified,
                        'user_type': message.sender.user_type
                    },
                    'created_at': message.created_at.isoformat(),
                    'is_read': False,
                    'sentiment': sentiment_score
                }
            }
        )

        # Send push notification to offline participants
        await self.send_push_notifications(message)

    async def handle_typing(self, data):
        # Send typing indicator to other users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': {
                    'id': str(self.user.id),
                    'username': self.user.username,
                    'full_name': self.user.get_full_name()
                },
                'is_typing': data.get('is_typing', False)
            }
        )

    async def handle_read_receipt(self, data):
        message_ids = data.get('message_ids', [])

        # Mark messages as read
        await self.mark_messages_read(message_ids)

        # Send read receipt to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'message_ids': message_ids,
                'user_id': str(self.user.id)
            }
        )

    async def handle_delete_message(self, data):
        message_id = data.get('message_id')

        # Delete message if user is sender
        if await self.delete_message(message_id):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'deleted_by': str(self.user.id)
                }
            )

    async def handle_edit_message(self, data):
        message_id = data.get('message_id')
        new_content = data.get('new_content')

        # Edit message if user is sender
        edited_message = await self.edit_message(message_id, new_content)
        if edited_message:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message': {
                        'id': message_id,
                        'new_content': new_content,
                        'edited_at': edited_message.edited_at.isoformat()
                    }
                }
            )

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        # Don't send typing indicator to the sender
        if event['user']['id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read',
            'message_ids': event['message_ids'],
            'user_id': event['user_id']
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'status': event['status']
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by']
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message']
        }))

    @database_sync_to_async
    def user_has_access(self):
        from apps.messaging.models import Conversation
        from apps.accounts.models import UserFollowing

        try:
            conversation = Conversation.objects.get(id=self.conversation_id)

            # Check if user is participant
            if self.user in conversation.participants.all():
                # For celebrity-fan conversations, check mutual follow
                other_participant = conversation.participants.exclude(id=self.user.id).first()
                if other_participant:
                    # Check if both users follow each other
                    is_following = UserFollowing.objects.filter(
                        follower=self.user,
                        following=other_participant,
                        is_active=True
                    ).exists()

                    is_followed_back = UserFollowing.objects.filter(
                        follower=other_participant,
                        following=self.user,
                        is_active=True
                    ).exists()

                    return is_following and is_followed_back
                return True
            return False
        except:
            return False

    @database_sync_to_async
    def get_conversation_participants(self):
        from apps.messaging.models import Conversation
        conversation = Conversation.objects.get(id=self.conversation_id)
        participants = []

        for participant in conversation.participants.all():
            participants.append({
                'id': str(participant.id),
                'username': participant.username,
                'full_name': participant.get_full_name(),
                'profile_picture': participant.profile_picture.url if participant.profile_picture else None,
                'is_online': participant.is_online,
                'user_type': participant.user_type,
                'is_verified': participant.is_verified
            })

        return participants

    @database_sync_to_async
    def save_message(self, content, sentiment_score=None):
        from apps.messaging.models import Conversation, Message

        conversation = Conversation.objects.get(id=self.conversation_id)

        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content
        )

        # Store sentiment score if available
        if sentiment_score:
            message.metadata = {'sentiment': sentiment_score}
            message.save()

        # Update conversation
        conversation.last_message = content
        conversation.updated_at = timezone.now()
        conversation.save()

        return message

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        from apps.messaging.models import Message
        Message.objects.filter(
            id__in=message_ids,
            conversation_id=self.conversation_id
        ).exclude(sender=self.user).update(
            is_read=True,
            read_at=timezone.now()
        )

    @database_sync_to_async
    def delete_message(self, message_id):
        from apps.messaging.models import Message
        try:
            message = Message.objects.get(
                id=message_id,
                sender=self.user,
                conversation_id=self.conversation_id
            )
            message.is_deleted = True
            message.deleted_at = timezone.now()
            message.save()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        from apps.messaging.models import Message
        try:
            message = Message.objects.get(
                id=message_id,
                sender=self.user,
                conversation_id=self.conversation_id
            )
            message.content = new_content
            message.is_edited = True
            message.edited_at = timezone.now()
            message.save()
            return message
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def update_online_status(self, is_online):
        self.user.is_online = is_online
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=['is_online', 'last_seen'])

    @database_sync_to_async
    def analyze_message_sentiment(self, content):
        try:
            from algorithms.sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            return analyzer.analyze_content(content)
        except:
            return None

    @database_sync_to_async
    def send_push_notifications(self, message):
        from apps.messaging.models import Conversation
        from utils.helpers import send_notification

        conversation = Conversation.objects.get(id=self.conversation_id)

        # Get offline participants
        offline_participants = conversation.participants.exclude(
            id=self.user.id
        ).filter(is_online=False)

        for participant in offline_participants:
            send_notification(
                participant,
                'message',
                f'New message from {self.user.get_full_name()}',
                message.content[:100],
                message
            )


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group_name = f'notifications_{self.user.id}'

        # Join user's notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        # Send unread notifications count
        unread_count = await self.get_unread_count()
        recent_notifications = await self.get_recent_notifications()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'unread_count': unread_count,
            'recent_notifications': recent_notifications
        }))

    async def disconnect(self, close_code):
        # Leave notification group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')

        if action == 'mark_read':
            notification_id = text_data_json.get('notification_id')
            await self.mark_notification_read(notification_id)
        elif action == 'mark_all_read':
            await self.mark_all_notifications_read()
        elif action == 'delete':
            notification_id = text_data_json.get('notification_id')
            await self.delete_notification(notification_id)

    async def notification_message(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    @database_sync_to_async
    def get_unread_count(self):
        from apps.notifications.models import Notification
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()

    @database_sync_to_async
    def get_recent_notifications(self):
        from apps.notifications.models import Notification
        notifications = Notification.objects.filter(
            user=self.user
        ).order_by('-created_at')[:10]

        return [{
            'id': str(n.id),
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'time_ago': self._get_time_ago(n.created_at)
        } for n in notifications]

    def _get_time_ago(self, created_at):
        from django.utils import timezone
        from django.contrib.humanize.templatetags.humanize import naturaltime
        return naturaltime(created_at)

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        from apps.notifications.models import Notification
        updated = Notification.objects.filter(
            id=notification_id,
            user=self.user
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return updated > 0

    @database_sync_to_async
    def mark_all_notifications_read(self):
        from apps.notifications.models import Notification
        Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )

    @database_sync_to_async
    def delete_notification(self, notification_id):
        from apps.notifications.models import Notification
        Notification.objects.filter(
            id=notification_id,
            user=self.user
        ).delete()


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for tracking online status"""

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.status_group_name = f'status_{self.user.id}'

        # Join status group
        await self.channel_layer.group_add(
            self.status_group_name,
            self.channel_name
        )

        # Update user online status
        await self.set_online_status(True)

        await self.accept()

        # Send initial status
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': 'online',
            'last_seen': timezone.now().isoformat()
        }))

    async def disconnect(self, close_code):
        # Update user offline status
        await self.set_online_status(False)

        # Leave status group
        await self.channel_layer.group_discard(
            self.status_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle heartbeat
        text_data_json = json.loads(text_data)
        if text_data_json.get('type') == 'heartbeat':
            await self.update_last_seen()
            await self.send(text_data=json.dumps({
                'type': 'heartbeat_ack',
                'timestamp': timezone.now().isoformat()
            }))

    @database_sync_to_async
    def set_online_status(self, is_online):
        self.user.is_online = is_online
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=['is_online', 'last_seen'])

        # Notify friends about status change
        from apps.accounts.models import UserFollowing
        # Get users this user is following
        following_ids = UserFollowing.objects.filter(
            follower=self.user
        ).values_list('following', flat=True)

        # Get users following this user
        follower_ids = UserFollowing.objects.filter(
            following=self.user
        ).values_list('follower', flat=True)

        # Combine both lists to get all friends
        friend_ids = list(following_ids) + list(follower_ids)
        friends = User.objects.filter(id__in=friend_ids).distinct()

        # Send status update to friends
        for friend in friends:
            channel_layer = self.channel_layer
            async_to_sync(channel_layer.group_send)(
                f'notifications_{friend.id}',
                {
                    'type': 'friend_status_update',
                    'user_id': str(self.user.id),
                    'status': 'online' if is_online else 'offline'
                }
            )

    @database_sync_to_async
    def update_last_seen(self):
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=['last_seen'])
