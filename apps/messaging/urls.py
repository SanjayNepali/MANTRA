# apps/messaging/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('inbox/', views.inbox_view, name='inbox'),
    path('conversation/<uuid:conversation_id>/', views.conversation_view, name='conversation'),
    path('start/<str:username>/', views.start_conversation, name='start_conversation'),
    path('send/<uuid:conversation_id>/', views.send_message, name='send_message'),
    path('request/<str:username>/', views.send_message_request, name='send_message_request'),
    path('request/handle/<int:request_id>/', views.handle_message_request, name='handle_message_request'),
]