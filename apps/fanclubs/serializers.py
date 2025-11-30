# apps/fanclubs/serializers.py

from rest_framework import serializers
from .models import FanClub, FanClubMembership

class FanClubSerializer(serializers.ModelSerializer):
    celebrity_username = serializers.CharField(source='celebrity.username', read_only=True)
    is_member = serializers.SerializerMethodField()
    
    class Meta:
        model = FanClub
        fields = ['id', 'celebrity', 'celebrity_username', 'name', 'slug',
                 'description', 'club_type', 'members_count', 'is_member',
                 'cover_image', 'icon', 'created_at']
        read_only_fields = ['slug', 'members_count']
    
    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FanClubMembership.objects.filter(
                user=request.user, fanclub=obj, status='active'
            ).exists()
        return False


class FanClubMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = FanClubMembership
        fields = '__all__'