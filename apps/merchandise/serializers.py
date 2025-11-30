# apps/merchandise/serializers.py

from rest_framework import serializers
from .models import Merchandise, MerchandiseOrder, OrderItem

class MerchandiseSerializer(serializers.ModelSerializer):
    celebrity_username = serializers.CharField(source='celebrity.username', read_only=True)
    final_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Merchandise
        fields = '__all__'
        read_only_fields = ['slug', 'total_sold', 'views_count']
    
    def get_final_price(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_final_price(request.user)
        return obj.get_final_price()


class OrderItemSerializer(serializers.ModelSerializer):
    merchandise_name = serializers.CharField(source='merchandise.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = MerchandiseOrder
        fields = '__all__'
        read_only_fields = ['order_number', 'order_status']