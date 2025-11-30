# apps/posts/views.py - Enhanced with Algorithm Integration

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.db.models import Q, F, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.db import transaction

from apps.posts.models import Post, Like, Comment, CommentLike, Share, PostReport, PostView, CommentReport
from apps.posts.forms import PostCreateForm, CommentForm, PostReportForm, PostEditForm


class PostListView(ListView):
    """Enhanced post list with recommendation algorithm"""
    model = Post
    template_name = 'posts/list.html'
    context_object_name = 'posts'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = Post.objects.filter(
            is_active=True
        ).select_related(
            'author',
            'author__celebrity_profile',
            'author__fan_profile'
        ).prefetch_related(
            'likes',
            'comments'
        )
        
        # Filter exclusive posts for non-subscribers
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_exclusive=False)
        
        # Get filter type
        filter_type = self.request.GET.get('filter', 'recommended')
        
        if filter_type == 'following' and self.request.user.is_authenticated:
            # Posts from followed users
            from apps.accounts.models import UserFollowing
            following_ids = UserFollowing.objects.filter(
                follower=self.request.user
            ).values_list('following_id', flat=True)
            queryset = queryset.filter(author_id__in=following_ids)
            
        elif filter_type == 'trending':
            # Use TrendingEngine
            try:
                from algorithms.recommendation import TrendingEngine
                trending_posts = TrendingEngine.calculate_trending_posts(days=3, limit=50)
                trending_ids = [p.id for p in trending_posts]
                queryset = queryset.filter(id__in=trending_ids)
            except ImportError:
                queryset = queryset.order_by('-likes_count', '-comments_count')
            
        elif filter_type == 'exclusive' and self.request.user.is_authenticated:
            # Exclusive posts user can access
            queryset = queryset.filter(is_exclusive=True)
            
        elif filter_type == 'recommended' and self.request.user.is_authenticated:
            # Use RecommendationEngine
            try:
                from algorithms.recommendation import RecommendationEngine
                engine = RecommendationEngine()
                recommended = engine.get_user_recommendations(
                    self.request.user,
                    recommendation_type='posts',
                    limit=50
                )
                if recommended and 'posts' in recommended:
                    recommended_ids = [p.id for p in recommended['posts']]
                    queryset = queryset.filter(id__in=recommended_ids)
                else:
                    # Fallback to mixed content
                    queryset = queryset.order_by('-created_at')
            except ImportError:
                queryset = queryset.order_by('-created_at')
        else:
            # Default: Recent posts
            queryset = queryset.order_by('-created_at')
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            try:
                from algorithms.string_matching import StringMatcher
                # Use fuzzy matching for better search
                all_posts = queryset.all()
                
                def get_searchable_text(post):
                    return f"{post.content} {' '.join(post.tags or [])}"
                
                results = StringMatcher.search_rank(
                    search_query,
                    all_posts,
                    get_searchable_text,
                    threshold=0.3
                )
                
                # Extract posts from results
                post_ids = [post.id for post, score in results]
                queryset = queryset.filter(id__in=post_ids)
            except ImportError:
                # Fallback to basic search
                queryset = queryset.filter(
                    Q(content__icontains=search_query) |
                    Q(tags__icontains=search_query)
                )
        
        # Tag filter
        tag_filter = self.request.GET.get('tag')
        if tag_filter:
            queryset = queryset.filter(tags__contains=[tag_filter])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add liked posts for authenticated users
        if self.request.user.is_authenticated:
            liked_posts = Like.objects.filter(
                user=self.request.user,
                post__in=context['posts']
            ).values_list('post_id', flat=True)
            context['liked_posts'] = list(liked_posts)

        # Get trending hashtags
        try:
            from algorithms.recommendation import TrendingEngine
            context['trending_hashtags'] = TrendingEngine.calculate_trending_hashtags(
                days=7,
                limit=10
            )
        except ImportError:
            context['trending_hashtags'] = []

        # Add engagement predictions for posts
        try:
            from algorithms.engagement import EngagementPredictor
            predictor = EngagementPredictor()
            engagement_predictions = {}
            for post in context['posts']:
                engagement_predictions[post.id] = predictor.predict_engagement(post)
            context['engagement_predictions'] = engagement_predictions
        except Exception:
            context['engagement_predictions'] = {}

        # Add filter info
        context['current_filter'] = self.request.GET.get('filter', 'recommended')

        return context


