# api/filters.py

from django_filters import rest_framework as filters
from apps.posts.models import Post
from apps.events.models import Event

class PostFilter(filters.FilterSet):
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    author = filters.CharFilter(field_name='author__username')
    
    class Meta:
        model = Post
        fields = ['post_type', 'is_exclusive', 'created_after', 'created_before', 'author']


class EventFilter(filters.FilterSet):
    date_from = filters.DateTimeFilter(field_name='event_date', lookup_expr='gte')
    date_to = filters.DateTimeFilter(field_name='event_date', lookup_expr='lte')
    price_min = filters.NumberFilter(field_name='ticket_price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='ticket_price', lookup_expr='lte')
    
    class Meta:
        model = Event
        fields = ['event_type', 'city', 'is_online', 'date_from', 'date_to', 'price_min', 'price_max']