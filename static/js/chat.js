// <!-- static/js/chat.js -->

// MANTRA Chat System

class ChatManager {
    constructor(conversationId, currentUser) {
        this.conversationId = conversationId;
        this.currentUser = currentUser;
        this.socket = null;
        this.typingTimer = null;
        this.isTyping = false;
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.scrollToBottom();
    }
    
    connectWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws/chat/${this.conversationId}/`;
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('Chat connected');
        };
        
        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = () => {
            console.log('Chat disconnected');
            this.reconnect();
        };
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'message':
                this.addMessage(data.message);
                break;
            case 'typing':
                this.updateTypingIndicator(data);
                break;
            case 'read':
                this.updateReadStatus(data);
                break;
        }
    }
    
    setupEventListeners() {
        const messageForm = document.getElementById('message-form');
        const messageInput = document.getElementById('message-input');
        
        if (messageForm) {
            messageForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }
        
        if (messageInput) {
            messageInput.addEventListener('input', () => {
                this.handleTyping();
            });
        }
    }
    
    sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (message) {
            this.socket.send(JSON.stringify({
                type: 'message',
                message: message
            }));
            
            input.value = '';
            this.stopTyping();
        }
    }
    
    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            this.socket.send(JSON.stringify({
                type: 'typing',
                is_typing: true
            }));
        }
        
        clearTimeout(this.typingTimer);
        this.typingTimer = setTimeout(() => {
            this.stopTyping();
        }, 1000);
    }
    
    stopTyping() {
        if (this.isTyping) {
            this.isTyping = false;
            this.socket.send(JSON.stringify({
                type: 'typing',
                is_typing: false
            }));
        }
    }
    
    addMessage(message) {
        const container = document.getElementById('messages-container');
        const messageDiv = this.createMessageElement(message);
        
        container.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    createMessageElement(message) {
        const div = document.createElement('div');
        const isSent = message.sender.username === this.currentUser;
        
        div.className = `message ${isSent ? 'sent' : 'received'} fade-in`;
        div.innerHTML = `
            <div class="message-bubble">
                ${!isSent ? `<strong>${message.sender.username}</strong>` : ''}
                <p>${message.content}</p>
                <small>${this.formatTime(message.created_at)}</small>
            </div>
        `;
        
        return div;
    }
    
    updateTypingIndicator(data) {
        if (data.user.username === this.currentUser) return;
        
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.style.display = data.is_typing ? 'inline' : 'none';
            indicator.textContent = data.is_typing ? `${data.user.username} is typing...` : '';
        }
    }
    
    updateReadStatus(data) {
        // Update read receipts
        const messages = document.querySelectorAll(`.message[data-id="${data.message_id}"]`);
        messages.forEach(msg => {
            msg.classList.add('read');
        });
    }
    
    scrollToBottom() {
        const container = document.getElementById('messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    reconnect() {
        setTimeout(() => {
            this.connectWebSocket();
        }, 3000);
    }
}

// Initialize chat if on conversation page
if (document.getElementById('messages-container')) {
    const conversationId = document.querySelector('[data-conversation-id]').dataset.conversationId;
    const currentUser = document.querySelector('[data-current-user]').dataset.currentUser;
    
    new ChatManager(conversationId, currentUser);
}