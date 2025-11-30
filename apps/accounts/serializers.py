# apps/accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserFollowing, PointsHistory, UserPreferences, SubAdminProfile

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'user_type', 'first_name', 'last_name',
            'bio', 'profile_picture', 'cover_image', 'points', 'rank',
            'is_verified', 'is_active', 'country', 'city',
            'followers_count', 'following_count', 'is_following',
            'created_at', 'last_active'
        )
        read_only_fields = ('id', 'points', 'rank', 'is_verified', 'created_at')
    
    def get_followers_count(self, obj):
        return obj.followers.count()
    
    def get_following_count(self, obj):
        return obj.following.count()
    
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFollowing.objects.filter(
                follower=request.user,
                following=obj
            ).exists()
        return False


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm',
            'user_type', 'first_name', 'last_name', 'phone',
            'country', 'city', 'bio'
        )
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError("Email already exists")
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Award initial points
        if user.user_type == 'celebrity':
            user.add_points(50, "Celebrity welcome bonus")
        else:
            user.add_points(10, "Welcome bonus")
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    user_type = serializers.ChoiceField(choices=User.USER_TYPES)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        user_type = attrs.get('user_type')
        
        # Check if username is email
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                username = user.username
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid credentials")
        
        # Authenticate
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        
        if user.user_type != user_type:
            raise serializers.ValidationError(f"This is not a {user_type} account")
        
        if user.check_ban_status():
            raise serializers.ValidationError(f"Account banned: {user.ban_reason}")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive")
        
        attrs['user'] = user
        return attrs


class UserFollowingSerializer(serializers.ModelSerializer):
    """Serializer for following relationships"""
    
    follower_details = UserSerializer(source='follower', read_only=True)
    following_details = UserSerializer(source='following', read_only=True)
    
    class Meta:
        model = UserFollowing
        fields = ('id', 'follower', 'following', 'follower_details', 
                 'following_details', 'created_at')
        read_only_fields = ('created_at',)


class PointsHistorySerializer(serializers.ModelSerializer):
    """Serializer for points history"""
    
    class Meta:
        model = PointsHistory
        fields = ('id', 'points', 'reason', 'balance_after', 'created_at')
        read_only_fields = '__all__'


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user preferences"""
    
    class Meta:
        model = UserPreferences
        exclude = ('user', 'id')


class SubAdminProfileSerializer(serializers.ModelSerializer):
    """Serializer for sub-admin profiles"""
    
    user_details = UserSerializer(source='user', read_only=True)
    assigned_by_details = UserSerializer(source='assigned_by', read_only=True)
    
    class Meta:
        model = SubAdminProfile
        fields = '__all__'