class PostDetailView(DetailView):
    """Enhanced post detail with view tracking and recommendations"""
    model = Post
    template_name = 'posts/detail.html'
    context_object_name = 'post'
    
    def get_object(self):
        post = super().get_object()
        
        # Check if user can view
        if not post.can_view(self.request.user):
            raise Http404("Post not found or you don't have access")
        
        # Track view
        if self.request.user.is_authenticated:
            PostView.objects.get_or_create(
                user=self.request.user,
                post=post
            )
        
        # Increment view count
        post.views_count = F('views_count') + 1
        post.save(update_fields=['views_count'])
        post.refresh_from_db()
        
        return post
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        
        # Check if liked
        if self.request.user.is_authenticated:
            context['is_liked'] = Like.objects.filter(
                user=self.request.user,
                post=post
            ).exists()
        else:
            context['is_liked'] = False
        
        # Get top-level comments with replies
        comments = Comment.objects.filter(
            post=post,
            parent=None,
            is_active=True
        ).select_related(
            'author',
            'author__celebrity_profile'
        ).prefetch_related(
            Prefetch(
                'replies',
                queryset=Comment.objects.filter(is_active=True).select_related('author')
            )
        ).order_by('-is_pinned', '-created_at')[:20]
        
        context['comments'] = comments
        context['comment_form'] = CommentForm()

        # Get engagement prediction for this post
        try:
            from algorithms.engagement import EngagementPredictor
            predictor = EngagementPredictor()
            engagement_prediction = predictor.predict_engagement(post)
            context['engagement_prediction'] = engagement_prediction
        except Exception:
            context['engagement_prediction'] = None

        # Get related posts using recommendation engine
        if self.request.user.is_authenticated:
            try:
                from algorithms.matching import MatchingEngine
                matcher = MatchingEngine()

                # Get similar posts based on tags and content
                similar_posts = Post.objects.filter(
                    is_active=True,
                    author=post.author
                ).exclude(id=post.id)[:5]

                context['related_posts'] = similar_posts
            except ImportError:
                context['related_posts'] = []

        return context


