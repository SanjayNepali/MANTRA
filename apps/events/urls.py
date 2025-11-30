# apps/events/urls.py - UPDATED WITH ALL ROUTES
from django.urls import path
from . import views

urlpatterns = [
    # List and detail views
    path('', views.EventListView.as_view(), name='event_list'),
    path('create/', views.create_event, name='create_event'),
    path('<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<slug:slug>/edit/', views.edit_event, name='edit_event'),
    path('<slug:slug>/cancel/', views.cancel_event, name='cancel_event'),
    
    # Booking related
    path('<slug:slug>/book/', views.book_event, name='book_event'),
    path('booking/<uuid:booking_id>/', views.event_booking_detail, name='event_booking_detail'),
    path('booking/<uuid:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    
    # Interest toggle
    path('<slug:slug>/interest/', views.toggle_event_interest, name='toggle_event_interest'),
]