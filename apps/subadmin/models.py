# apps/subadmin/models.py
"""
SubAdmin Models for extended functionality
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class SubAdminActivityReport(models.Model):
    """Activity reports submitted by SubAdmins to Admin"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subadmin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_reports'
    )
    region = models.CharField(max_length=100)
    
    # Report period
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Report data (stored as JSON)
    reports_data = models.JSONField(default=dict)
    
    # Metrics
    reports_resolved = models.IntegerField(default=0)
    kyc_processed = models.IntegerField(default=0)
    warnings_issued = models.IntegerField(default=0)
    suspensions_issued = models.IntegerField(default=0)
    bans_issued = models.IntegerField(default=0)
    
    # Average sentiment scores
    avg_toxicity_score = models.FloatField(default=0)
    avg_spam_score = models.FloatField(default=0)
    
    # Admin review
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('needs_improvement', 'Needs Improvement'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_activity_reports'
    )
    review_notes = models.TextField(blank=True)
    admin_feedback = models.TextField(blank=True, help_text="Detailed feedback from admin")
    performance_rating = models.IntegerField(default=0, help_text="Rating 1-5")

    # Timestamps
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['subadmin', '-submitted_at']),
            models.Index(fields=['region', '-submitted_at']),
        ]
    
    def __str__(self):
        return f"Activity Report - {self.region} ({self.period_start} to {self.period_end})"


class RegionalAlert(models.Model):
    """Alerts for SubAdmins about issues in their region"""
    
    ALERT_TYPES = (
        ('high_toxicity', 'High Toxicity Content'),
        ('spam_wave', 'Spam Wave Detected'),
        ('mass_reporting', 'Mass Reporting Activity'),
        ('ban_evasion', 'Potential Ban Evasion'),
        ('impersonation', 'Celebrity Impersonation'),
        ('urgent_kyc', 'Urgent KYC Verification'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.CharField(max_length=100)
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # Alert details
    title = models.CharField(max_length=200)
    description = models.TextField()
    affected_users = models.JSONField(default=list)  # List of user IDs
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='regional_alerts'
    )
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['region', 'is_resolved', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.priority.upper()}] {self.title}"


