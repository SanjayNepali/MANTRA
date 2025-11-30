# api/views.py

from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User, UserFollowing
from apps.accounts.serializers import UserSerializer, UserRegistrationSerializer, LoginSerializer
from apps.celebrities.models import CelebrityProfile, Subscription
from apps.celebrities.serializers import CelebrityProfileSerializer, SubscriptionSerializer
from apps.fans.models import FanProfile, FanRecommendation
from apps.posts.models import Post, Like, Comment
from apps.posts.serializers import PostSerializer, CommentSerializer
from apps.fanclubs.models import FanClub, FanClubMembership
from apps.fanclubs.serializers import FanClubSerializer, FanClubMembershipSerializer
from apps.events.models import Event, EventBooking
from apps.events.serializers import EventSerializer, EventBookingSerializer
from apps.merchandise.models import Merchandise, MerchandiseOrder
from apps.merchandise.serializers import MerchandiseSerializer, OrderSerializer
from apps.messaging.models import Conversation, Message
from apps.messaging.serializers import ConversationSerializer, MessageSerializer
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer

from algorithms.recommendation import RecommendationEngine
from algorithms.sentiment import SentimentAnalyzer

# Authentication Views

class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """User login endpoint"""
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Generate token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        # Update last active
        user.last_active = timezone.now()
        user.save(update_fields=['last_active'])
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class UserProfileViewSet(viewsets.ModelViewSet):
    """User profile management"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        """Follow/unfollow a user"""
        target_user = self.get_object()
        
        if target_user == request.user:
            return Response({'error': 'Cannot follow yourself'}, status=400)
        
        following, created = UserFollowing.objects.get_or_create(
            follower=request.user,
            following=target_user
        )
        
        if not created:
            following.delete()
            return Response({'status': 'unfollowed'})
        
        return Response({'status': 'followed'})


# Celebrity Views

class CelebrityViewSet(viewsets.ReadOnlyModelViewSet):
    """Celebrity profiles"""
    serializer_class = CelebrityProfileSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = CelebrityProfile.objects.filter(
            user__is_active=True,
            verification_status='approved'
        )
        
        # Filters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Sorting
        sort = self.request.query_params.get('sort', '-user__points')
        queryset = queryset.order_by(sort)
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        """Subscribe to celebrity"""
        celebrity_profile = self.get_object()
        
        # Check existing subscription
        existing = Subscription.objects.filter(
            subscriber=request.user,
            celebrity=celebrity_profile,
            status='active'
        ).first()
        
        if existing:
            return Response({'error': 'Already subscribed'}, status=400)
        
        # Create subscription
        subscription = Subscription.objects.create(
            subscriber=request.user,
            celebrity=celebrity_profile,
            end_date=timezone.now() + timedelta(days=30),
            amount_paid=celebrity_profile.subscription_fee,
            payment_method='api'
        )
        
        return Response(SubscriptionSerializer(subscription).data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    """Subscription management"""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(subscriber=self.request.user)


# Fan Views

class FanViewSet(viewsets.ReadOnlyModelViewSet):
    """Fan profiles"""
    queryset = FanProfile.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecommendationView(APIView):
    """Get personalized recommendations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Initialize recommendation engine
        engine = RecommendationEngine()
        
        # Get user interactions
        from apps.accounts.models import UserFollowing
        interactions = []
        
        for follow in UserFollowing.objects.filter(follower=user):
            interactions.append((user.id, follow.following.id, 1.0))
        
        if interactions:
            engine.build_user_item_matrix(interactions)
            recommendations = engine.get_user_recommendations(
                user.id, 
                n_recommendations=10,
                method='hybrid'
            )
            
            # Get recommended users
            recommended_ids = [rec[0] for rec in recommendations]
            recommended_users = User.objects.filter(id__in=recommended_ids)
            
            return Response(UserSerializer(recommended_users, many=True).data)
        
        # Return trending if no interactions
        trending = User.objects.filter(
            user_type='celebrity',
            is_verified=True
        ).order_by('-points')[:10]
        
        return Response(UserSerializer(trending, many=True).data)


# Post Views

