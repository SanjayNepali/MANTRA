# MANTRA/config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Import main authentication views for convenience
from apps.accounts.views import (
    HomeView, FanRegistrationView, CelebrityRegistrationView,
    UnifiedLoginView, logout_view, dashboard_view, smart_feed_view
)
from apps.accounts.search_views import global_search, api_live_search

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Home/Landing
    path('', HomeView.as_view(), name='home'),

    # Quick Authentication (convenience URLs)
    path('signup/', TemplateView.as_view(template_name='accounts/signup_choice.html'), name='signup'),
    path('signup/', TemplateView.as_view(template_name='accounts/signup_choice.html'), name='signup_choice'),  # Alias
    path('signup/fan/', FanRegistrationView.as_view(), name='fan_register'),
    path('signup/celebrity/', CelebrityRegistrationView.as_view(), name='celebrity_register'),
    path('login/', UnifiedLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),

    # App URLs
    path('accounts/', include('apps.accounts.urls')),
    path('celebrities/', include('apps.celebrities.urls')),
    path('fans/', include('apps.fans.urls')),
    path('fanclubs/', include('apps.fanclubs.urls')),
    path('posts/', include('apps.posts.urls')),
    path('messaging/', include('apps.messaging.urls')),
    path('events/', include('apps.events.urls')),
    path('merchandise/', include('apps.merchandise.urls')),
    path('payments/', include('apps.payments.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('reports/', include('apps.reports.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('subadmin/', include('apps.subadmin.urls')),
    path('admin-dashboard/', include('apps.admin_dashboard.urls')),

    # API URLs
    path('api/v1/', include('api.urls')),

    # Static/Info Pages
    path('about/', TemplateView.as_view(template_name='pages/about.html'), name='about'),
    path('help/', TemplateView.as_view(template_name='pages/help.html'), name='help'),
    path('terms/', TemplateView.as_view(template_name='pages/terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='pages/privacy.html'), name='privacy'),
    path('contact/', TemplateView.as_view(template_name='pages/contact.html'), name='contact'),
    path('careers/', TemplateView.as_view(template_name='pages/careers.html'), name='careers'),
    path('faq/', TemplateView.as_view(template_name='pages/faq.html'), name='faq'),
    path('press/', TemplateView.as_view(template_name='pages/press.html'), name='press'),

    # Search
    path('search/', global_search, name='search'),
    path('api/search/', api_live_search, name='api_search'),

    # API endpoints for frontend
    path('api/notifications/', include('apps.notifications.urls')),
]

# Convenience URL aliases for templates
from django.urls import re_path
from django.views.generic import RedirectView

urlpatterns += [
    # Smart feed that routes based on user type
    path('feed/', smart_feed_view, name='feed'),
    path('discover/', smart_feed_view, name='discover'),  # Alias for feed/discover

    # Redirect aliases for template compatibility
    re_path(r'^feed/home/$', RedirectView.as_view(pattern_name='fan_feed', permanent=False), name='home_feed'),
    re_path(r'^events/$', RedirectView.as_view(pattern_name='event_list', permanent=False), name='events'),
    re_path(r'^fan-clubs/$', RedirectView.as_view(pattern_name='fanclub_list', permanent=False), name='fan_clubs'),
    re_path(r'^notifications/$', RedirectView.as_view(pattern_name='notifications_list', permanent=False), name='notifications'),
    re_path(r'^analytics/fan/$', RedirectView.as_view(pattern_name='celebrity_analytics', permanent=False), name='fan_analytics'),
    re_path(r'^analytics/system/$', RedirectView.as_view(pattern_name='admin_dashboard', permanent=False), name='system_analytics'),
    re_path(r'^merchandise/add/$', RedirectView.as_view(pattern_name='create_merchandise', permanent=False), name='add_merchandise'),

    # Additional navbar aliases
    re_path(r'^post/$', RedirectView.as_view(pattern_name='post_list', permanent=False), name='post'),
    re_path(r'^event/create/$', RedirectView.as_view(pattern_name='create_event', permanent=False), name='event_create'),
    re_path(r'^cart/$', RedirectView.as_view(pattern_name='view_cart', permanent=False), name='cart'),

    # Story and Live features (placeholder - to be implemented)
    path('story/create/', TemplateView.as_view(template_name='coming_soon.html'), name='story_create'),
    path('live/start/', TemplateView.as_view(template_name='coming_soon.html'), name='start_live'),
]

# Media files and Debug Toolbar in development
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'apps.accounts.views.error_404_view'
handler500 = 'apps.accounts.views.error_500_view'
handler403 = 'apps.accounts.views.error_403_view'
handler400 = 'apps.accounts.views.error_400_view'