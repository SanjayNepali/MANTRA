# apps/posts/urls.py

from django.urls import path
from . import views
from . import api_views  # Import the API views

urlpatterns = [
    # Post views
    path('', views.PostListView.as_view(), name='post_list'),
    path('create/', views.create_post, name='create_post'),
    path('<uuid:pk>/', views.PostDetailView.as_view(), name='post_detail'),
    path('<uuid:pk>/delete/', views.delete_post, name='delete_post'),
    path('<uuid:pk>/edit/', views.edit_post, name='edit_post'),
    # Interactions
    path('<uuid:pk>/like/', views.like_post, name='like_post'),
    path('<uuid:pk>/comment/', views.comment_on_post, name='comment_on_post'),
    path('<uuid:pk>/share/', views.share_post, name='share_post'),
    path('<uuid:pk>/report/', views.report_post, name='report_post'),
    path('comment/<uuid:comment_id>/report/', views.report_comment, name='report_comment'),
    
    # API endpoints
    path('api/analyze-content/', api_views.analyze_content_api, name='analyze_content_api'),
    path('api/suggested-users/', api_views.get_suggested_users_api, name='suggested_users_api'),
    path('api/trending-hashtags/', api_views.get_trending_hashtags_api, name='trending_hashtags_api'),
    path('api/post-recommendations/', api_views.get_post_recommendations_api, name='post_recommendations_api'),
    path('api/engagement-prediction/', api_views.calculate_engagement_prediction_api, name='engagement_prediction_api'),
    path('api/check-similar-posts/', api_views.check_similar_posts_api, name='check_similar_posts_api'),
    path('api/post-stats/<uuid:pk>/', api_views.get_post_stats_api, name='post_stats_api'),
]