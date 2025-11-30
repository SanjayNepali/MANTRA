# apps/merchandise/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import (
    MerchandiseCategory, Merchandise, MerchandiseOrder, OrderItem
)

@admin.register(MerchandiseCategory)
class MerchandiseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Merchandise)
class MerchandiseAdmin(admin.ModelAdmin):
    list_display = ['name', 'celebrity', 'category', 'price', 'stock_quantity',
                   'status', 'total_sold', 'is_featured', 'is_exclusive', 'created_at']
    list_filter = ['status', 'is_featured', 'is_exclusive', 'category', 'created_at']
    search_fields = ['name', 'celebrity__username', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['total_sold', 'views_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('celebrity', 'category', 'name', 'slug', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_percentage', 'subscriber_discount')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'status')
        }),
        ('Media', {
            'fields': ('primary_image', 'gallery_images')
        }),
        ('Specifications', {
            'fields': ('specifications',),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('is_featured', 'is_exclusive')
        }),
        ('Statistics', {
            'fields': ('total_sold', 'views_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_featured', 'mark_as_available', 'mark_as_out_of_stock']

    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} product(s) marked as featured.')
    mark_as_featured.short_description = 'Mark as Featured'

    def mark_as_available(self, request, queryset):
        updated = queryset.filter(stock_quantity__gt=0).update(status='available')
        self.message_user(request, f'{updated} product(s) marked as available.')
    mark_as_available.short_description = 'Mark as Available'

    def mark_as_out_of_stock(self, request, queryset):
        updated = queryset.update(status='out_of_stock')
        self.message_user(request, f'{updated} product(s) marked as out of stock.')
    mark_as_out_of_stock.short_description = 'Mark as Out of Stock'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']
    fields = ['merchandise', 'quantity', 'price', 'subtotal']


@admin.register(MerchandiseOrder)
class MerchandiseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'total_amount', 'order_status',
                   'payment_status', 'created_at', 'shipped_at', 'delivered_at']
    list_filter = ['order_status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'user__username', 'tracking_number', 'transaction_id']
    readonly_fields = ['order_number', 'created_at', 'shipped_at', 'delivered_at']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Info', {
            'fields': ('user', 'order_number', 'total_amount')
        }),
        ('Shipping Address', {
            'fields': ('shipping_address', 'shipping_city', 'shipping_country',
                      'shipping_postal_code', 'contact_number')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_status', 'transaction_id')
        }),
        ('Status & Tracking', {
            'fields': ('order_status', 'tracking_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']

    def mark_as_processing(self, request, queryset):
        updated = queryset.update(order_status='processing')
        self.message_user(request, f'{updated} order(s) marked as processing.')
    mark_as_processing.short_description = 'Mark as Processing'

    def mark_as_shipped(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(order_status='shipped', shipped_at=now)
        self.message_user(request, f'{updated} order(s) marked as shipped.')
    mark_as_shipped.short_description = 'Mark as Shipped'

    def mark_as_delivered(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(order_status='delivered', delivered_at=now)
        self.message_user(request, f'{updated} order(s) marked as delivered.')
    mark_as_delivered.short_description = 'Mark as Delivered'

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(order_status='cancelled')
        self.message_user(request, f'{updated} order(s) cancelled.')
    mark_as_cancelled.short_description = 'Cancel Orders'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'merchandise', 'quantity', 'price', 'subtotal']
    list_filter = ['order__created_at']
    search_fields = ['order__order_number', 'merchandise__name']
    readonly_fields = ['subtotal']

    fieldsets = (
        ('Order Item Info', {
            'fields': ('order', 'merchandise', 'quantity', 'price', 'subtotal')
        }),
    )