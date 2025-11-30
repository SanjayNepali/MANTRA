/**
 * MANTRA WebSocket Client Library
 * Handles real-time chat, notifications, and online status
 */

// Base WebSocket Manager
class WebSocketManager {
    constructor(url, options = {}) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
        this.reconnectDelay = options.reconnectDelay || 3000;
        this.heartbeatInterval = options.heartbeatInterval || 30000;
        this.heartbeatTimer = null;
        this.isManualClose = false;

        this.onOpen = options.onOpen || (() => {});
        this.onClose = options.onClose || (() => {});
        this.onError = options.onError || (() => {});
        this.onMessage = options.onMessage || (() => {});
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}${this.url}`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = (e) => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.startHeartbeat();
            this.onOpen(e);
        };

        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.onMessage(data);
            } catch (err) {
                console.error('Error parsing WebSocket message:', err);
            }
        };

        this.ws.onerror = (e) => {
            console.error('WebSocket error:', e);
            this.onError(e);
        };

        this.ws.onclose = (e) => {
            console.log('WebSocket closed');
            this.stopHeartbeat();
            this.onClose(e);

            if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnect();
            }
        };
    }

    reconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected. Cannot send message.');
        }
    }

    close() {
        this.isManualClose = true;
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
        }
    }

    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            this.send({ type: 'heartbeat' });
        }, this.heartbeatInterval);
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
}

// Chat WebSocket Client
class ChatWebSocket extends WebSocketManager {
    constructor(conversationId, options = {}) {
        super(`/ws/chat/${conversationId}/`, options);
        this.conversationId = conversationId;
        this.typingTimeout = null;

        // Event handlers
        this.onNewMessage = options.onNewMessage || (() => {});
        this.onTypingIndicator = options.onTypingIndicator || (() => {});
        this.onReadReceipt = options.onReadReceipt || (() => {});
        this.onUserStatus = options.onUserStatus || (() => {});
        this.onMessageDeleted = options.onMessageDeleted || (() => {});
        this.onMessageEdited = options.onMessageEdited || (() => {});
        this.onConnectionEstablished = options.onConnectionEstablished || (() => {});
        this.onMessageError = options.onMessageError || (() => {});

        // Override onMessage to route to specific handlers
        this.onMessage = (data) => this.handleMessage(data);
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                this.onConnectionEstablished(data);
                break;
            case 'message':
                this.onNewMessage(data.message);
                break;
            case 'typing':
                this.onTypingIndicator(data.user, data.is_typing);
                break;
            case 'read':
                this.onReadReceipt(data.message_ids, data.user_id);
                break;
            case 'user_status':
                this.onUserStatus(data.user_id, data.status);
                break;
            case 'message_deleted':
                this.onMessageDeleted(data.message_id, data.deleted_by);
                break;
            case 'message_edited':
                this.onMessageEdited(data.message);
                break;
            case 'error':
                this.onMessageError(data.message);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    sendMessage(content, replyTo = null) {
        this.send({
            type: 'message',
            message: content,
            reply_to: replyTo
        });
    }

    sendTyping(isTyping = true) {
        this.send({
            type: 'typing',
            is_typing: isTyping
        });
    }

    markAsRead(messageIds) {
        this.send({
            type: 'read',
            message_ids: Array.isArray(messageIds) ? messageIds : [messageIds]
        });
    }

    deleteMessage(messageId) {
        this.send({
            type: 'delete_message',
            message_id: messageId
        });
    }

    editMessage(messageId, newContent) {
        this.send({
            type: 'edit_message',
            message_id: messageId,
            new_content: newContent
        });
    }

    // Helper to handle typing with auto-stop
    handleTypingInput() {
        if (!this.typingTimeout) {
            this.sendTyping(true);
        }

        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.sendTyping(false);
            this.typingTimeout = null;
        }, 2000);
    }
}

// Notification WebSocket Client
class NotificationWebSocket extends WebSocketManager {
    constructor(options = {}) {
        super('/ws/notifications/', options);

        this.onNewNotification = options.onNewNotification || (() => {});
        this.onUnreadCountUpdate = options.onUnreadCountUpdate || (() => {});
        this.onRecentNotifications = options.onRecentNotifications || (() => {});
        this.onConnectionEstablished = options.onConnectionEstablished || (() => {});

        this.onMessage = (data) => this.handleMessage(data);
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection':
            case 'connection_established':
                this.onConnectionEstablished(data.unread_count, data.recent_notifications);
                this.onUnreadCountUpdate(data.unread_count);
                break;
            case 'notification':
                this.onNewNotification(data.notification);
                break;
            case 'update_count':
                this.onUnreadCountUpdate(data.unread_count);
                break;
            case 'recent_notifications':
                this.onRecentNotifications(data.notifications);
                break;
            default:
                console.log('Unknown notification type:', data.type);
        }
    }

    markAsRead(notificationId) {
        this.send({
            action: 'mark_read',
            notification_id: notificationId
        });
    }

    markAllAsRead() {
        this.send({
            action: 'mark_all_read'
        });
    }

    deleteNotification(notificationId) {
        this.send({
            action: 'delete',
            notification_id: notificationId
        });
    }

    getRecent() {
        this.send({
            action: 'get_recent'
        });
    }
}

// Online Status WebSocket Client
class OnlineStatusWebSocket extends WebSocketManager {
    constructor(options = {}) {
        super('/ws/status/', options);

        this.onStatusUpdate = options.onStatusUpdate || (() => {});
        this.onFriendStatusUpdate = options.onFriendStatusUpdate || (() => {});

        this.onMessage = (data) => this.handleMessage(data);
    }

    handleMessage(data) {
        switch (data.type) {
            case 'status_update':
                this.onStatusUpdate(data.status, data.last_seen);
                break;
            case 'friend_status_update':
                this.onFriendStatusUpdate(data.user_id, data.status);
                break;
            case 'heartbeat_ack':
                // Heartbeat acknowledged
                break;
            default:
                console.log('Unknown status message:', data.type);
        }
    }
}

// Notification Toast Manager
class NotificationToast {
    constructor() {
        this.toastContainer = this.createToastContainer();
    }

    createToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    }

    show(notification) {
        const toast = document.createElement('div');
        toast.className = 'toast show';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="toast-header">
                <i class='bx ${notification.icon || 'bx-bell'} me-2' style='color: ${notification.color || '#FFB6C1'};'></i>
                <strong class="me-auto">${notification.title || 'Notification'}</strong>
                <small>${this.getTimeAgo(notification.created_at)}</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${notification.message || notification.description}
            </div>
        `;

        this.toastContainer.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);

        // Play notification sound
        this.playNotificationSound();
    }

    getTimeAgo(dateStr) {
        const date = new Date(dateStr);
        const seconds = Math.floor((new Date() - date) / 1000);

        if (seconds < 60) return 'just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        return `${Math.floor(hours / 24)}d ago`;
    }

    playNotificationSound() {
        // Optional: Add notification sound
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {});
        } catch (e) {}
    }
}

