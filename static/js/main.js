// MANTRA/static/js/main.js - Main JavaScript

// ========== Global Configuration ==========
const MANTRA = {
    baseURL: window.location.origin,
    csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
    user: null,
    notifications: {
        count: 0,
        unread: []
    },
    websocket: null
};

// ========== Utility Functions ==========
const Utils = {
    // Format date/time
    formatDate: (date) => {
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return new Date(date).toLocaleDateString(undefined, options);
    },
    
    formatTime: (date) => {
        const options = { hour: '2-digit', minute: '2-digit' };
        return new Date(date).toLocaleTimeString(undefined, options);
    },
    
    timeAgo: (date) => {
        const seconds = Math.floor((new Date() - new Date(date)) / 1000);
        const intervals = {
            year: 31536000,
            month: 2592000,
            week: 604800,
            day: 86400,
            hour: 3600,
            minute: 60
        };
        
        for (const [unit, value] of Object.entries(intervals)) {
            const interval = Math.floor(seconds / value);
            if (interval >= 1) {
                return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
            }
        }
        return 'just now';
    },
    
    // Format numbers
    formatNumber: (num) => {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    },
    
    // Show toast notification
    showToast: (message, type = 'info') => {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class='bx ${Utils.getToastIcon(type)}'></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    getToastIcon: (type) => {
        const icons = {
            success: 'bx-check-circle',
            error: 'bx-error-circle',
            warning: 'bx-error',
            info: 'bx-info-circle'
        };
        return icons[type] || icons.info;
    },
    
    // Debounce function
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // API request helper
    apiRequest: async (url, options = {}) => {
        const defaultOptions = {
            headers: {
                'X-CSRFToken': MANTRA.csrfToken,
                'Content-Type': 'application/json',
            }
        };
        
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
};

// ========== Post Interactions ==========
const PostManager = {
    // Like/Unlike post
    toggleLike: async (postId, element) => {
        try {
            const response = await Utils.apiRequest(`/posts/${postId}/like/`, {
                method: 'POST'
            });
            
            if (response.liked) {
                element.classList.add('liked');
                element.innerHTML = `<i class='bx bxs-heart'></i> ${response.likes_count}`;
            } else {
                element.classList.remove('liked');
                element.innerHTML = `<i class='bx bx-heart'></i> ${response.likes_count}`;
            }
        } catch (error) {
            Utils.showToast('Error liking post', 'error');
        }
    },
    
    // Share post
    sharePost: (postId) => {
        const shareUrl = `${MANTRA.baseURL}/posts/${postId}`;
        
        if (navigator.share) {
            navigator.share({
                title: 'Check out this post on MANTRA',
                url: shareUrl
            }).catch(() => {});
        } else {
            // Copy to clipboard
            navigator.clipboard.writeText(shareUrl).then(() => {
                Utils.showToast('Link copied to clipboard', 'success');
            });
        }
    },
    
    // Save/Unsave post
    toggleSave: async (postId, element) => {
        try {
            const response = await Utils.apiRequest(`/posts/${postId}/save/`, {
                method: 'POST'
            });
            
            if (response.saved) {
                element.classList.add('saved');
                element.innerHTML = `<i class='bx bxs-bookmark'></i>`;
                Utils.showToast('Post saved', 'success');
            } else {
                element.classList.remove('saved');
                element.innerHTML = `<i class='bx bx-bookmark'></i>`;
                Utils.showToast('Post unsaved', 'info');
            }
        } catch (error) {
            Utils.showToast('Error saving post', 'error');
        }
    },
    
    // Load comments
    loadComments: async (postId) => {
        try {
            const response = await Utils.apiRequest(`/posts/${postId}/comments/`);
            const commentsContainer = document.getElementById(`comments-${postId}`);
            
            if (response.comments.length === 0) {
                commentsContainer.innerHTML = '<p class="text-muted">No comments yet</p>';
                return;
            }
            
            commentsContainer.innerHTML = response.comments.map(comment => `
                <div class="comment">
                    <div class="comment-header">
                        <img src="${comment.author.avatar}" alt="${comment.author.username}" class="avatar-sm">
                        <div>
                            <strong>${comment.author.username}</strong>
                            <small>${Utils.timeAgo(comment.created_at)}</small>
                        </div>
                    </div>
                    <p>${comment.content}</p>
                    <div class="comment-actions">
                        <button onclick="PostManager.likeComment('${comment.id}', this)">
                            <i class='bx bx-heart'></i> ${comment.likes_count}
                        </button>
                        <button onclick="PostManager.replyToComment('${comment.id}')">
                            <i class='bx bx-comment'></i> Reply
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            Utils.showToast('Error loading comments', 'error');
        }
    },
    
    // Post comment
    postComment: async (postId) => {
        const input = document.querySelector(`#comment-input-${postId}`);
        const content = input.value.trim();
        
        if (!content) {
            Utils.showToast('Please enter a comment', 'warning');
            return;
        }
        
        try {
            const response = await Utils.apiRequest(`/posts/${postId}/comments/`, {
                method: 'POST',
                body: JSON.stringify({ content })
            });
            
            input.value = '';
            await PostManager.loadComments(postId);
            Utils.showToast('Comment posted', 'success');
        } catch (error) {
            Utils.showToast('Error posting comment', 'error');
        }
    }
};

// ========== User Interactions ==========
const UserManager = {
    // Follow/Unfollow user
    toggleFollow: async (username, element) => {
        try {
            const response = await Utils.apiRequest(`/accounts/follow/${username}/`, {
                method: 'POST'
            });
            
            if (response.following) {
                element.textContent = 'Unfollow';
                element.classList.remove('btn-primary');
                element.classList.add('btn-outline');
            } else {
                element.textContent = 'Follow';
                element.classList.remove('btn-outline');
                element.classList.add('btn-primary');
            }
            
            Utils.showToast(response.message, 'success');
        } catch (error) {
            Utils.showToast('Error updating follow status', 'error');
        }
    },
    
    // Block user
    blockUser: async (username) => {
        if (!confirm(`Are you sure you want to block ${username}?`)) {
            return;
        }
        
        try {
            const response = await Utils.apiRequest(`/accounts/block/${username}/`, {
                method: 'POST'
            });
            
            Utils.showToast(`${username} has been blocked`, 'success');
            setTimeout(() => window.location.reload(), 1500);
        } catch (error) {
            Utils.showToast('Error blocking user', 'error');
        }
    }
};

// ========== Real-time Features ==========
const RealtimeManager = {
    // Initialize WebSocket connection
    initWebSocket: () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        MANTRA.websocket = new WebSocket(wsUrl);
        
        MANTRA.websocket.onopen = () => {
            console.log('WebSocket connected');
        };
        
        MANTRA.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            RealtimeManager.handleWebSocketMessage(data);
        };
        
        MANTRA.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        MANTRA.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            // Attempt to reconnect after 3 seconds
            setTimeout(() => RealtimeManager.initWebSocket(), 3000);
        };
    },
    
    // Handle incoming WebSocket messages
    handleWebSocketMessage: (data) => {
        switch (data.type) {
            case 'notification':
                RealtimeManager.showNotification(data.notification);
                RealtimeManager.updateNotificationCount();
                break;
                
            case 'message':
                RealtimeManager.showNewMessage(data.message);
                break;
                
            case 'online_status':
                RealtimeManager.updateOnlineStatus(data.user_id, data.is_online);
                break;
        }
    },
    
    // Show new notification
    showNotification: (notification) => {
        // Update notification badge
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            const count = parseInt(badge.textContent) || 0;
            badge.textContent = count + 1;
            badge.style.display = 'block';
        }
        
        // Show toast
        Utils.showToast(notification.message, 'info');
        
        // Play notification sound
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.play().catch(() => {});
    },
    
    // Update notification count
    updateNotificationCount: async () => {
        try {
            const response = await Utils.apiRequest('/notifications/count/');
            const badge = document.querySelector('.notification-badge');
            
            if (badge) {
                if (response.count > 0) {
                    badge.textContent = response.count;
                    badge.style.display = 'block';
                } else {
                    badge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error updating notification count:', error);
        }
    }
};

// ========== Search Functionality ==========
const SearchManager = {
    // Global search
    performSearch: Utils.debounce(async (query) => {
        if (query.length < 2) {
            SearchManager.hideResults();
            return;
        }
        
        try {
            const response = await Utils.apiRequest(`/api/v1/search/?q=${encodeURIComponent(query)}`);
            SearchManager.displayResults(response);
        } catch (error) {
            console.error('Search error:', error);
        }
    }, 300),
    
    // Display search results
    displayResults: (results) => {
        const container = document.getElementById('search-results');
        if (!container) return;
        
        if (results.users.length === 0 && results.posts.length === 0) {
            container.innerHTML = '<p class="text-muted">No results found</p>';
            container.classList.add('show');
            return;
        }
        
        let html = '';
        
        if (results.users.length > 0) {
            html += '<div class="search-section"><h5>Users</h5>';
            results.users.forEach(user => {
                html += `
                    <a href="/profile/${user.username}" class="search-item">
                        <img src="${user.avatar}" alt="${user.username}" class="avatar-sm">
                        <div>
                            <strong>${user.username}</strong>
                            ${user.is_verified ? '<i class="bx bxs-badge-check"></i>' : ''}
                            <small>${user.user_type}</small>
                        </div>
                    </a>
                `;
            });
            html += '</div>';
        }
        
        if (results.posts.length > 0) {
            html += '<div class="search-section"><h5>Posts</h5>';
            results.posts.forEach(post => {
                html += `
                    <a href="/posts/${post.id}" class="search-item">
                        <p>${post.content.substring(0, 100)}...</p>
                        <small>by @${post.author.username}</small>
                    </a>
                `;
            });
            html += '</div>';
        }
        
        container.innerHTML = html;
        container.classList.add('show');
    },
    
    // Hide search results
    hideResults: () => {
        const container = document.getElementById('search-results');
        if (container) {
            container.classList.remove('show');
        }
    }
};

// ========== Form Handlers ==========
const FormManager = {
    // Handle form submission with loading state
    handleSubmit: async (formId, callback) => {
        const form = document.getElementById(formId);
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = form.querySelector('[type="submit"]');
            const originalText = submitBtn.textContent;
            
            // Show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-sm"></span> Processing...';
            
            try {
                const formData = new FormData(form);
                await callback(formData);
            } catch (error) {
                Utils.showToast('An error occurred', 'error');
            } finally {
                // Restore button
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    },
    
    // Image preview
    setupImagePreview: (inputId, previewId) => {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        
        if (!input || !preview) return;
        
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                
                reader.onload = (e) => {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                };
                
                reader.readAsDataURL(file);
            }
        });
    },
    
    // Character counter
    setupCharacterCounter: (inputId, counterId, maxLength) => {
        const input = document.getElementById(inputId);
        const counter = document.getElementById(counterId);
        
        if (!input || !counter) return;
        
        const updateCounter = () => {
            const remaining = maxLength - input.value.length;
            counter.textContent = `${remaining} characters remaining`;
            
            if (remaining < 20) {
                counter.style.color = 'var(--danger)';
            } else {
                counter.style.color = 'var(--text-muted)';
            }
        };
        
        input.addEventListener('input', updateCounter);
        updateCounter();
    }
};