class ModeratedContent(models.Model):
    """Track all content moderated by SubAdmins"""
    
    CONTENT_TYPES = (
        ('post', 'Post'),
        ('comment', 'Comment'),
        ('message', 'Message'),
        ('profile', 'Profile'),
    )
    
    MODERATION_ACTIONS = (
        ('approved', 'Approved'),
        ('edited', 'Edited'),
        ('deleted', 'Deleted'),
        ('hidden', 'Hidden'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content reference
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content_id = models.CharField(max_length=100)
    original_content = models.TextField()  # Store original for records
    
    # Moderation details
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moderated_content'
    )
    moderation_action = models.CharField(max_length=20, choices=MODERATION_ACTIONS)
    reason = models.TextField()
    
    # Sentiment analysis results
    sentiment_score = models.FloatField()
    toxicity_score = models.FloatField()
    spam_score = models.FloatField()
    severity = models.CharField(max_length=20)
    
    # User info
    content_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_content_authored'
    )
    
    # Timestamps
    moderated_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-moderated_at']
        indexes = [
            models.Index(fields=['moderated_by', '-moderated_at']),
            models.Index(fields=['content_type', '-moderated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_content_type_display()} moderated by {self.moderated_by.username}"


class SubAdminPerformance(models.Model):
    """Track SubAdmin performance metrics"""
    
    subadmin = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='performance_metrics'
    )
    
    # Daily metrics
    reports_handled_today = models.IntegerField(default=0)
    kyc_verified_today = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0)  # in hours
    
    # Weekly metrics
    reports_handled_week = models.IntegerField(default=0)
    kyc_verified_week = models.IntegerField(default=0)
    false_positive_rate = models.FloatField(default=0)  # Percentage
    
    # Monthly metrics
    reports_handled_month = models.IntegerField(default=0)
    kyc_verified_month = models.IntegerField(default=0)
    user_satisfaction_score = models.FloatField(default=0)  # 0-5 scale
    
    # Overall metrics
    total_reports_handled = models.IntegerField(default=0)
    total_kyc_verified = models.IntegerField(default=0)
    total_warnings_issued = models.IntegerField(default=0)
    total_bans_issued = models.IntegerField(default=0)
    
    # Quality metrics
    accuracy_rate = models.FloatField(default=0)  # Percentage
    appeal_overturn_rate = models.FloatField(default=0)  # Percentage
    
    # Last updated
    last_calculated = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-total_reports_handled']
    
    def __str__(self):
        return f"Performance metrics for {self.subadmin.username}"
    
    def calculate_metrics(self):
        """Calculate and update performance metrics"""
        from django.db.models import Count, Avg
        from datetime import timedelta
        from apps.reports.models import Report, ModerationAction
        from apps.celebrities.models import CelebrityProfile
        
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Daily metrics
        self.reports_handled_today = Report.objects.filter(
            reviewed_by=self.subadmin,
            reviewed_at__date=today
        ).count()
        
        self.kyc_verified_today = CelebrityProfile.objects.filter(
            verified_by=self.subadmin,
            verification_date__date=today
        ).count()
        
        # Weekly metrics
        self.reports_handled_week = Report.objects.filter(
            reviewed_by=self.subadmin,
            reviewed_at__gte=week_ago
        ).count()
        
        self.kyc_verified_week = CelebrityProfile.objects.filter(
            verified_by=self.subadmin,
            verification_date__gte=week_ago
        ).count()
        
        # Monthly metrics
        self.reports_handled_month = Report.objects.filter(
            reviewed_by=self.subadmin,
            reviewed_at__gte=month_ago
        ).count()
        
        self.kyc_verified_month = CelebrityProfile.objects.filter(
            verified_by=self.subadmin,
            verification_date__gte=month_ago
        ).count()
        
        # Overall metrics
        self.total_reports_handled = Report.objects.filter(
            reviewed_by=self.subadmin
        ).count()
        
        self.total_kyc_verified = CelebrityProfile.objects.filter(
            verified_by=self.subadmin
        ).count()
        
        self.total_warnings_issued = ModerationAction.objects.filter(
            performed_by=self.subadmin,
            action_type='warning'
        ).count()
        
        self.total_bans_issued = ModerationAction.objects.filter(
            performed_by=self.subadmin,
            action_type__contains='ban'
        ).count()
        
        # Calculate average response time
        reports_with_time = Report.objects.filter(
            reviewed_by=self.subadmin,
            reviewed_at__isnull=False
        ).values('created_at', 'reviewed_at')
        
        if reports_with_time:
            total_time = sum(
                (r['reviewed_at'] - r['created_at']).total_seconds() / 3600
                for r in reports_with_time
            )
            self.avg_response_time = total_time / len(reports_with_time)
        
        self.last_calculated = now
        self.save()


class ContentModerationAlert(models.Model):
    """Alert for SubAdmins when harmful content is detected by AI"""

    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    ALERT_TYPE_CHOICES = (
        ('toxicity', 'Toxic Content'),
        ('spam', 'Spam'),
        ('hate_speech', 'Hate Speech'),
        ('violence', 'Violence'),
        ('self_harm', 'Self Harm'),
        ('explicit', 'Explicit Content'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('reviewing', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    )

    ACTION_CHOICES = (
        ('none', 'No Action'),
        ('warned', 'User Warned'),
        ('content_removed', 'Content Removed'),
        ('user_suspended', 'User Suspended'),
        ('user_banned', 'User Banned'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Content information
    content_type = models.CharField(max_length=50, help_text="Type of content (post, comment, etc.)")
    content_id = models.UUIDField(help_text="ID of the flagged content")
    content_text = models.TextField(help_text="Excerpt of the problematic content")
    content_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moderation_alerts_authored'
    )

    # Alert details
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    toxicity_score = models.FloatField(default=0.0, help_text="AI toxicity score (0-1)")
    toxic_words = models.JSONField(default=list, help_text="List of detected toxic words")

    # AI Analysis
    sentiment_score = models.FloatField(default=0.0)
    sentiment_label = models.CharField(max_length=20, default='neutral')
    spam_score = models.FloatField(default=0.0)

    # Moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_moderation_alerts',
        limit_choices_to={'user_type': 'subadmin'}
    )
    action_taken = models.CharField(max_length=30, choices=ACTION_CHOICES, default='none')
    moderator_notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # User history
    user_previous_violations = models.IntegerField(default=0)
    is_repeat_offender = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['content_author', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.content_author.username}"

    def assign_to_subadmin(self):
        """Auto-assign to appropriate SubAdmin based on user location"""
        try:
            from apps.subadmin.models import SubAdminProfile

            # Get author's country
            author_country = self.content_author.country

            if author_country:
                # Find SubAdmins responsible for this country
                subadmins = SubAdminProfile.objects.filter(
                    assigned_areas__contains=[author_country],
                    user__is_active=True
                ).select_related('user')

                if subadmins.exists():
                    # Assign to SubAdmin with least pending alerts
                    from django.db.models import Count, Q
                    subadmin = subadmins.annotate(
                        pending_count=Count('user__assigned_moderation_alerts',
                                          filter=Q(user__assigned_moderation_alerts__status='pending'))
                    ).order_by('pending_count').first()

                    self.assigned_to = subadmin.user
                    self.save(update_fields=['assigned_to'])
                    return True

            return False
        except Exception as e:
            print(f"Error assigning alert: {e}")
            return False

    def take_action(self, action, moderator, notes=''):
        """Take moderation action on the alert"""
        self.action_taken = action
        self.moderator_notes = notes
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()

        # Apply the action
        if action == 'warned':
            self._warn_user()
        elif action == 'content_removed':
            self._remove_content()
        elif action == 'user_suspended':
            self._suspend_user()
        elif action == 'user_banned':
            self._ban_user()

    def _warn_user(self):
        """Send warning to user"""
        # Implementation depends on notification system
        pass

    def _remove_content(self):
        """Remove the flagged content"""
        if self.content_type == 'post':
            from apps.posts.models import Post
            try:
                post = Post.objects.get(id=self.content_id)
                post.is_active = False
                post.save()
            except Post.DoesNotExist:
                pass

    def _suspend_user(self):
        """Suspend user temporarily"""
        self.content_author.is_active = False
        self.content_author.save()

    def _ban_user(self):
        """Permanently ban user"""
        self.content_author.is_banned = True
        self.content_author.is_active = False
        self.content_author.save()


# Note: KYCDocument model is defined in apps.celebrities.models to avoid duplication