@login_required
@require_http_methods(["GET", "POST"])
def create_post(request):
    """Create post with AI-powered content analysis"""
    
    if request.method == 'POST':
        form = PostCreateForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.author = request.user

                # AI Content Analysis
                content = post.content
                analysis_passed = True
                warnings = []
                flag_for_review = False  # Initialize outside try block
                moderation_result = None  # Initialize for later use

                try:
                    from algorithms.sentiment import SentimentAnalyzer, EngagementPredictor
                    from algorithms.integration import moderate_post_content

                    # Content moderation (flagging instead of blocking)
                    moderation_result = moderate_post_content(content)

                    # Flag content if needed (but don't block posting)
                    if moderation_result['should_flag']:
                        post.is_reported = True
                        # Add warning message but allow posting
                        messages.warning(
                            request,
                            f"Your post has been published but flagged for review: {moderation_result['flag_reason']}"
                        )
                        # Notify subadmins after post is saved (will be called after post.save())
                        flag_for_review = True
                    
                    # Sentiment analysis
                    analyzer = SentimentAnalyzer()
                    sentiment = analyzer.analyze_sentiment(content)
                    toxicity = analyzer.detect_toxicity(content)
                    spam = analyzer.detect_spam(content)

                    # Override sentiment if toxic content detected
                    if toxicity['is_toxic']:
                        # Force negative label for toxic content
                        post.sentiment_score = -0.8
                        post.sentiment_label = 'negative'
                    else:
                        # Store normal sentiment data
                        post.sentiment_score = sentiment['score']
                        post.sentiment_label = sentiment['label']
                    
                    # Check for warnings
                    if toxicity['is_toxic'] and toxicity['severity'] in ['medium', 'high']:
                        warnings.append({
                            'type': 'toxicity',
                            'message': f"Potentially toxic content detected (severity: {toxicity['severity']})",
                            'details': toxicity['toxic_words'][:3]
                        })
                    
                    if spam['is_spam'] and spam['spam_score'] > 0.6:
                        warnings.append({
                            'type': 'spam',
                            'message': "Content may be flagged as spam",
                            'details': spam['spam_indicators'][:2]
                        })
                    
                    # If warnings exist, show them to user for confirmation
                    if warnings and not request.POST.get('confirm_warnings'):
                        return render(request, 'posts/create.html', {
                            'form': form,
                            'warnings': warnings,
                            'sentiment': sentiment,
                            'requires_confirmation': True
                        })
                    
                    # Engagement prediction
                    predictor = EngagementPredictor()
                    author_stats = {
                        'followers_count': request.user.followers.count() if hasattr(request.user, 'followers') else 0
                    }
                    engagement = predictor.predict_post_engagement(content, author_stats)
                    
                except Exception as e:
                    print(f"Content analysis error: {e}")
                    post.sentiment_score = 0.0
                    post.sentiment_label = 'neutral'
                    engagement = {'engagement_score': 0}
                    toxicity = {'is_toxic': False, 'severity': 'low', 'toxic_words': []}

                # Save the post
                post.published_at = timezone.now()

                # Keep post active - we're flagging, not hiding
                post.save()

                # Notify subadmins if flagged
                if flag_for_review and moderation_result:
                    from algorithms.integration import notify_subadmin_of_flagged_content
                    notify_subadmin_of_flagged_content(
                        post,
                        moderation_result['flag_reason'],
                        moderation_result['flag_severity']
                    )

                # Award points (reduced for flagged content)
                try:
                    if flag_for_review:
                        request.user.add_points(5, "Created a post")  # Reduced points for flagged content
                    else:
                        request.user.add_points(10, "Created a post")
                except AttributeError:
                    pass

                # Create auto-report for flagged content
                if flag_for_review and moderation_result:
                    from apps.reports.models import Report
                    try:
                        Report.objects.create(
                            content_type='post',
                            content_id=post.id,
                            reported_by=request.user,
                            reason='hate_speech',
                            description=f"Auto-flagged: {moderation_result['flag_reason']}",
                            status='pending'
                        )
                    except Exception as e:
                        print(f"Error creating auto-report: {e}")

                # Create SubAdmin moderation alert for flagged content
                if flag_for_review and moderation_result:
                    from apps.subadmin.models import ContentModerationAlert

                    # Count previous violations
                    try:
                        previous_violations = ContentModerationAlert.objects.filter(
                            content_author=request.user,
                            status='resolved',
                            action_taken__in=['warned', 'content_removed', 'user_suspended']
                        ).count()
                    except:
                        previous_violations = 0

                    # Determine alert type based on moderation results
                    alert_type = 'toxicity'
                    if toxicity.get('toxicity_score', 0) > 0.7:
                        alert_type = 'hate_speech'
                    elif spam.get('is_spam', False):
                        alert_type = 'spam'

                    # Create alert
                    try:
                        alert = ContentModerationAlert.objects.create(
                            content_type='post',
                            content_id=post.id,
                            content_text=content[:500],  # First 500 chars
                            content_author=request.user,
                            alert_type=alert_type,
                            severity='critical' if moderation_result.get('flag_severity') == 'high' else 'high',
                            toxicity_score=toxicity.get('toxicity_score', 0),
                            toxic_words=toxicity.get('toxic_words', [])[:10],
                            sentiment_score=sentiment.get('score', 0),
                            sentiment_label=sentiment.get('label', 'neutral'),
                            spam_score=spam.get('spam_score', 0),
                            user_previous_violations=previous_violations,
                            is_repeat_offender=previous_violations >= 2
                        )

                        # Auto-assign to SubAdmin
                        alert.assign_to_subadmin()
                    except Exception as e:
                        print(f"Error creating moderation alert: {e}")

                # Update celebrity statistics
                if hasattr(request.user, 'user_type') and request.user.user_type == 'celebrity':
                    try:
                        profile = request.user.celebrity_profile
                        profile.total_posts = F('total_posts') + 1
                        profile.save(update_fields=['total_posts'])
                    except Exception as e:
                        print(f"Error updating celebrity stats: {e}")

                # Create notifications for mentioned users
                if post.mentioned_users:
                    try:
                        from apps.notifications.models import Notification
                        from apps.accounts.models import User
                        
                        for user_id in post.mentioned_users:
                            try:
                                mentioned_user = User.objects.get(id=user_id)
                                Notification.objects.create(
                                    recipient=mentioned_user,
                                    sender=request.user,
                                    notification_type='mention',
                                    message=f'{request.user.username} mentioned you in a post',
                                    target_id=str(post.id)
                                )
                            except User.DoesNotExist:
                                pass
                    except ImportError:
                        pass

                # Success message with engagement insights
                if engagement.get('engagement_score', 0) > 70:
                    messages.success(
                        request,
                        f'🎉 Post created! High engagement potential detected '
                        f'(~{engagement.get("predicted_likes", 0)} likes predicted)'
                    )
                else:
                    messages.success(request, 'Post created successfully!')

                return redirect('post_detail', pk=post.id)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = PostCreateForm(user=request.user)

    return render(request, 'posts/create.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def like_post(request, pk):
    """Like/unlike a post with analytics"""
    post = get_object_or_404(Post, pk=pk)
    
    if not post.can_view(request.user):
        return JsonResponse({'error': 'Cannot access this post'}, status=403)
    
    like, created = Like.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        # Unlike
        like.delete()
        post.likes_count = F('likes_count') - 1
        post.save(update_fields=['likes_count'])
        post.refresh_from_db()
        
        return JsonResponse({
            'status': 'unliked',
            'likes_count': post.likes_count
        })
    else:
        # Like
        post.likes_count = F('likes_count') + 1
        post.save(update_fields=['likes_count'])
        post.refresh_from_db()
        
        # Award points
        try:
            request.user.add_points(2, "Liked a post")
            post.author.add_points(1, f"Post liked by {request.user.username}")
        except AttributeError:
            pass
        
        # Create notification
        if post.author != request.user:
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    notification_type='like',
                    message=f'{request.user.username} liked your post',
                    target_id=str(post.id)
                )
            except ImportError:
                pass
        
        return JsonResponse({
            'status': 'liked',
            'likes_count': post.likes_count
        })


