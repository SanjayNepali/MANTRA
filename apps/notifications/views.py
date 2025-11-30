# apps/notifications/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Notification, NotificationPreference, SystemAnnouncement
from .forms import NotificationPreferenceForm

@login_required
def notifications_list(request):
    """List all notifications"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender')
    
    # Filter by type
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # Filter by read status
    status = request.GET.get('status')
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Mark notifications as read when viewed
    unread_notifications = [n for n in page_obj.object_list if not n.is_read]
    for notification in unread_notifications:
        notification.mark_as_read()
    
    context = {
        'notifications': page_obj,
        'notification_types': Notification.NOTIFICATION_TYPES,
        'selected_type': notification_type,
        'selected_status': status,
    }
    
    return render(request, 'notifications/list.html', context)


@login_required
def notification_preferences(request):
    """Manage notification preferences"""
    try:
        preferences = request.user.notification_preferences
    except NotificationPreference.DoesNotExist:
        preferences = NotificationPreference.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
    else:
        form = NotificationPreferenceForm(instance=preferences)
    
    return render(request, 'notifications/preferences.html', {'form': form})


@login_required
def mark_notification_read(request, notification_id):
    """Mark single notification as read"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()
        
        return JsonResponse({
            'status': 'success',
            'unread_count': Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
        })
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)


@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return JsonResponse({'status': 'success', 'unread_count': 0})


@login_required
def delete_notification(request, notification_id):
    """Delete a notification"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.delete()
        
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)


@login_required
def get_unread_count(request):
    """Get unread notifications count"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return JsonResponse({'count': count})


@login_required
def get_recent_notifications(request):
    """Get recent notifications (for navbar dropdown)"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender').order_by('-created_at')[:10]

    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': str(notification.id),
            'type': notification.notification_type,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'sender': {
                'username': notification.sender.username if notification.sender else None,
                'profile_picture': notification.sender.profile_picture.url if notification.sender and notification.sender.profile_picture else None,
            } if notification.sender else None,
            'link': notification.target_url or '#',
        })

    return JsonResponse({
        'notifications': notifications_data,
        'count': len(notifications_data),
        'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count()
    })


def system_announcements(request):
    """View system announcements"""
    announcements = SystemAnnouncement.objects.filter(
        is_active=True
    ).filter(
        Q(show_until__isnull=True) | Q(show_until__gte=timezone.now())
    )
    
    # Filter by user type
    if request.user.is_authenticated:
        if request.user.user_type == 'fan':
            announcements = announcements.filter(
                Q(target_user_type='') | Q(target_user_type='fan')
            )
        elif request.user.user_type == 'celebrity':
            announcements = announcements.filter(
                Q(target_user_type='') | Q(target_user_type='celebrity')
            )
    
    return render(request, 'notifications/announcements.html', {
        'announcements': announcements
    })