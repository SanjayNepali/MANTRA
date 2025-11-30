// static/js/websocket.js

class WebSocketManager {
    constructor() {
        this.sockets = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.userId = document.querySelector('meta[name="user-id"]')?.content;
        this.wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        this.baseUrl = `${this.wsScheme}://${window.location.host}`;
    }

    // Initialize all WebSocket connections
    init() {
        if (!this.userId) return;

        this.initNotifications();
        this.initOnlineStatus();
        this.setupHeartbeat();
    }

    // Initialize notifications WebSocket
    initNotifications() {
        const notificationSocket = new WebSocket(`${this.baseUrl}/ws/notifications/`);
        
        notificationSocket.onopen = () => {
            console.log('Notifications WebSocket connected');
            this.reconnectAttempts = 0;
        };

        notificationSocket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleNotification(data);
        };

        notificationSocket.onclose = () => {
            console.log('Notifications WebSocket disconnected');
            this.attemptReconnect('notifications', () => this.initNotifications());
        };

        notificationSocket.onerror = (e) => {
            console.error('Notifications WebSocket error:', e);
        };

        this.sockets.notifications = notificationSocket;
    }

    // Initialize online status WebSocket
    initOnlineStatus() {
        // TODO: Implement OnlineStatusConsumer in apps/messaging/consumers.py
        // Temporarily disabled to prevent WebSocket errors
        console.log('Status WebSocket disabled - implementation pending');
        return;

        /* Uncomment when OnlineStatusConsumer is implemented
        const statusSocket = new WebSocket(`${this.baseUrl}/ws/status/`);

        statusSocket.onopen = () => {
            console.log('Status WebSocket connected');
            this.updateOnlineIndicator(true);
        };

        statusSocket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'heartbeat_ack') {
                this.lastHeartbeatAck = Date.now();
            }
        };

        statusSocket.onclose = () => {
            console.log('Status WebSocket disconnected');
            this.updateOnlineIndicator(false);
            this.attemptReconnect('status', () => this.initOnlineStatus());
        };

        this.sockets.status = statusSocket;
        */
    }

    // Initialize chat WebSocket for specific conversation
    initChat(conversationId) {
        if (this.sockets.chat) {
            this.sockets.chat.close();
        }

        const chatSocket = new WebSocket(`${this.baseUrl}/ws/chat/${conversationId}/`);
        
        chatSocket.onopen = () => {
            console.log('Chat WebSocket connected');
            this.updateChatStatus('connected');
        };

        chatSocket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleChatMessage(data);
        };

        chatSocket.onclose = () => {
            console.log('Chat WebSocket disconnected');
            this.updateChatStatus('disconnected');
            this.attemptReconnect('chat', () => this.initChat(conversationId));
        };

        chatSocket.onerror = (e) => {
            console.error('Chat WebSocket error:', e);
            this.updateChatStatus('error');
        };

        this.sockets.chat = chatSocket;
        return chatSocket;
    }

    // Handle incoming notifications
    handleNotification(data) {
        switch (data.type) {
            case 'notification':
                this.showNotification(data.notification);
                this.updateNotificationBadge(1);
                this.playNotificationSound();
                break;
            
            case 'connection_established':
                this.updateNotificationBadge(data.unread_count);
                if (data.recent_notifications) {
                    this.displayRecentNotifications(data.recent_notifications);
                }
                break;
            
            case 'friend_status_update':
                this.updateFriendStatus(data.user_id, data.status);
                break;
        }
    }

    // Handle chat messages
    handleChatMessage(data) {
        switch (data.type) {
            case 'connection_established':
                this.updateParticipantsList(data.participants);
                break;
            
            case 'message':
                this.displayMessage(data.message);
                break;
            
            case 'typing':
                this.showTypingIndicator(data.user, data.is_typing);
                break;
            
            case 'read':
                this.markMessagesAsRead(data.message_ids, data.user_id);
                break;
            
            case 'user_status':
                this.updateUserStatus(data.user_id, data.status);
                break;
            
            case 'message_deleted':
                this.removeMessage(data.message_id);
                break;
            
            case 'message_edited':
                this.updateMessage(data.message);
                break;
            
            case 'error':
                this.showChatError(data.message);
                break;
        }
    }

    // Show browser notification
    showNotification(notification) {
        // Check if browser supports notifications
        if (!('Notification' in window)) return;

        // Request permission if needed
        if (Notification.permission === 'default') {
            Notification.requestPermission();
        }

        // Show notification if permitted
        if (Notification.permission === 'granted') {
            const n = new Notification(notification.title, {
                body: notification.message,
                icon: '/static/images/logo-icon.png',
                badge: '/static/images/badge-icon.png',
                tag: notification.id,
                requireInteraction: false
            });

            // Handle notification click
            n.onclick = () => {
                window.focus();
                this.handleNotificationClick(notification);
                n.close();
            };

            // Auto close after 5 seconds
            setTimeout(() => n.close(), 5000);
        }

        // Also show in-app notification
        this.showInAppNotification(notification);
    }

    // Show in-app notification
    showInAppNotification(notification) {
        const container = document.getElementById('notification-container') || this.createNotificationContainer();
        
        const notificationEl = document.createElement('div');
        notificationEl.className = 'app-notification animate__animated animate__slideInRight';
        notificationEl.innerHTML = `
            <div class="notification-content">
                <div class="notification-header">
                    <h6>${this.escapeHtml(notification.title)}</h6>
                    <button class="btn-close-notification" onclick="this.parentElement.parentElement.parentElement.remove()">
                        <i class='bx bx-x'></i>
                    </button>
                </div>
                <p>${this.escapeHtml(notification.message)}</p>
                <small class="text-muted">${notification.time_ago || 'Just now'}</small>
            </div>
        `;
        
        container.appendChild(notificationEl);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notificationEl.classList.add('animate__slideOutRight');
            setTimeout(() => notificationEl.remove(), 500);
        }, 5000);
    }

    // Create notification container
    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
        return container;
    }

    // Update notification badge
    updateNotificationBadge(count) {
        const badges = document.querySelectorAll('.notification-badge');
        badges.forEach(badge => {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        });
    }

    // Play notification sound
    playNotificationSound() {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.5;
        audio.play().catch(e => console.log('Could not play notification sound'));
    }

    // Send chat message
    sendMessage(content) {
        if (this.sockets.chat && this.sockets.chat.readyState === WebSocket.OPEN) {
            this.sockets.chat.send(JSON.stringify({
                type: 'message',
                message: content
            }));
            return true;
        }
        return false;
    }

    // Send typing indicator
    sendTypingIndicator(isTyping) {
        if (this.sockets.chat && this.sockets.chat.readyState === WebSocket.OPEN) {
            this.sockets.chat.send(JSON.stringify({
                type: 'typing',
                is_typing: isTyping
            }));
        }
    }

    // Mark messages as read
    markMessagesRead(messageIds) {
        if (this.sockets.chat && this.sockets.chat.readyState === WebSocket.OPEN) {
            this.sockets.chat.send(JSON.stringify({
                type: 'read',
                message_ids: messageIds
            }));
        }
    }

    // Delete message
    deleteMessage(messageId) {
        if (this.sockets.chat && this.sockets.chat.readyState === WebSocket.OPEN) {
            this.sockets.chat.send(JSON.stringify({
                type: 'delete_message',
                message_id: messageId
            }));
        }
    }

    // Edit message
    editMessage(messageId, newContent) {
        if (this.sockets.chat && this.sockets.chat.readyState === WebSocket.OPEN) {
            this.sockets.chat.send(JSON.stringify({
                type: 'edit_message',
                message_id: messageId,
                new_content: newContent
            }));
        }
    }

    // Display message in chat
    displayMessage(message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const messageEl = this.createMessageElement(message);
        chatMessages.appendChild(messageEl);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Mark as read if visible
        if (this.isElementInViewport(messageEl)) {
            this.markMessagesRead([message.id]);
        }
    }

    // Create message element
    createMessageElement(message) {
        const div = document.createElement('div');
        const isOwnMessage = message.sender.id === this.userId;
        
        div.className = `message ${isOwnMessage ? 'message-sent' : 'message-received'}`;
        div.dataset.messageId = message.id;
        
        div.innerHTML = `
            <div class="message-content">
                ${!isOwnMessage ? `
                    <div class="message-sender">
                        <img src="${message.sender.profile_picture || '/static/images/default-avatar.png'}" 
                             alt="${message.sender.username}" class="sender-avatar">
                        <span class="sender-name">${this.escapeHtml(message.sender.full_name)}</span>
                        ${message.sender.is_verified ? '<i class="bx bxs-badge-check verified-badge"></i>' : ''}
                    </div>
                ` : ''}
                <div class="message-text">${this.escapeHtml(message.content)}</div>
                <div class="message-meta">
                    <span class="message-time">${this.formatTime(message.created_at)}</span>
                    ${isOwnMessage ? `
                        <span class="message-status">
                            <i class='bx ${message.is_read ? 'bxs-check-double' : 'bx-check'}'></i>
                        </span>
                    ` : ''}
                </div>
            </div>
            ${isOwnMessage ? `
                <div class="message-actions">
                    <button class="btn-message-action" onclick="wsManager.editMessagePrompt('${message.id}')">
                        <i class='bx bx-edit'></i>
                    </button>
                    <button class="btn-message-action" onclick="wsManager.deleteMessage('${message.id}')">
                        <i class='bx bx-trash'></i>
                    </button>
                </div>
            ` : ''}
        `;
        
        return div;
    }

    // Show typing indicator
    showTypingIndicator(user, isTyping) {
        const typingIndicator = document.getElementById('typing-indicator');
        if (!typingIndicator) return;

        if (isTyping) {
            typingIndicator.innerHTML = `
                <div class="typing-user">
                    <span>${this.escapeHtml(user.full_name)} is typing</span>
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            `;
            typingIndicator.style.display = 'block';
        } else {
            typingIndicator.style.display = 'none';
        }
    }

    // Setup heartbeat
    setupHeartbeat() {
        // Send heartbeat every 30 seconds
        setInterval(() => {
            if (this.sockets.status && this.sockets.status.readyState === WebSocket.OPEN) {
                this.sockets.status.send(JSON.stringify({ type: 'heartbeat' }));
            }
        }, 30000);
    }

    // Attempt to reconnect
    attemptReconnect(socketName, reconnectFunc) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`Max reconnection attempts reached for ${socketName}`);
            this.showConnectionError();
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Attempting to reconnect ${socketName} in ${delay}ms...`);
        
        setTimeout(() => {
            reconnectFunc();
        }, delay);
    }

    // Show connection error
    showConnectionError() {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'connection-error';
        errorDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class='bx bx-wifi-off me-2'></i>
                Connection lost. Please refresh the page.
                <button class="btn btn-sm btn-light ms-3" onclick="location.reload()">
                    <i class='bx bx-refresh'></i> Refresh
                </button>
            </div>
        `;
        document.body.appendChild(errorDiv);
    }

    // Update online indicator
    updateOnlineIndicator(isOnline) {
        const indicators = document.querySelectorAll('.online-status');
        indicators.forEach(indicator => {
            if (isOnline) {
                indicator.classList.add('online');
                indicator.classList.remove('offline');
            } else {
                indicator.classList.add('offline');
                indicator.classList.remove('online');
            }
        });
    }

    // Utility functions
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        
        return date.toLocaleDateString();
    }

    isElementInViewport(el) {
        const rect = el.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    // Close all connections
    close() {
        Object.values(this.sockets).forEach(socket => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.close();
            }
        });
    }
}

// Initialize WebSocket manager
const wsManager = new WebSocketManager();
document.addEventListener('DOMContentLoaded', () => {
    wsManager.init();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    wsManager.close();
});