@login_required
@require_http_methods(["POST"])
def comment_on_post(request, pk):
    """Add comment with sentiment analysis"""
    post = get_object_or_404(Post, pk=pk)
    
    if not post.can_view(request.user):
        return HttpResponseForbidden()
    
    if not post.allow_comments:
        messages.error(request, 'Comments are disabled for this post')
        return redirect('post_detail', pk=post.id)
    
    form = CommentForm(request.POST)
    
    if form.is_valid():
        comment_content = form.cleaned_data['content']

        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user

        # Run AI sentiment analysis on comment
        try:
            from algorithms.sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer()

            # Get comprehensive analysis
            insights = analyzer.get_content_insights(comment_content)

            # Store toxicity and spam scores
            comment.toxicity_score = insights['toxicity']['toxicity_score']
            comment.spam_score = insights['spam']['spam_score']
            comment.sentiment_score = insights['sentiment']['score']
            comment.sentiment_label = insights['sentiment']['label']

            # Check if comment should be blocked (high toxicity)
            if insights['toxicity']['toxicity_score'] >= 0.75:
                comment.is_blocked = True
                comment.is_active = False
                comment.ai_flagged = True
                comment.ai_flag_reason = f"High toxicity: {insights['toxicity']['severity']}"

                # Save the comment as blocked
                comment.save()

                # Create AI alert for SubAdmin review
                try:
                    from apps.subadmin.models import ContentModerationAlert

                    alert = ContentModerationAlert.objects.create(
                        content_type='comment',
                        content_id=comment.id,
                        content_text=comment_content[:500],
                        content_author=request.user,
                        alert_type='toxicity',
                        severity='high',
                        toxicity_score=insights['toxicity']['toxicity_score'],
                        toxic_words=insights['toxicity']['toxic_words'][:10],
                        sentiment_score=insights['sentiment']['score'],
                        sentiment_label=insights['sentiment']['label'],
                        spam_score=insights['spam']['spam_score'],
                        user_previous_violations=0
                    )
                    # Auto-assign to SubAdmin
                    alert.assign_to_subadmin()
                except Exception as e:
                    print(f"Error creating alert: {e}")

                messages.error(
                    request,
                    "Your comment has been blocked due to inappropriate content. It will be reviewed by our moderation team."
                )
                return redirect('post_detail', pk=post.id)

            # Flag for review if moderately toxic or spammy
            elif insights['toxicity']['toxicity_score'] >= 0.5 or insights['spam']['spam_score'] >= 0.6:
                comment.ai_flagged = True
                if insights['toxicity']['toxicity_score'] >= 0.5:
                    comment.ai_flag_reason = f"Moderate toxicity: {insights['toxicity']['severity']}"
                else:
                    comment.ai_flag_reason = "Potential spam detected"

                # Create AI alert for SubAdmin review
                try:
                    from apps.subadmin.models import ContentModerationAlert

                    severity = 'medium' if insights['toxicity']['toxicity_score'] >= 0.6 else 'low'
                    alert_type = 'toxicity' if insights['toxicity']['toxicity_score'] >= 0.5 else 'spam'

                    alert = ContentModerationAlert.objects.create(
                        content_type='comment',
                        content_id=comment.id,
                        content_text=comment_content[:500],
                        content_author=request.user,
                        alert_type=alert_type,
                        severity=severity,
                        toxicity_score=insights['toxicity']['toxicity_score'],
                        toxic_words=insights['toxicity'].get('toxic_words', [])[:10],
                        sentiment_score=insights['sentiment']['score'],
                        sentiment_label=insights['sentiment']['label'],
                        spam_score=insights['spam']['spam_score'],
                        user_previous_violations=0
                    )
                    # Auto-assign to SubAdmin
                    alert.assign_to_subadmin()
                except Exception as e:
                    print(f"Error creating alert: {e}")
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            # Continue even if sentiment analysis fails
        
        # Check if it's a reply
        parent_id = request.POST.get('parent_id')
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id, post=post)
            comment.parent = parent_comment
            
            # Update parent's reply count
            parent_comment.replies_count = F('replies_count') + 1
            parent_comment.save(update_fields=['replies_count'])
        
        comment.save()
        
        # Update post comment count
        post.comments_count = F('comments_count') + 1
        post.save(update_fields=['comments_count'])
        
        # Award points
        try:
            request.user.add_points(5, "Commented on a post")
        except AttributeError:
            pass
        
        # Create notification
        if post.author != request.user:
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    notification_type='comment',
                    message=f'{request.user.username} commented on your post',
                    target_id=str(post.id)
                )
            except ImportError:
                pass
        
        messages.success(request, 'Comment added successfully!')
        return redirect('post_detail', pk=post.id)
    
    messages.error(request, 'Invalid comment')
    return redirect('post_detail', pk=post.id)