// Utility functions
const WebSocketUtils = {
    formatMessageTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    linkify(text) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        return text.replace(urlRegex, '<a href="$1" target="_blank">$1</a>');
    },

    createMessageElement(message, isOwn = false) {
        const div = document.createElement('div');
        div.className = `message-bubble ${isOwn ? 'sent' : 'received'}`;
        div.dataset.messageId = message.id;

        div.innerHTML = `
            ${!isOwn ? `
                <div class="message-avatar">
                    <img src="${message.sender.profile_picture || '/static/images/default-avatar.png'}"
                         alt="${message.sender.full_name}">
                </div>
            ` : ''}

            <div class="message-content-wrapper">
                ${!isOwn ? `<div class="message-sender-name">${message.sender.full_name}</div>` : ''}

                <div class="message-content">
                    <p class="message-text">${this.linkify(this.escapeHtml(message.content))}</p>
                </div>

                <div class="message-meta">
                    <span class="message-time">${this.formatMessageTime(message.created_at)}</span>
                    ${isOwn ? `
                        <span class="message-status ${message.is_read ? 'read' : 'sent'}">
                            <i class='bx ${message.is_read ? 'bx-check-double' : 'bx-check'}'></i>
                        </span>
                    ` : ''}
                </div>
            </div>

            ${isOwn ? `
                <div class="message-avatar">
                    <img src="${message.sender.profile_picture || '/static/images/default-avatar.png'}"
                         alt="${message.sender.full_name}">
                </div>
            ` : ''}
        `;

        return div;
    },

    scrollToBottom(element, smooth = true) {
        element.scrollTo({
            top: element.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    },

    updateUnreadBadge(count) {
        const badges = document.querySelectorAll('.unread-badge, .notification-badge');
        badges.forEach(badge => {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        });
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        WebSocketManager,
        ChatWebSocket,
        NotificationWebSocket,
        OnlineStatusWebSocket,
        NotificationToast,
        WebSocketUtils
    };
}
