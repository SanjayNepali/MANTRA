# apps/fanclubs/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.FanClubListView.as_view(), name='fanclub_list'),
    path('create/', views.create_fanclub, name='create_fanclub'),
    path('<slug:slug>/', views.FanClubDetailView.as_view(), name='fanclub_detail'),
    path('<slug:slug>/edit/', views.edit_fanclub, name='edit_fanclub'),
    path('<slug:slug>/join/', views.join_fanclub, name='join_fanclub'),
    path('<slug:slug>/leave/', views.leave_fanclub, name='leave_fanclub'),
    path('<slug:slug>/post/', views.post_in_fanclub, name='post_in_fanclub'),
]