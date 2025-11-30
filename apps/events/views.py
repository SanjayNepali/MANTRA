# apps/events/views.py - FIXED WITH ALGORITHM INTEGRATION

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, F, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from decimal import Decimal
from apps.events.models import Event, EventBooking, EventInterest
from apps.events.forms import EventCreateForm, EventBookingForm, EventEditForm, EventCancelForm
from apps.accounts.models import UserFollowing

# Import recommendation algorithms
from algorithms.recommendation import TrendingEngine
from algorithms.integration import get_user_recommendations
from algorithms.matching import MatchingEngine


class EventListView(TemplateView):
    """List all events with recommendation algorithms"""
    template_name = 'events/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        base_qs = Event.objects.filter(status='published').select_related('celebrity')

        # 🔥 ALGORITHM INTEGRATION: Get trending events
        trending_engine = TrendingEngine()
        context['trending_events'] = trending_engine.calculate_trending_events(days=14, limit=10)

        # 🏆 Top Events (by bookings)
        context['top_events'] = base_qs.annotate(
            bookings_count=Count('registrations')
        ).order_by('-bookings_count')[:10]

        # ⏳ Upcoming (next 30 days)
        context['upcoming_events'] = base_qs.filter(
            start_datetime__gte=now,
            start_datetime__lte=now + timedelta(days=30)
        ).order_by('start_datetime')[:10]

        # ⭐ ALGORITHM INTEGRATION: Recommended Events with caching
        if self.request.user.is_authenticated and self.request.user.user_type == 'fan':
            try:
                recommendations = get_user_recommendations(
                    self.request.user,
                    recommendation_type='events',
                    limit=10,
                    use_cache=True
                )
                context['recommended_events'] = recommendations.get('events', [])
                if not context['recommended_events']:
                    context['recommended_events'] = context['top_events']
            except Exception as e:
                print(f"Error getting event recommendations: {e}")
                context['recommended_events'] = context['top_events']
        else:
            context['recommended_events'] = context['top_events']

        # 🎯 Main query with filters
        queryset = base_qs
        
        # Search
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(city__icontains=search) |
                Q(celebrity__username__icontains=search)
            )
        context['search_query'] = search

        # Filter by type
        event_type = self.request.GET.get('type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        context['current_type'] = event_type

        # Filter by city
        city = self.request.GET.get('city')
        if city:
            queryset = queryset.filter(city=city)
        context['current_city'] = city

        # Sorting options
        sort = self.request.GET.get('sort', 'date')
        if sort == 'popular':
            queryset = queryset.annotate(bookings_count=Count('registrations')).order_by('-bookings_count')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'price_low':
            queryset = queryset.order_by('ticket_price')
        elif sort == 'price_high':
            queryset = queryset.order_by('-ticket_price')
        else:
            queryset = queryset.order_by('start_datetime')
        context['current_sort'] = sort

        # Get unique cities and event types for filter dropdowns
        context['cities'] = Event.objects.filter(status='published').values_list('city', flat=True).distinct().order_by('city')
        context['event_types'] = Event.EVENT_TYPES

        # Pagination
        paginator = Paginator(queryset, 12)
        page_number = self.request.GET.get('page')
        context['events'] = paginator.get_page(page_number)

        return context


class EventDetailView(DetailView):
    """View event details"""
    model = Event
    template_name = 'events/detail.html'
    context_object_name = 'event'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        
        # Check if user has booked
        if self.request.user.is_authenticated:
            context['has_booked'] = EventBooking.objects.filter(
                event=event,
                user=self.request.user,
                status__in=['confirmed', 'pending']
            ).exists()
            
            # Check if user has shown interest
            context['user_interest'] = EventInterest.objects.filter(
                event=event,
                user=self.request.user
            ).first()
            
            # Hide "Going" button if already booked
            context['show_going_button'] = not context['has_booked']
        
        # Get current price
        context['current_price'] = event.get_current_price()
        context['tickets_available'] = event.available_tickets > 0
        
        # 🔥 ALGORITHM INTEGRATION: Similar/Related Events
        if self.request.user.is_authenticated and self.request.user.user_type == 'fan':
            matching_engine = MatchingEngine()
            
            similar_events = Event.objects.filter(
                status='published',
                start_datetime__gte=timezone.now()
            ).exclude(id=event.id)[:20]
            
            matched_events = matching_engine.match_content_to_user(
                self.request.user,
                similar_events,
                content_type='event',
                limit=4
            )
            context['similar_events'] = [item for item, score in matched_events]
        else:
            context['similar_events'] = Event.objects.filter(
                celebrity=event.celebrity,
                status='published',
                start_datetime__gte=timezone.now()
            ).exclude(id=event.id)[:4]
        
        # Get event statistics
        context['total_interested'] = event.interested_count
        context['total_going'] = event.going_count
        context['total_booked'] = event.tickets_sold
        
        return context


@login_required
def create_event(request):
    """Create new event (celebrities only)"""
    if request.user.user_type != 'celebrity':
        messages.error(request, 'Only celebrities can create events')
        return redirect('event_list')
    
    if request.method == 'POST':
        form = EventCreateForm(request.POST, request.FILES)
        
        if form.is_valid():
            event = form.save(commit=False)
            event.celebrity = request.user
            event.available_tickets = event.total_capacity or event.total_tickets
            event.save()
            
            messages.success(request, 'Event created successfully!')
            return redirect('event_detail', slug=event.slug)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventCreateForm()
    
    return render(request, 'events/create.html', {'form': form})


@login_required
def book_event(request, slug):
    """Book event tickets with points discount support"""
    event = get_object_or_404(Event, slug=slug)
    
    if event.status != 'published':
        messages.error(request, 'This event is not available for booking')
        return redirect('event_detail', slug=slug)
    
    # Check if already booked
    existing_booking = EventBooking.objects.filter(
        event=event,
        user=request.user,
        status__in=['confirmed', 'pending']
    ).first()
    
    if existing_booking:
        messages.info(request, 'You already have a booking for this event')
        return redirect('event_booking_detail', booking_id=existing_booking.id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('ticket_quantity', 1))
        payment_method = request.POST.get('payment_method', 'esewa')
        points_to_use = int(request.POST.get('points_to_use', 0))
        
        # Validate quantity
        if quantity > event.available_tickets:
            messages.error(request, 'Not enough tickets available')
            return redirect('event_detail', slug=slug)
        
        # Calculate price
        price = event.get_current_price()
        subtotal = Decimal(str(price)) * quantity
        
        # Apply points discount (max 50% of total)
        max_discount = subtotal * Decimal('0.5')
        discount = Decimal(str(min(points_to_use, float(max_discount))))
        
        # Ensure user has enough points
        if discount > request.user.points:
            discount = Decimal(str(request.user.points))
        
        total = subtotal - discount
        
        # Create booking
        booking = EventBooking.objects.create(
            event=event,
            user=request.user,
            attendee=request.user,
            quantity=quantity,
            ticket_quantity=quantity,
            total_amount=total,
            payment_method=payment_method,
            status='pending',
            booking_status='pending'
        )
        
        # Update event tickets
        event.available_tickets = F('available_tickets') - quantity
        event.tickets_sold = F('tickets_sold') + quantity
        event.save()
        event.refresh_from_db()
        
        # Deduct points if used
        if discount > 0:
            request.user.deduct_points(
                int(discount), 
                f"Discount for event booking: {event.title}"
            )
        
        messages.success(request, f'Successfully reserved {quantity} ticket(s)! Please complete payment.')
        return redirect('event_booking_detail', booking_id=booking.id)
    
    # GET request - show booking form
    current_price = event.get_current_price()
    
    context = {
        'event': event,
        'current_price': current_price,
    }
    
    return render(request, 'events/book.html', context)


@login_required
def event_booking_detail(request, booking_id):
    """View booking details with payment processing"""
    booking = get_object_or_404(
        EventBooking,
        id=booking_id,
        user=request.user
    )
    
    # Handle payment confirmation
    if request.method == 'POST' and booking.status == 'pending':
        booking.status = 'confirmed'
        booking.booking_status = 'confirmed'
        booking.payment_status = 'completed'
        booking.paid_at = timezone.now()
        booking.save()
        
        # Award points for booking
        booking.user.add_points(20, f"Booked event: {booking.event.title}")
        
        # Automatically mark user as "Going"
        EventInterest.objects.update_or_create(
            event=booking.event,
            user=booking.user,
            defaults={'interest_type': 'going'}
        )
        
        # Update going count
        booking.event.going_count = F('going_count') + 1
        booking.event.save()
        
        messages.success(request, 'Payment confirmed! Your booking is complete. You are marked as "Going" to this event.')
        return redirect('event_booking_detail', booking_id=booking.id)
    
    return render(request, 'events/booking_detail.html', {'booking': booking})


@login_required
def my_bookings(request):
    """View user's event bookings"""
    bookings = EventBooking.objects.filter(
        user=request.user
    ).select_related('event', 'event__celebrity').order_by('-created_at')
    
    # Separate by status
    upcoming_bookings = bookings.filter(
        event__start_datetime__gte=timezone.now(),
        status__in=['confirmed', 'pending']
    )
    
    past_bookings = bookings.filter(
        Q(event__start_datetime__lt=timezone.now()) |
        Q(status__in=['cancelled', 'refunded'])
    )
    
    context = {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'all_bookings': bookings
    }
    
    return render(request, 'events/my_bookings.html', context)


@login_required
def edit_event(request, slug):
    """Edit event"""
    event = get_object_or_404(Event, slug=slug, celebrity=request.user)
    
    if event.status == 'cancelled':
        messages.error(request, 'Cannot edit cancelled events')
        return redirect('event_detail', slug=event.slug)
    
    if request.method == 'POST':
        form = EventEditForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event_detail', slug=event.slug)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventEditForm(instance=event)
    
    return render(request, 'events/edit.html', {'form': form, 'event': event})


@login_required
def cancel_event(request, slug):
    """Cancel event"""
    event = get_object_or_404(Event, slug=slug, celebrity=request.user)
    
    if event.status == 'cancelled':
        messages.info(request, 'Event is already cancelled')
        return redirect('event_detail', slug=slug)
    
    if request.method == 'POST':
        form = EventCancelForm(request.POST)
        if form.is_valid():
            event.status = 'cancelled'
            event.save()
            
            # Notify all attendees (implement notification system)
            if form.cleaned_data['notify_attendees']:
                # TODO: Send notifications to all booked users
                pass
            
            messages.success(request, 'Event cancelled successfully')
            return redirect('event_detail', slug=slug)
    else:
        form = EventCancelForm()
    
    return render(request, 'events/cancel.html', {'form': form, 'event': event})


@login_required
def toggle_event_interest(request, slug):
    """Toggle user interest in event (interested/going)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    event = get_object_or_404(Event, slug=slug)
    interest_type = request.POST.get('type', 'interested')
    
    # Check if user has already booked - prevent changing to "interested" if booked
    has_booked = EventBooking.objects.filter(
        event=event,
        user=request.user,
        status__in=['confirmed', 'pending']
    ).exists()
    
    if has_booked and interest_type != 'going':
        return JsonResponse({
            'error': 'You have already booked this event',
            'status': 'booked'
        }, status=400)
    
    interest, created = EventInterest.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={'interest_type': interest_type}
    )
    
    if not created:
        if interest.interest_type == interest_type:
            # Remove interest
            old_type = interest.interest_type
            interest.delete()
            
            # Update counts
            if old_type == 'interested':
                event.interested_count = F('interested_count') - 1
            elif old_type == 'going':
                event.going_count = F('going_count') - 1
            event.save()
            event.refresh_from_db()
            
            return JsonResponse({
                'status': 'removed',
                'interested_count': event.interested_count,
                'going_count': event.going_count
            })
        else:
            # Update existing interest
            old_type = interest.interest_type
            interest.interest_type = interest_type
            interest.save()
            
            # Update counts
            if old_type == 'interested':
                event.interested_count = F('interested_count') - 1
            elif old_type == 'going':
                event.going_count = F('going_count') - 1
            
            if interest_type == 'interested':
                event.interested_count = F('interested_count') + 1
            elif interest_type == 'going':
                event.going_count = F('going_count') + 1
            
            event.save()
            event.refresh_from_db()
    else:
        # New interest
        if interest_type == 'interested':
            event.interested_count = F('interested_count') + 1
        elif interest_type == 'going':
            event.going_count = F('going_count') + 1
        event.save()
        event.refresh_from_db()
    
    return JsonResponse({
        'status': 'added',
        'type': interest_type,
        'interested_count': event.interested_count,
        'going_count': event.going_count
    })



@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(EventBooking, id=booking_id, user=request.user)
    
    if booking.status == 'cancelled':
        messages.info(request, 'Booking is already cancelled')
        return redirect('event_booking_detail', booking_id=booking.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'User cancelled')
        
        booking.status = 'cancelled'
        booking.booking_status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = reason
        booking.save()
        
        # Return tickets to event
        booking.event.available_tickets = F('available_tickets') + booking.quantity
        booking.event.tickets_sold = F('tickets_sold') - booking.quantity
        booking.event.save()
        
        messages.success(request, 'Booking cancelled successfully')
        return redirect('my_bookings')
    
    return render(request, 'events/cancel_booking.html', {'booking': booking})