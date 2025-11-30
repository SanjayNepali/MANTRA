# apps/notifications/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.notifications_list, name='notifications_list'),
    path('preferences/', views.notification_preferences, name='notification_preferences'),
    path('mark-read/<uuid:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('delete/<uuid:notification_id>/', views.delete_notification, name='delete_notification'),
    path('unread-count/', views.get_unread_count, name='get_unread_count'),
    path('recent/', views.get_recent_notifications, name='get_recent_notifications'),
    path('announcements/', views.system_announcements, name='system_announcements'),
]