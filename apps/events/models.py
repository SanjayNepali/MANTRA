# apps/events/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Event(models.Model):
    """Events created by celebrities"""

    EVENT_TYPES = (
        ('concert', 'Concert'),
        ('meet_greet', 'Meet & Greet'),
        ('fanmeeting', 'Fan Meeting'),
        ('livestream', 'Live Stream'),
        ('premiere', 'Premiere'),
        ('workshop', 'Workshop'),
        ('charity', 'Charity Event'),
        ('virtual', 'Virtual Event'),
        ('other', 'Other'),
    )

    EVENT_STATUS = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    celebrity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events',
        limit_choices_to={'user_type': 'celebrity'}
    )

    # Basic Info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    status = models.CharField(max_length=20, choices=EVENT_STATUS, default='draft')

    # Media
    poster = models.ImageField(upload_to='events/posters/', null=True, blank=True)
    banner = models.ImageField(upload_to='events/banners/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='events/covers/')  # Keeping for compatibility
    gallery = models.JSONField(default=list, blank=True)
    gallery_images = models.JSONField(default=list, blank=True)  # Keeping for compatibility

    # Location
    is_virtual = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)  # Keeping for compatibility
    venue_name = models.CharField(max_length=200, blank=True)
    venue = models.CharField(max_length=200, blank=True)  # Keeping for compatibility
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    map_link = models.URLField(blank=True)
    streaming_link = models.URLField(blank=True)
    online_link = models.URLField(blank=True)  # Keeping for compatibility

    # Timing
    start_datetime = models.DateTimeField(null=True, blank=True)  # Will sync from event_date
    event_date = models.DateTimeField()  # Keeping for compatibility
    end_datetime = models.DateTimeField(null=True, blank=True)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, default=2)
    doors_open = models.DateTimeField(null=True, blank=True)

    # Tickets & Capacity
    total_capacity = models.IntegerField(default=0)
    total_tickets = models.IntegerField(default=0)  # Keeping for compatibility
    available_tickets = models.IntegerField(default=0)
    tickets_sold = models.IntegerField(default=0)

    # Pricing
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    early_bird_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    early_bird_deadline = models.DateTimeField(null=True, blank=True)

    # Pricing Tiers
    has_multiple_tiers = models.BooleanField(default=False)

    # Age Restrictions
    min_age = models.IntegerField(default=0)
    is_adult_only = models.BooleanField(default=False)

    # Special Requirements
    special_requirements = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)

    # Fan Club Priority
    fan_club_exclusive = models.BooleanField(default=False)
    fan_club_presale = models.BooleanField(default=False)
    presale_start = models.DateTimeField(null=True, blank=True)

    # Engagement
    interested_count = models.IntegerField(default=0)
    going_count = models.IntegerField(default=0)

    # Revenue
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status
    is_featured = models.BooleanField(default=False)

    # SEO
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime', '-created_at']
        indexes = [
            models.Index(fields=['celebrity', 'status']),
            models.Index(fields=['start_datetime', 'status']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.title} by {self.celebrity.username}"

    def clean(self):
        """Validate event data"""
        from django.core.exceptions import ValidationError
        errors = {}

        # Validate event timing
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                errors['end_datetime'] = 'End time must be after start time'

        # Validate early bird deadline
        if self.early_bird_deadline and self.start_datetime:
            if self.early_bird_deadline >= self.start_datetime:
                errors['early_bird_deadline'] = 'Early bird deadline must be before event start'

        # Validate tickets
        if self.available_tickets > self.total_capacity:
            errors['available_tickets'] = 'Available tickets cannot exceed total capacity'

        # Validate virtual events have streaming link
        if self.is_virtual and self.status == 'published':
            if not self.streaming_link and not self.online_link:
                errors['streaming_link'] = 'Virtual events must have a streaming link'

        # Validate physical events have venue
        if not self.is_virtual and self.status == 'published':
            if not self.venue_name and not self.venue:
                errors['venue_name'] = 'Physical events must have a venue'

        # Validate pricing
        if self.early_bird_price and self.ticket_price:
            if self.early_bird_price >= self.ticket_price:
                errors['early_bird_price'] = 'Early bird price must be less than regular price'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.celebrity.username}")
        # Sync compatibility fields
        if not self.start_datetime and self.event_date:
            self.start_datetime = self.event_date
        if not self.event_date and self.start_datetime:
            self.event_date = self.start_datetime
        if not self.venue:
            self.venue = self.venue_name
        if not self.total_tickets:
            self.total_tickets = self.total_capacity
        if self.is_virtual and not self.is_online:
            self.is_online = True
        if not self.online_link:
            self.online_link = self.streaming_link
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.start_datetime > timezone.now()


    @property
    def is_past(self):
        if self.end_datetime:
            return self.end_datetime < timezone.now()
        return self.start_datetime < timezone.now()

    @property
    def is_sold_out(self):
        return self.available_tickets == 0 and self.total_capacity > 0

    def get_current_price(self):
        """Get current ticket price"""
        if self.early_bird_deadline and timezone.now() < self.early_bird_deadline:
            return self.early_bird_price or self.ticket_price
        return self.ticket_price

    def get_absolute_url(self):
        """Get absolute URL for this event"""
        from django.urls import reverse
        return reverse('event_detail', kwargs={'slug': self.slug})