// ========== Modal Manager ==========
const ModalManager = {
    // Open modal
    open: (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    },
    
    // Close modal
    close: (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    },
    
    // Initialize modal triggers
    init: () => {
        // Close on background click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    ModalManager.close(modal.id);
                }
            });
        });
        
        // Close buttons
        document.querySelectorAll('[data-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const modal = btn.closest('.modal');
                if (modal) {
                    ModalManager.close(modal.id);
                }
            });
        });
    }
};

// ========== Initialize on DOM Ready ==========
document.addEventListener('DOMContentLoaded', () => {
    // Initialize components
    ModalManager.init();
    
    // Initialize WebSocket if user is authenticated
    const userElement = document.getElementById('user-data');
    if (userElement) {
        MANTRA.user = JSON.parse(userElement.textContent);
        RealtimeManager.initWebSocket();
        RealtimeManager.updateNotificationCount();
    }
    
    // Setup search
    const searchInput = document.querySelector('.search-form input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            SearchManager.performSearch(e.target.value);
        });
    }
    
    // Setup infinite scroll
    if (document.querySelector('.infinite-scroll')) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Load more content
                    console.log('Load more content');
                }
            });
        });
        
        const sentinel = document.querySelector('.scroll-sentinel');
        if (sentinel) {
            observer.observe(sentinel);
        }
    }
    
    // Initialize tooltips
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', (e) => {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = e.target.dataset.tooltip;
            document.body.appendChild(tooltip);
            
            const rect = e.target.getBoundingClientRect();
            tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
            
            e.target.addEventListener('mouseleave', () => {
                tooltip.remove();
            }, { once: true });
        });
    });
    
    // Auto-hide alerts
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            alert.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        });
    }, 5000);
    
    console.log('MANTRA initialized successfully');
});

// Export for use in other scripts
window.MANTRA = MANTRA;
window.Utils = Utils;
window.PostManager = PostManager;
window.UserManager = UserManager;
window.ModalManager = ModalManager;