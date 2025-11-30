# utils/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

def celebrity_required(view_func):
    """Decorator to ensure user is a verified celebrity"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Authentication required'}, status=401)
            return redirect('login')
        
        if request.user.user_type != 'celebrity':
            messages.error(request, 'This page is only accessible to celebrities.')
            return redirect('dashboard')
        
        # Check if celebrity profile exists and is verified
        if hasattr(request.user, 'celebrity_profile'):
            if request.user.celebrity_profile.verification_status != 'approved':
                messages.warning(request, 'Your celebrity account needs to be verified first.')
                return redirect('celebrity_verification')
        else:
            messages.error(request, 'Celebrity profile not found.')
            return redirect('profile_setup')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def fan_required(view_func):
    """Decorator to ensure user is a fan"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.user_type != 'fan':
            messages.error(request, 'This page is only accessible to fans.')
            return redirect('dashboard')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """Decorator to ensure user is admin or superuser"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not (request.user.is_superuser or request.user.user_type == 'admin'):
            messages.error(request, 'Admin access required.')
            raise PermissionDenied
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def subadmin_required(view_func):
    """Decorator to ensure user is subadmin"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.user_type != 'subadmin':
            messages.error(request, 'SubAdmin access required.')
            raise PermissionDenied
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def points_required(min_points):
    """Decorator to check if user has minimum points"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
                
            if request.user.points < min_points:
                messages.error(request, f'You need at least {min_points} points to access this feature.')
                return redirect('points_history')
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def ajax_required(view_func):
    """Decorator to ensure request is AJAX"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'error': 'AJAX request required'}, status=400)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def verified_email_required(view_func):
    """Decorator to ensure user has verified email"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
            
        if not request.user.is_verified:
            messages.warning(request, 'Please verify your email address first.')
            return redirect('email_verification')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def mutual_follow_required(view_func):
    """Decorator for features requiring mutual follow between users"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
            
        # Extract target user from kwargs or request
        target_user_id = kwargs.get('user_id') or request.POST.get('user_id')
        if not target_user_id:
            messages.error(request, 'User not specified.')
            return redirect('dashboard')
            
        # Check mutual follow status
        from apps.accounts.models import UserFollowing
        
        is_following = UserFollowing.objects.filter(
            follower=request.user,
            following_id=target_user_id,
            is_active=True
        ).exists()
        
        is_followed_back = UserFollowing.objects.filter(
            follower_id=target_user_id,
            following=request.user,
            is_active=True
        ).exists()
        
        if not (is_following and is_followed_back):
            messages.error(request, 'Mutual follow required for this action.')
            return redirect('profile', user_id=target_user_id)
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view