class EventTicketTier(models.Model):
    """Different ticket tiers for events"""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_tiers')

    name = models.CharField(max_length=100)
    description = models.TextField()

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')

    # Capacity
    total_quantity = models.IntegerField()
    available_quantity = models.IntegerField()
    max_per_person = models.IntegerField(default=4)

    # Perks
    perks = models.JSONField(default=list, blank=True)
    includes_merchandise = models.BooleanField(default=False)
    includes_meet_greet = models.BooleanField(default=False)

    # Sales Period
    sale_start = models.DateTimeField()
    sale_end = models.DateTimeField()

    # Display
    display_order = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['display_order', 'price']

    def __str__(self):
        return f"{self.event.title} - {self.name}"


class EventBooking(models.Model):
    """Event registrations/bookings"""

    REGISTRATION_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
        ('refunded', 'Refunded'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_registrations',
        null=True,
        blank=True
    )
    user = models.ForeignKey(  # Keeping for compatibility
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_bookings'
    )

    # Ticket Info
    ticket_tier = models.ForeignKey(
        EventTicketTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    ticket_quantity = models.IntegerField(default=1)  # Keeping for compatibility

    # Status
    status = models.CharField(max_length=20, choices=REGISTRATION_STATUS, default='pending')
    booking_status = models.CharField(max_length=20, default='pending')  # Keeping for compatibility

    # Booking Details
    booking_reference = models.CharField(max_length=20, unique=True, null=True, blank=True)
    booking_code = models.CharField(max_length=20, unique=True)  # Keeping for compatibility
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment
    payment_status = models.CharField(max_length=20, default='pending')
    payment_method = models.CharField(max_length=20, blank=True)
    payment_id = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)  # Keeping for compatibility
    paid_at = models.DateTimeField(null=True, blank=True)

    # Additional Info
    special_requests = models.TextField(blank=True)
    dietary_requirements = models.CharField(max_length=200, blank=True)

    # Check-in
    checked_in = models.BooleanField(default=False)
    is_checked_in = models.BooleanField(default=False)  # Keeping for compatibility
    checked_in_at = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event', 'attendee']),
            models.Index(fields=['event', 'user']),
            models.Index(fields=['booking_reference']),
            models.Index(fields=['booking_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        username = self.attendee.username if self.attendee else (self.user.username if self.user else "Unknown")
        return f"{username} - {self.event.title}"

    def generate_booking_code(self):
        """Generate unique booking code"""
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        while EventBooking.objects.filter(booking_code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return code

    def save(self, *args, **kwargs):
        if not self.booking_code:
            self.booking_code = self.generate_booking_code()
        if not self.booking_reference:
            self.booking_reference = self.booking_code
        # Sync compatibility fields
        if not self.attendee and self.user:
            self.attendee = self.user
        if not self.user and self.attendee:
            self.user = self.attendee
        if not self.ticket_quantity:
            self.ticket_quantity = self.quantity
        if not self.is_checked_in:
            self.is_checked_in = self.checked_in
        if not self.booking_status:
            self.booking_status = self.status
        super().save(*args, **kwargs)


class EventInterest(models.Model):
    """Track user interest in events"""

    INTEREST_TYPES = (
        ('interested', 'Interested'),
        ('going', 'Going'),
        ('maybe', 'Maybe'),
    )

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='interests')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_interests'
    )

    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPES)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event', 'interest_type']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.interest_type} - {self.event.title}"


class EventReview(models.Model):
    """Reviews for completed events"""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_reviews'
    )

    # Ratings
    overall_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    venue_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    organization_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )

    # Review
    title = models.CharField(max_length=200)
    review_text = models.TextField()

    # Media
    photos = models.JSONField(default=list, blank=True)

    # Verification
    verified_attendee = models.BooleanField(default=False)

    # Engagement
    helpful_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('event', 'reviewer')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event', '-created_at']),
            models.Index(fields=['verified_attendee', '-helpful_count']),
        ]

    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.event.title}"


class EventUpdate(models.Model):
    """Updates/announcements for events"""

    UPDATE_TYPES = (
        ('general', 'General Update'),
        ('schedule', 'Schedule Change'),
        ('venue', 'Venue Change'),
        ('tickets', 'Ticket Update'),
        ('cancellation', 'Cancellation'),
        ('postponement', 'Postponement'),
    )

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='updates')

    update_type = models.CharField(max_length=20, choices=UPDATE_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()

    # Importance
    is_urgent = models.BooleanField(default=False)
    send_notification = models.BooleanField(default=True)

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event', '-created_at']),
            models.Index(fields=['is_urgent', '-created_at']),
        ]

    def __str__(self):
        return f"{self.event.title} - {self.title}"