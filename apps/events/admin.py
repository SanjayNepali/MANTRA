# apps/events/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import (
    Event, EventTicketTier, EventBooking, EventInterest,
    EventReview, EventUpdate
)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'celebrity', 'event_type', 'status', 'start_datetime',
                   'tickets_sold', 'available_tickets', 'total_revenue', 'is_featured',
                   'created_at']
    list_filter = ['event_type', 'status', 'is_virtual', 'is_featured', 'fan_club_exclusive',
                  'fan_club_presale', 'is_adult_only', 'created_at']
    search_fields = ['title', 'description', 'celebrity__username', 'venue_name', 'city', 'country']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['tickets_sold', 'interested_count', 'going_count', 'total_revenue',
                      'created_at', 'updated_at']
    date_hierarchy = 'start_datetime'

    fieldsets = (
        ('Basic Info', {
            'fields': ('celebrity', 'title', 'slug', 'description', 'event_type', 'status')
        }),
        ('Media', {
            'fields': ('poster', 'banner', 'cover_image', 'gallery', 'gallery_images')
        }),
        ('Location', {
            'fields': ('is_virtual', 'is_online', 'venue_name', 'venue', 'address',
                      'city', 'country', 'map_link', 'streaming_link', 'online_link')
        }),
        ('Timing', {
            'fields': ('start_datetime', 'event_date', 'end_datetime', 'duration_hours', 'doors_open')
        }),
        ('Capacity & Tickets', {
            'fields': ('total_capacity', 'total_tickets', 'available_tickets', 'tickets_sold')
        }),
        ('Pricing', {
            'fields': ('ticket_price', 'early_bird_price', 'early_bird_deadline', 'has_multiple_tiers')
        }),
        ('Restrictions', {
            'fields': ('min_age', 'is_adult_only', 'special_requirements', 'terms_conditions')
        }),
        ('Fan Club', {
            'fields': ('fan_club_exclusive', 'fan_club_presale', 'presale_start'),
            'classes': ('collapse',)
        }),
        ('Engagement', {
            'fields': ('interested_count', 'going_count'),
            'classes': ('collapse',)
        }),
        ('Revenue & Status', {
            'fields': ('total_revenue', 'is_featured')
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_featured', 'mark_as_published', 'mark_as_cancelled']

    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} event(s) marked as featured.')
    mark_as_featured.short_description = 'Mark as Featured'

    def mark_as_published(self, request, queryset):
        updated = queryset.update(status='published')
        self.message_user(request, f'{updated} event(s) published.')
    mark_as_published.short_description = 'Publish Events'

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} event(s) cancelled.')
    mark_as_cancelled.short_description = 'Cancel Events'


@admin.register(EventTicketTier)
class EventTicketTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'event', 'price', 'total_quantity', 'available_quantity',
                   'display_order', 'is_featured', 'created_at']
    list_filter = ['is_featured', 'includes_merchandise', 'includes_meet_greet', 'created_at']
    search_fields = ['name', 'description', 'event__title']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('event', 'name', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'currency')
        }),
        ('Capacity', {
            'fields': ('total_quantity', 'available_quantity', 'max_per_person')
        }),
        ('Perks', {
            'fields': ('perks', 'includes_merchandise', 'includes_meet_greet')
        }),
        ('Sales Period', {
            'fields': ('sale_start', 'sale_end')
        }),
        ('Display', {
            'fields': ('display_order', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EventBooking)
class EventBookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'event', 'attendee', 'quantity', 'total_amount',
                   'status', 'payment_status', 'checked_in', 'created_at']
    list_filter = ['status', 'payment_status', 'checked_in', 'created_at']
    search_fields = ['booking_reference', 'booking_code', 'attendee__username',
                    'event__title', 'payment_id']
    readonly_fields = ['booking_reference', 'booking_code', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Event & Attendee', {
            'fields': ('event', 'attendee', 'user')
        }),
        ('Ticket Info', {
            'fields': ('ticket_tier', 'quantity', 'ticket_quantity')
        }),
        ('Booking Details', {
            'fields': ('booking_reference', 'booking_code', 'total_amount', 'status', 'booking_status')
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_method', 'payment_id', 'transaction_id', 'paid_at')
        }),
        ('Additional Info', {
            'fields': ('special_requests', 'dietary_requirements'),
            'classes': ('collapse',)
        }),
        ('Check-in', {
            'fields': ('checked_in', 'is_checked_in', 'checked_in_at')
        }),
        ('Cancellation', {
            'fields': ('cancelled_at', 'cancellation_reason', 'refund_amount'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_confirmed', 'mark_as_attended', 'check_in_attendees']

    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed', booking_status='confirmed')
        self.message_user(request, f'{updated} booking(s) confirmed.')
    mark_as_confirmed.short_description = 'Confirm Bookings'

    def mark_as_attended(self, request, queryset):
        updated = queryset.update(status='attended')
        self.message_user(request, f'{updated} booking(s) marked as attended.')
    mark_as_attended.short_description = 'Mark as Attended'

    def check_in_attendees(self, request, queryset):
        now = timezone.now()
        queryset.update(checked_in=True, is_checked_in=True, checked_in_at=now)
        self.message_user(request, f'{queryset.count()} attendee(s) checked in.')
    check_in_attendees.short_description = 'Check In Attendees'


@admin.register(EventInterest)
class EventInterestAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'interest_type', 'created_at']
    list_filter = ['interest_type', 'created_at']
    search_fields = ['user__username', 'event__title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('event', 'user', 'interest_type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(EventReview)
class EventReviewAdmin(admin.ModelAdmin):
    list_display = ['event', 'reviewer', 'overall_rating', 'venue_rating',
                   'organization_rating', 'verified_attendee', 'helpful_count', 'created_at']
    list_filter = ['overall_rating', 'verified_attendee', 'created_at']
    search_fields = ['title', 'review_text', 'reviewer__username', 'event__title']
    readonly_fields = ['helpful_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Event & Reviewer', {
            'fields': ('event', 'reviewer', 'verified_attendee')
        }),
        ('Ratings', {
            'fields': ('overall_rating', 'venue_rating', 'organization_rating')
        }),
        ('Review', {
            'fields': ('title', 'review_text', 'photos')
        }),
        ('Engagement', {
            'fields': ('helpful_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_verified']

    def mark_as_verified(self, request, queryset):
        updated = queryset.update(verified_attendee=True)
        self.message_user(request, f'{updated} review(s) marked as verified.')
    mark_as_verified.short_description = 'Mark as Verified Attendee'


@admin.register(EventUpdate)
class EventUpdateAdmin(admin.ModelAdmin):
    list_display = ['event', 'update_type', 'title', 'is_urgent', 'send_notification',
                   'posted_by', 'created_at']
    list_filter = ['update_type', 'is_urgent', 'send_notification', 'created_at']
    search_fields = ['title', 'message', 'event__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Event & Type', {
            'fields': ('event', 'update_type', 'posted_by')
        }),
        ('Content', {
            'fields': ('title', 'message')
        }),
        ('Settings', {
            'fields': ('is_urgent', 'send_notification')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    actions = ['mark_as_urgent', 'enable_notifications']

    def mark_as_urgent(self, request, queryset):
        updated = queryset.update(is_urgent=True)
        self.message_user(request, f'{updated} update(s) marked as urgent.')
    mark_as_urgent.short_description = 'Mark as Urgent'

    def enable_notifications(self, request, queryset):
        updated = queryset.update(send_notification=True)
        self.message_user(request, f'{updated} update(s) will send notifications.')
    enable_notifications.short_description = 'Enable Notifications'