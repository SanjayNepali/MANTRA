# apps/events/serializers.py

from rest_framework import serializers
from .models import Event, EventBooking

class EventSerializer(serializers.ModelSerializer):
    celebrity_username = serializers.CharField(source='celebrity.username', read_only=True)
    current_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['slug', 'status']
    
    def get_current_price(self, obj):
        return obj.get_current_price()


class EventBookingSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    
    class Meta:
        model = EventBooking
        fields = '__all__'
        read_only_fields = ['booking_code', 'booking_status']