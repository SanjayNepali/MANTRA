# apps/messaging/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count, Max
from django.utils import timezone

from apps.accounts.models import User, UserFollowing
from .models import Conversation, Message, MessageRequest
from .forms import MessageForm, MessageRequestForm

@login_required
def inbox_view(request):
    """View inbox with all conversations"""
    search_query = request.GET.get('search', '').strip()

    conversations = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    ).prefetch_related('participants').annotate(
        last_message_time=Max('messages__created_at'),
        unread_count=Count(
            'messages',
            filter=Q(
                messages__is_read=False,
                messages__is_deleted=False
            ) & ~Q(messages__sender=request.user)
        )
    )

    # Apply search filter if provided
    if search_query:
        # Search by conversation title (for groups) or participant username
        conversations = conversations.filter(
            Q(title__icontains=search_query) |
            Q(participants__username__icontains=search_query) |
            Q(participants__first_name__icontains=search_query) |
            Q(participants__last_name__icontains=search_query)
        ).distinct()

    conversations = conversations.order_by('-last_message_time')

    # Enhance conversations with display info
    conversations_list = []
    for conv in conversations:
        conv_data = {
            'conversation': conv,
            'unread_count': conv.unread_count
        }

        if conv.is_group:
            # Group chat or Fanclub chat
            conv_data['display_name'] = conv.title or "Group Chat"
            conv_data['display_image'] = conv.group_image.url if conv.group_image else None
            conv_data['is_group'] = True
            conv_data['is_fanclub'] = conv.is_fanclub
        else:
            # Direct message
            other_user = conv.get_other_participant(request.user)
            if other_user:
                conv_data['display_name'] = other_user.get_full_name() or other_user.username
                conv_data['display_username'] = f"@{other_user.username}"
                conv_data['display_image'] = other_user.avatar.url if hasattr(other_user, 'avatar') and other_user.avatar else None
                conv_data['other_user'] = other_user
            else:
                conv_data['display_name'] = "Unknown User"
                conv_data['display_username'] = ""
                conv_data['display_image'] = None
            conv_data['is_group'] = False

        # Get last message
        last_msg = conv.get_last_message()
        if last_msg:
            conv_data['last_message'] = last_msg.content
            conv_data['last_message_time'] = last_msg.created_at
        else:
            conv_data['last_message'] = "No messages yet"
            conv_data['last_message_time'] = conv.created_at

        conversations_list.append(conv_data)

    # Get message requests
    message_requests = MessageRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user')

    # Get followers and following for new message
    following = request.user.following.all().select_related('following')
    followers = request.user.followers.all().select_related('follower')

    # Users you can message (mutual follows)
    mutual_follows = []
    for follow in following:
        if UserFollowing.objects.filter(follower=follow.following, following=request.user).exists():
            mutual_follows.append(follow.following)

    context = {
        'conversations': conversations_list,
        'message_requests': message_requests,
        'message_requests_count': message_requests.count(),
        'search_query': search_query,
        'mutual_follows': mutual_follows,
    }

    return render(request, 'messaging/inbox.html', context)


