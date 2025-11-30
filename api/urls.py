# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    # Authentication
    UserRegistrationView,
    UserLoginView,
    UserProfileViewSet,
    
    # Celebrities
    CelebrityViewSet,
    SubscriptionViewSet,
    
    # Fans
    FanViewSet,
    RecommendationView,
    
    # Posts
    PostViewSet,
    FeedView,
    
    # Fanclubs
    FanClubViewSet,
    
    # Events
    EventViewSet,
    EventBookingViewSet,
    
    # Merchandise
    MerchandiseViewSet,
    OrderViewSet,
    
    # Messaging
    ConversationViewSet,
    MessageViewSet,
    
    # Notifications
    NotificationViewSet,
    
    # Analytics
    AnalyticsView,
    
    # Search
    SearchView,
)

router = DefaultRouter()
router.register('users', UserProfileViewSet, basename='user')
router.register('celebrities', CelebrityViewSet, basename='celebrity')
router.register('subscriptions', SubscriptionViewSet, basename='subscription')
router.register('fans', FanViewSet, basename='fan')
router.register('posts', PostViewSet, basename='post')
router.register('fanclubs', FanClubViewSet, basename='fanclub')
router.register('events', EventViewSet, basename='event')
router.register('bookings', EventBookingViewSet, basename='booking')
router.register('merchandise', MerchandiseViewSet, basename='merchandise')
router.register('orders', OrderViewSet, basename='order')
router.register('conversations', ConversationViewSet, basename='conversation')
router.register('messages', MessageViewSet, basename='message')
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # Authentication
    path('auth/register/', UserRegistrationView.as_view(), name='api_register'),
    path('auth/login/', UserLoginView.as_view(), name='api_login'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Custom endpoints
    path('feed/', FeedView.as_view(), name='api_feed'),
    path('recommendations/', RecommendationView.as_view(), name='api_recommendations'),
    path('analytics/', AnalyticsView.as_view(), name='api_analytics'),
    path('search/', SearchView.as_view(), name='api_search'),
    
    # Router URLs
    path('', include(router.urls)),
]