@login_required
@require_http_methods(["GET", "POST"])
def edit_post(request, pk):
    """Edit post with re-analysis"""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    
    if not post.is_active:
        messages.error(request, 'Cannot edit inactive post')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PostEditForm(request.POST, request.FILES, instance=post)
        
        if form.is_valid():
            updated_post = form.save(commit=False)
            
            # Re-analyze content
            try:
                from algorithms.integration import moderate_post_content
                
                content = updated_post.content
                moderation = moderate_post_content(content)

                # Flag content if needed (but don't block editing)
                if moderation['should_flag']:
                    updated_post.is_reported = True
                    messages.warning(
                        request,
                        f"Your post has been updated but flagged for review: {moderation['flag_reason']}"
                    )

                # Update sentiment
                updated_post.sentiment_score = moderation['analysis']['sentiment']['score']
                updated_post.sentiment_label = moderation['analysis']['sentiment']['label']
                
            except ImportError:
                pass
            
            # Mark as edited
            updated_post.is_edited = True
            updated_post.edited_at = timezone.now()
            updated_post.save()
            
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', pk=post.id)
    else:
        form = PostEditForm(instance=post)
    
    return render(request, 'posts/edit.html', {
        'form': form,
        'post': post
    })


@login_required
@require_http_methods(["GET", "POST"])
def delete_post(request, pk):
    """Delete post"""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    
    if request.method == 'POST':
        post.is_active = False
        post.save()
        
        messages.success(request, 'Post deleted successfully!')
        return redirect('profile', username=request.user.username)
    
    return render(request, 'posts/delete_confirm.html', {'post': post})