class PostViewSet(viewsets.ModelViewSet):
    """Post management"""
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Post.objects.filter(is_active=True)
        
        # Filter by author
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author__username=author)
        
        # Filter by type
        post_type = self.request.query_params.get('type')
        if post_type:
            queryset = queryset.filter(post_type=post_type)
        
        return queryset
    
    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        
        # Check for harassment
        analyzer = SentimentAnalyzer()
        harassment_check = analyzer.detect_harassment(post.content)
        
        if harassment_check['is_harassment'] and harassment_check['severity'] == 'high':
            post.is_active = False
            post.is_reported = True
            post.save()
            
            # Create automatic report
            from apps.reports.models import Report
            Report.objects.create(
                reported_by=User.objects.get(username='system'),
                report_type='post',
                reason='harassment',
                description='Automatically detected harassment',
                target_object_id=str(post.id)
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """Like/unlike a post"""
        post = self.get_object()
        
        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if not created:
            like.delete()
            post.likes_count -= 1
            post.save()
            return Response({'status': 'unliked'})
        
        post.likes_count += 1
        post.save()
        return Response({'status': 'liked'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def comment(self, request, pk=None):
        """Add comment to post"""
        post = self.get_object()
        
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment = serializer.save(
            post=post,
            author=request.user
        )
        
        post.comments_count += 1
        post.save()
        
        return Response(CommentSerializer(comment).data)


class FeedView(APIView):
    """Get personalized feed"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get followed users
        following_ids = UserFollowing.objects.filter(
            follower=user
        ).values_list('following_id', flat=True)
        
        # Get posts from followed users
        posts = Post.objects.filter(
            Q(author_id__in=following_ids) | Q(author=user),
            is_active=True
        ).order_by('-created_at')[:50]
        
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)


# FanClub Views

class FanClubViewSet(viewsets.ModelViewSet):
    """FanClub management"""
    serializer_class = FanClubSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return FanClub.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def join(self, request, pk=None):
        """Join fanclub"""
        fanclub = self.get_object()
        
        membership, created = FanClubMembership.objects.get_or_create(
            user=request.user,
            fanclub=fanclub,
            defaults={'status': 'active'}
        )
        
        if not created:
            return Response({'error': 'Already a member'}, status=400)
        
        return Response(FanClubMembershipSerializer(membership).data)


# Event Views

class EventViewSet(viewsets.ModelViewSet):
    """Event management"""
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Event.objects.filter(
            status__in=['upcoming', 'ongoing']
        )
        
        # Filter by celebrity
        celebrity = self.request.query_params.get('celebrity')
        if celebrity:
            queryset = queryset.filter(celebrity__username=celebrity)
        
        # Filter by city
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        return queryset


class EventBookingViewSet(viewsets.ModelViewSet):
    """Event booking management"""
    serializer_class = EventBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EventBooking.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        booking = serializer.save(user=self.request.user)
        booking.confirm_booking()  # Auto-confirm for API


# Merchandise Views

class MerchandiseViewSet(viewsets.ModelViewSet):
    """Merchandise management"""
    serializer_class = MerchandiseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Merchandise.objects.filter(status='available')


class OrderViewSet(viewsets.ModelViewSet):
    """Order management"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return MerchandiseOrder.objects.filter(user=self.request.user)


# Messaging Views

class ConversationViewSet(viewsets.ModelViewSet):
    """Conversation management"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        )


class MessageViewSet(viewsets.ModelViewSet):
    """Message management"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        conversation_id = self.request.query_params.get('conversation')
        if conversation_id:
            return Message.objects.filter(
                conversation_id=conversation_id,
                conversation__participants=self.request.user
            )
        return Message.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


# Notification Views

class NotificationViewSet(viewsets.ModelViewSet):
    """Notification management"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({'status': 'success'})


# Analytics Views

class AnalyticsView(APIView):
    """Analytics endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        from apps.analytics.models import UserEngagementMetrics
        
        # Get or create metrics
        metrics, created = UserEngagementMetrics.objects.get_or_create(
            user=user
        )
        
        # Update metrics
        metrics.total_posts = user.posts.count()
        metrics.followers_count = user.followers.count()
        metrics.following_count = user.following.count()
        metrics.calculate_engagement_score()
        metrics.save()
        
        return Response({
            'engagement_score': metrics.engagement_score,
            'influence_score': metrics.influence_score,
            'total_posts': metrics.total_posts,
            'followers': metrics.followers_count,
            'following': metrics.following_count
        })


# Search Views

class SearchView(APIView):
    """Global search endpoint"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        search_type = request.query_params.get('type', 'all')
        
        results = {}
        
        if search_type in ['all', 'users']:
            users = User.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )[:10]
            results['users'] = UserSerializer(users, many=True).data
        
        if search_type in ['all', 'posts']:
            posts = Post.objects.filter(
                Q(content__icontains=query) |
                Q(tags__icontains=query),
                is_active=True
            )[:10]
            results['posts'] = PostSerializer(posts, many=True).data
        
        if search_type in ['all', 'events']:
            events = Event.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )[:10]
            results['events'] = EventSerializer(events, many=True).data
        
        return Response(results)