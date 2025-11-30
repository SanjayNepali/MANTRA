# apps/messaging/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import (
    Conversation, Message, MessageRequest
)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'participant_names', 'is_group', 'is_active',
                   'last_message_at', 'created_at']
    list_filter = ['is_group', 'is_active', 'created_at']
    search_fields = ['title', 'participants__username']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at', 'updated_at', 'last_message_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'is_group', 'is_active')
        }),
        ('Participants', {
            'fields': ('participants',)
        }),
        ('Group Settings', {
            'fields': ('group_admin', 'group_image'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_message_at'),
            'classes': ('collapse',)
        }),
    )

    def participant_names(self, obj):
        return ', '.join([p.username for p in obj.participants.all()[:5]])
    participant_names.short_description = 'Participants'

    actions = ['activate_conversations', 'deactivate_conversations']

    def activate_conversations(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} conversation(s) activated.')
    activate_conversations.short_description = 'Activate Conversations'

    def deactivate_conversations(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} conversation(s) deactivated.')
    deactivate_conversations.short_description = 'Deactivate Conversations'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'conversation', 'content_preview',
                   'is_read', 'is_deleted', 'created_at']
    list_filter = ['is_read', 'is_deleted', 'created_at']
    search_fields = ['sender__username', 'content']
    readonly_fields = ['created_at', 'read_at', 'edited_at', 'deleted_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Message Info', {
            'fields': ('conversation', 'sender')
        }),
        ('Content', {
            'fields': ('content', 'attachment')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_deleted', 'deleted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at')
        }),
    )

    def content_preview(self, obj):
        if obj.is_deleted:
            return "This message was deleted"
        return obj.content[:50] if obj.content else "-"
    content_preview.short_description = 'Content'

    actions = ['mark_as_read', 'soft_delete_messages']

    def mark_as_read(self, request, queryset):
        now = timezone.now()
        queryset.update(is_read=True, read_at=now)
        self.message_user(request, f'{queryset.count()} message(s) marked as read.')
    mark_as_read.short_description = 'Mark as Read'

    def soft_delete_messages(self, request, queryset):
        now = timezone.now()
        queryset.update(is_deleted=True, deleted_at=now)
        self.message_user(request, f'{queryset.count()} message(s) deleted.')
    soft_delete_messages.short_description = 'Delete Messages'


@admin.register(MessageRequest)
class MessageRequestAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'status', 'created_at', 'responded_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_user__username', 'to_user__username', 'message']
    readonly_fields = ['created_at', 'responded_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Users', {
            'fields': ('from_user', 'to_user')
        }),
        ('Request', {
            'fields': ('message', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'responded_at')
        }),
    )

    actions = ['mark_as_accepted', 'mark_as_rejected']

    def mark_as_accepted(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status='pending').update(status='accepted', responded_at=now)
        self.message_user(request, f'{updated} request(s) accepted.')
    mark_as_accepted.short_description = 'Accept Requests'

    def mark_as_rejected(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status='pending').update(status='rejected', responded_at=now)
        self.message_user(request, f'{updated} request(s) rejected.')
    mark_as_rejected.short_description = 'Reject Requests'