@login_required
@require_http_methods(["POST"])
def share_post(request, pk):
    """Share/repost with tracking"""
    post = get_object_or_404(Post, pk=pk)
    
    if not post.can_view(request.user):
        return JsonResponse({'error': 'Cannot share this post'}, status=403)
    
    if not post.allow_sharing:
        return JsonResponse({'error': 'Sharing disabled for this post'}, status=403)
    
    # Check if already shared
    existing_share = Share.objects.filter(
        user=request.user,
        post=post
    ).first()
    
    if existing_share:
        return JsonResponse({'error': 'Already shared'}, status=400)
    
    # Create share
    text = request.POST.get('text', '')
    share = Share.objects.create(
        user=request.user,
        post=post,
        text=text
    )
    
    # Update share count
    post.shares_count = F('shares_count') + 1
    post.save(update_fields=['shares_count'])
    post.refresh_from_db()
    
    # Award points
    try:
        request.user.add_points(3, "Shared a post")
    except AttributeError:
        pass
    
    return JsonResponse({
        'status': 'shared',
        'shares_count': post.shares_count
    })


@login_required
@require_http_methods(["GET", "POST"])
def report_post(request, pk):
    """Report post with tracking"""
    post = get_object_or_404(Post, pk=pk)
    
    # Check if already reported
    existing_report = PostReport.objects.filter(
        post=post,
        reported_by=request.user
    ).first()
    
    if existing_report:
        messages.warning(request, 'You have already reported this post')
        return redirect('post_detail', pk=post.id)
    
    if request.method == 'POST':
        form = PostReportForm(request.POST)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.post = post
            report.reported_by = request.user
            report.save()
            
            # Mark post as reported
            post.is_reported = True
            post.save(update_fields=['is_reported'])
            
            messages.success(
                request,
                'Thank you for your report. Our team will review it shortly.'
            )
            return redirect('post_detail', pk=post.id)
    else:
        form = PostReportForm()
    
    return render(request, 'posts/report.html', {
        'form': form,
        'post': post
    })


@login_required
def report_comment(request, comment_id):
    """Report a comment"""
    comment = get_object_or_404(Comment, id=comment_id)

    # Check if user already reported this comment
    existing_report = CommentReport.objects.filter(
        comment=comment,
        reported_by=request.user
    ).first()

    if existing_report:
        messages.warning(request, 'You have already reported this comment.')
        return redirect('post_detail', pk=comment.post.id)

    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description', '')

        if reason:
            # Create comment report
            CommentReport.objects.create(
                comment=comment,
                reported_by=request.user,
                reason=reason,
                description=description,
                status='pending'
            )

            # Mark comment as reported
            comment.is_reported = True
            comment.save(update_fields=['is_reported'])

            # Create notification for subadmins in the region
            try:
                from apps.notifications.models import Notification
                from apps.accounts.models import User

                # Get subadmins for this region
                user_region = request.user.region if hasattr(request.user, 'region') else 'Global'
                subadmins = User.objects.filter(
                    user_type='subadmin',
                    is_active=True,
                    region=user_region
                )

                for subadmin in subadmins:
                    Notification.objects.create(
                        recipient=subadmin,
                        sender=request.user,
                        notification_type='comment_report',
                        message=f'New comment report: {reason}',
                        target_id=str(comment.id)
                    )
            except Exception as e:
                print(f"Error creating notification: {e}")

            messages.success(
                request,
                'Thank you for your report. Our team will review it shortly.'
            )
            return redirect('post_detail', pk=comment.post.id)

    return render(request, 'posts/report_comment.html', {
        'comment': comment,
        'report_reasons': CommentReport.REPORT_REASONS
    })