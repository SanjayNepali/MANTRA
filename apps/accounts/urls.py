# apps/accounts/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.UnifiedLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/fan/', views.FanRegistrationView.as_view(), name='fan_register'),
    path('register/celebrity/', views.CelebrityRegistrationView.as_view(), name='celebrity_register'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Profile
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile-edit/', views.edit_profile_view, name='edit_profile'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/password/', views.change_password_view, name='change_password'),
    path('settings/deactivate/', views.deactivate_account, name='deactivate_account'),
    path('settings/delete/', views.delete_account, name='delete_account'),
    
    # Follow/Unfollow
    path('follow/<str:username>/', views.follow_user_view, name='follow_user'),
    path('followers/<str:username>/', views.followers_list_view, name='followers_list'),
    path('following/<str:username>/', views.following_list_view, name='following_list'),
    
    # Points
    path('points/history/', views.points_history_view, name='points_history'),
    
    # Celebrity suggestions for new users
    path('welcome/follow/', views.celebrity_follow_suggestions, name='celebrity_follow_suggestions'),
]