@login_required
def conversation_view(request, conversation_id):
    """View single conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Check if user is participant
    if request.user not in conversation.participants.all():
        return HttpResponseForbidden()

    # Mark messages as read
    conversation.mark_as_read(request.user)

    # Get messages
    messages_list = conversation.messages.filter(
        is_deleted=False
    ).select_related('sender').order_by('created_at')

    # Determine conversation type and permissions
    can_message = True
    other_user = None
    is_fanclub_chat = False
    fanclub = None
    is_group_chat = False
    conversation_title = None
    conversation_image = None

    if conversation.is_group:
        is_group_chat = True
        conversation_title = conversation.title or "Group Chat"
        conversation_image = conversation.group_image.url if conversation.group_image else None

        # Check if this is a fan club group chat
        if hasattr(conversation, 'fanclub'):
            is_fanclub_chat = True
            fanclub = conversation.fanclub
            # Only celebrity can post in fanclub chats
            can_message = (request.user == conversation.fanclub_celebrity)
        else:
            # Regular group chat - all members can message
            can_message = True
    else:
        # Get other participant for direct messages
        other_user = conversation.get_other_participant(request.user)

        # Check if can message (mutual follow required)
        can_message = UserFollowing.objects.filter(
            follower=request.user,
            following=other_user
        ).exists() and UserFollowing.objects.filter(
            follower=other_user,
            following=request.user
        ).exists()

        # Override for celebrities - they can always message their fans
        if request.user.user_type == 'celebrity':
            can_message = True

    context = {
        'conversation': conversation,
        'other_user': other_user,
        'messages': messages_list,
        'can_message': can_message,
        'is_fanclub_chat': is_fanclub_chat,
        'fanclub': fanclub,
        'is_group_chat': is_group_chat,
        'conversation_title': conversation_title,
        'conversation_image': conversation_image,
    }

    return render(request, 'messaging/conversation.html', context)


@login_required
def start_conversation(request, username):
    """Start a new conversation"""
    other_user = get_object_or_404(User, username=username)
    
    if other_user == request.user:
        messages.error(request, "You can't message yourself")
        return redirect('inbox')
    
    # Check if mutual follow exists using utility function
    from .utils import can_message
    mutual_follow = can_message(request.user, other_user)
    
    # Check user preferences
    if other_user.preferences.who_can_message == 'nobody':
        messages.error(request, "This user doesn't accept messages")
        return redirect('profile', username=username)
    
    if other_user.preferences.who_can_message == 'mutual' and not mutual_follow:
        # Send message request instead
        return redirect('send_message_request', username=username)
    
    # Get or create conversation
    conversation, created = Conversation.get_or_create_conversation(
        request.user, other_user
    )
    
    return redirect('conversation', conversation_id=conversation.id)


@login_required
def send_message(request, conversation_id):
    """Send a message via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Check if user is participant
    if request.user not in conversation.participants.all():
        return JsonResponse({'error': 'Access denied'}, status=403)

    # Check fanclub posting restrictions
    if conversation.is_fanclub:
        try:
            fanclub = conversation.fanclub
            if not fanclub.can_post(request.user):
                return JsonResponse({
                    'error': 'Only the celebrity can post updates in this official fan club'
                }, status=403)
        except:
            # If fanclub doesn't exist or can't be accessed
            if conversation.fanclub_celebrity and request.user != conversation.fanclub_celebrity:
                return JsonResponse({
                    'error': 'Only the celebrity can post in this fanclub'
                }, status=403)

    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    if len(content) > 1000:
        return JsonResponse({'error': 'Message too long'}, status=400)

    # AI Sentiment Analysis for celebrity messages
    sentiment_data = None
    if request.user.user_type == 'celebrity':
        try:
            from utils.ai_content_moderation import analyze_text_content
            insights = analyze_text_content(content)

            # Check for negativity
            if insights['sentiment']['label'] in ['negative', 'very_negative']:
                sentiment_data = {
                    'sentiment': insights['sentiment']['label'],
                    'score': insights['sentiment']['score'],
                    'warning': 'This message has negative sentiment'
                }

            # Check toxicity
            if insights['toxicity']['is_toxic']:
                return JsonResponse({
                    'error': 'This message contains inappropriate content',
                    'toxic_words': insights['toxicity']['toxic_words'][:5],
                    'sentiment': insights['sentiment']
                }, status=400)

        except Exception as e:
            print(f"AI analysis error: {e}")

    # Create message
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content
    )

    # Update conversation timestamp
    conversation.last_message_at = timezone.now()
    conversation.save(update_fields=['last_message_at'])

    # Create notifications
    from apps.notifications.models import Notification

    if conversation.is_group:
        # For group chats, notify all participants except sender
        for participant in conversation.participants.exclude(id=request.user.id):
            Notification.objects.create(
                recipient=participant,
                sender=request.user,
                notification_type='message',
                message=f'{request.user.username} sent a message in {conversation.title}',
                target_id=str(conversation.id)
            )
    else:
        # For direct messages, notify the other user
        other_user = conversation.get_other_participant(request.user)
        if other_user:
            Notification.objects.create(
                recipient=other_user,
                sender=request.user,
                notification_type='message',
                message=f'{request.user.username} sent you a message',
                target_id=str(conversation.id)
            )
    
    response_data = {
        'status': 'success',
        'message': {
            'id': str(message.id),
            'content': message.content,
            'sender': {
                'id': str(message.sender.id),
                'username': message.sender.username,
                'full_name': message.sender.get_full_name() or message.sender.username,
                'profile_picture': message.sender.profile_picture.url if hasattr(message.sender, 'profile_picture') and message.sender.profile_picture else None
            },
            'created_at': message.created_at.isoformat()
        }
    }

    # Add sentiment data if available
    if sentiment_data:
        response_data['sentiment'] = sentiment_data

    return JsonResponse(response_data)


@login_required
def send_message_request(request, username):
    """Send message request to non-mutual follower"""
    to_user = get_object_or_404(User, username=username)
    
    if to_user == request.user:
        messages.error(request, "Invalid request")
        return redirect('inbox')
    
    # Check if request already exists
    existing_request = MessageRequest.objects.filter(
        from_user=request.user,
        to_user=to_user
    ).first()
    
    if existing_request:
        if existing_request.status == 'pending':
            messages.info(request, "Message request already sent")
        elif existing_request.status == 'rejected':
            messages.error(request, "Your message request was rejected")
        else:
            return redirect('start_conversation', username=username)
        return redirect('profile', username=username)
    
    if request.method == 'POST':
        form = MessageRequestForm(request.POST)
        
        if form.is_valid():
            message_request = form.save(commit=False)
            message_request.from_user = request.user
            message_request.to_user = to_user
            message_request.save()
            
            # Create notification
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=to_user,
                sender=request.user,
                notification_type='message_request',
                message=f'{request.user.username} wants to message you'
            )
            
            messages.success(request, "Message request sent!")
            return redirect('profile', username=username)
    else:
        form = MessageRequestForm()
    
    return render(request, 'messaging/message_request.html', {
        'form': form,
        'to_user': to_user
    })


@login_required
def handle_message_request(request, request_id):
    """Accept or reject message request"""
    message_request = get_object_or_404(
        MessageRequest,
        id=request_id,
        to_user=request.user,
        status='pending'
    )
    
    action = request.POST.get('action')
    
    if action == 'accept':
        message_request.accept()
        messages.success(request, f"You can now chat with {message_request.from_user.username}")
        
        # Create notification
        from apps.notifications.models import Notification
        Notification.objects.create(
            recipient=message_request.from_user,
            sender=request.user,
            notification_type='message_request_accepted',
            message=f'{request.user.username} accepted your message request'
        )
        
        # Redirect to conversation
        conversation, _ = Conversation.get_or_create_conversation(
            request.user, message_request.from_user
        )
        return redirect('conversation', conversation_id=conversation.id)
    
    elif action == 'reject':
        message_request.reject()
        messages.info(request, "Message request rejected")
    
    return redirect('inbox')