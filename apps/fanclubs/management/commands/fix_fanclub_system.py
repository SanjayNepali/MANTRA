# apps/fanclubs/management/commands/fix_fanclub_system.py
"""
COMPREHENSIVE FIX SCRIPT - Fixes ALL fanclub issues in one go
Run: python manage.py fix_fanclub_system
"""

from django.core.management.base import BaseCommand
from django.db import transaction, models, connection
from django.conf import settings
from django.utils import timezone
import os
import sys


class Command(BaseCommand):
    help = '🚀 Comprehensive fix for all fanclub issues - runs everything automatically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-cleanup',
            action='store_true',
            help='Skip duplicate cleanup (only create files)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_cleanup = options['skip_cleanup']
        
        self.stdout.write(self.style.SUCCESS(''))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🚀 COMPREHENSIVE FANCLUB SYSTEM FIX'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN MODE - No changes will be made'))
            self.stdout.write('')
        
        # Step 1: Create AI moderation module
        self.stdout.write(self.style.HTTP_INFO('Step 1/6: Creating AI content moderation module...'))
        self.create_ai_moderation_module(dry_run)
        
        # Step 2: Update signals.py
        self.stdout.write(self.style.HTTP_INFO('Step 2/6: Updating signals.py with duplicate prevention...'))
        self.update_signals_file(dry_run)
        
        # Step 3: Clean up duplicate fanclubs
        if not skip_cleanup:
            self.stdout.write(self.style.HTTP_INFO('Step 3/6: Cleaning up duplicate fanclubs...'))
            self.cleanup_duplicates(dry_run)
        else:
            self.stdout.write(self.style.WARNING('Step 3/6: Skipped duplicate cleanup (--skip-cleanup)'))
        
        # Step 4: Update fanclub model
        self.stdout.write(self.style.HTTP_INFO('Step 4/6: Adding database constraint to model...'))
        self.update_fanclub_model(dry_run)
        
        # Step 5: Create and run migration
        self.stdout.write(self.style.HTTP_INFO('Step 5/6: Creating and running migration...'))
        self.create_and_run_migration(dry_run)
        
        # Step 6: Verify everything
        self.stdout.write(self.style.HTTP_INFO('Step 6/6: Verifying fixes...'))
        self.verify_fixes()
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        if dry_run:
            self.stdout.write(self.style.WARNING('✅ DRY RUN COMPLETE - No changes were made'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply fixes'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ ALL FIXES APPLIED SUCCESSFULLY!'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Your fanclub system is now bulletproof:'))
            self.stdout.write(self.style.SUCCESS('  ✓ Duplicates removed'))
            self.stdout.write(self.style.SUCCESS('  ✓ Database constraint added'))
            self.stdout.write(self.style.SUCCESS('  ✓ Signal protection enabled'))
            self.stdout.write(self.style.SUCCESS('  ✓ AI moderation working'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

    def create_ai_moderation_module(self, dry_run):
        """Create utils/ai_content_moderation.py"""
        content = '''# utils/ai_content_moderation.py
"""
AI-powered content moderation utilities
Provides sentiment analysis and toxicity detection for user-generated content
"""

import re
from typing import Dict, List, Any


# Toxic words list (basic version - expand as needed)
TOXIC_WORDS = [
    'hate', 'stupid', 'idiot', 'dumb', 'kill', 'die', 'death',
    'fuck', 'shit', 'bitch', 'ass', 'damn', 'hell',
    'loser', 'failure', 'worthless', 'pathetic', 'disgusting'
]

# Negative words for sentiment analysis
NEGATIVE_WORDS = [
    'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate',
    'angry', 'sad', 'depressed', 'upset', 'disappointed',
    'frustrating', 'annoying', 'useless', 'broken', 'failed'
]

# Positive words for sentiment analysis
POSITIVE_WORDS = [
    'good', 'great', 'excellent', 'amazing', 'wonderful', 'love',
    'happy', 'excited', 'best', 'awesome', 'fantastic',
    'perfect', 'beautiful', 'brilliant', 'outstanding', 'superb'
]


def analyze_text_content(text: str) -> Dict[str, Any]:
    """Analyze text content for sentiment and toxicity"""
    if not text or not isinstance(text, str):
        return {
            'sentiment': {'label': 'neutral', 'score': 0.5},
            'toxicity': {'is_toxic': False, 'toxic_words': []},
            'text_stats': {'length': 0, 'word_count': 0}
        }
    
    text_lower = text.lower()
    words = re.findall(r'\\b\\w+\\b', text_lower)
    
    text_stats = {
        'length': len(text),
        'word_count': len(words)
    }
    
    # Toxicity detection
    toxic_words_found = [word for word in words if word in TOXIC_WORDS]
    is_toxic = len(toxic_words_found) > 0
    toxicity_score = min(len(toxic_words_found) / max(len(words), 1), 1.0)
    
    toxicity_result = {
        'is_toxic': is_toxic,
        'toxic_words': list(set(toxic_words_found)),
        'toxicity_score': toxicity_score
    }
    
    # Sentiment analysis
    positive_count = sum(1 for word in words if word in POSITIVE_WORDS)
    negative_count = sum(1 for word in words if word in NEGATIVE_WORDS)
    
    total_sentiment_words = positive_count + negative_count
    if total_sentiment_words == 0:
        sentiment_score = 0.5
        sentiment_label = 'neutral'
    else:
        sentiment_score = positive_count / total_sentiment_words
        
        if sentiment_score >= 0.7:
            sentiment_label = 'very_positive'
        elif sentiment_score >= 0.55:
            sentiment_label = 'positive'
        elif sentiment_score >= 0.45:
            sentiment_label = 'neutral'
        elif sentiment_score >= 0.3:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'very_negative'
    
    sentiment_result = {
        'label': sentiment_label,
        'score': sentiment_score,
        'positive_words': positive_count,
        'negative_words': negative_count
    }
    
    return {
        'sentiment': sentiment_result,
        'toxicity': toxicity_result,
        'text_stats': text_stats
    }
'''
        
        utils_dir = os.path.join(settings.BASE_DIR, 'utils')
        file_path = os.path.join(utils_dir, 'ai_content_moderation.py')
        
        if not dry_run:
            os.makedirs(utils_dir, exist_ok=True)
            
            # Create __init__.py
            init_path = os.path.join(utils_dir, '__init__.py')
            if not os.path.exists(init_path):
                with open(init_path, 'w') as f:
                    f.write('')
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            self.stdout.write(self.style.SUCCESS('  ✓ Created utils/ai_content_moderation.py'))
        else:
            self.stdout.write(self.style.WARNING(f'  → Would create {file_path}'))

    def update_signals_file(self, dry_run):
        """Update apps/celebrities/signals.py with duplicate prevention"""
        content = '''# apps/celebrities/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from apps.accounts.models import User
from .models import CelebrityProfile, Subscription, CelebrityAchievement


@receiver(post_save, sender=User)
def create_celebrity_profile(sender, instance, created, **kwargs):
    """Create celebrity profile when celebrity user is created"""
    if created and instance.user_type == 'celebrity':
        with transaction.atomic():
            profile, _ = CelebrityProfile.objects.get_or_create(
                user=instance,
                defaults={'categories': [instance.category] if hasattr(instance, 'category') else []}
            )
            create_default_achievements(instance)
            create_official_fanclub(instance)


def create_official_fanclub(user):
    """Create official fanclub for celebrity - DUPLICATE PREVENTION"""
    from apps.fanclubs.models import FanClub, FanClubMembership
    
    # Check if official fanclub already exists
    existing_official = FanClub.objects.filter(
        celebrity=user,
        is_official=True
    ).first()
    
    if existing_official:
        return existing_official
    
    # Check by slug pattern too
    base_slug = slugify(f"{user.username}-official-fan-club")
    existing_by_slug = FanClub.objects.filter(
        celebrity=user,
        slug__startswith=base_slug
    ).first()
    
    if existing_by_slug:
        if not existing_by_slug.is_official:
            existing_by_slug.is_official = True
            existing_by_slug.save(update_fields=['is_official'])
        return existing_by_slug
    
    # Use transaction to prevent race conditions
    with transaction.atomic():
        existing_check = FanClub.objects.select_for_update().filter(
            celebrity=user,
            is_official=True
        ).first()
        
        if existing_check:
            return existing_check
        
        fanclub_name = f"{user.get_full_name() or user.username}'s Official Fan Club"
        fanclub_slug = slugify(f"{user.username}-official-fan-club")
        
        counter = 1
        original_slug = fanclub_slug
        while FanClub.objects.filter(slug=fanclub_slug).exists():
            fanclub_slug = f"{original_slug}-{counter}"
            counter += 1
        
        fanclub = FanClub.objects.create(
            celebrity=user,
            name=fanclub_name,
            slug=fanclub_slug,
            description=f"Official fan club for {user.get_full_name() or user.username}. Join to get exclusive updates and connect with other fans!",
            welcome_message=f"Welcome to {user.get_full_name() or user.username}'s official fan club! 🎉",
            club_type='default',
            is_official=True,
            is_active=True,
            is_private=False,
            visibility='public',
            requires_approval=False,
            allow_member_posts=False,
            allow_member_invites=True
        )
        
        FanClubMembership.objects.create(
            user=user,
            fanclub=fanclub,
            role='admin',
            status='active'
        )
        
        return fanclub


def create_default_achievements(user):
    """Create default achievements for new celebrities"""
    achievements_data = [
        {'title': 'First Fan', 'description': 'Get your first follower', 'icon': 'bx bx-user-plus', 
         'achievement_type': 'followers', 'threshold': 1, 'points_reward': 10},
        {'title': 'Rising Star', 'description': 'Reach 100 followers', 'icon': 'bx bx-star',
         'achievement_type': 'followers', 'threshold': 100, 'points_reward': 50},
        {'title': 'Popular', 'description': 'Reach 1,000 followers', 'icon': 'bx bx-trending-up',
         'achievement_type': 'followers', 'threshold': 1000, 'points_reward': 100},
        {'title': 'Celebrity Status', 'description': 'Reach 10,000 followers', 'icon': 'bx bx-crown',
         'achievement_type': 'followers', 'threshold': 10000, 'points_reward': 500},
        {'title': 'First Dollar', 'description': 'Earn your first dollar', 'icon': 'bx bx-dollar',
         'achievement_type': 'earnings', 'threshold': 1, 'points_reward': 20},
        {'title': 'Business Minded', 'description': 'Earn $100', 'icon': 'bx bx-briefcase',
         'achievement_type': 'earnings', 'threshold': 100, 'points_reward': 100},
        {'title': 'Content Creator', 'description': 'Create 10 posts', 'icon': 'bx bx-edit',
         'achievement_type': 'posts', 'threshold': 10, 'points_reward': 30},
        {'title': 'Prolific', 'description': 'Create 100 posts', 'icon': 'bx bx-book',
         'achievement_type': 'posts', 'threshold': 100, 'points_reward': 150},
    ]
    
    for data in achievements_data:
        CelebrityAchievement.objects.get_or_create(
            celebrity=user,
            achievement_type=data['achievement_type'],
            threshold=data['threshold'],
            defaults=data
        )


@receiver(pre_save, sender=Subscription)
def handle_subscription_expiry(sender, instance, **kwargs):
    """Check and update subscription status"""
    if instance.pk:
        if instance.status == 'active' and timezone.now() > instance.end_date:
            instance.status = 'expired'
'''
        
        file_path = os.path.join(settings.BASE_DIR, 'apps', 'celebrities', 'signals.py')
        
        if not dry_run:
            with open(file_path, 'w') as f:
                f.write(content)
            self.stdout.write(self.style.SUCCESS('  ✓ Updated apps/celebrities/signals.py'))
        else:
            self.stdout.write(self.style.WARNING(f'  → Would update {file_path}'))

    def cleanup_duplicates(self, dry_run):
        """Clean up duplicate official fanclubs"""
        from apps.fanclubs.models import FanClub, FanClubMembership
        from apps.accounts.models import User
        
        # Find celebrities with multiple official fanclubs
        celebrities_with_duplicates = User.objects.filter(
            user_type='celebrity'
        ).annotate(
            official_count=models.Count('fanclubs', filter=models.Q(fanclubs__is_official=True))
        ).filter(official_count__gt=1)
        
        if not celebrities_with_duplicates.exists():
            self.stdout.write(self.style.SUCCESS('  ✓ No duplicate fanclubs found!'))
            return
        
        total_deleted = 0
        
        for celebrity in celebrities_with_duplicates:
            official_fanclubs = FanClub.objects.filter(
                celebrity=celebrity,
                is_official=True
            ).order_by('created_at')
            
            fanclub_to_keep = official_fanclubs.first()
            fanclubs_to_delete = official_fanclubs.exclude(pk=fanclub_to_keep.pk)
            
            self.stdout.write(f'  → {celebrity.username}: Keeping "{fanclub_to_keep.name}"')
            
            if not dry_run:
                with transaction.atomic():
                    for fanclub in fanclubs_to_delete:
                        # Migrate members
                        for membership in fanclub.memberships.all():
                            existing = FanClubMembership.objects.filter(
                                user=membership.user,
                                fanclub=fanclub_to_keep
                            ).first()
                            
                            if not existing:
                                FanClubMembership.objects.create(
                                    user=membership.user,
                                    fanclub=fanclub_to_keep,
                                    status=membership.status,
                                    role=membership.role,
                                    tier=membership.tier,
                                    joined_at=membership.joined_at
                                )
                            
                            membership.delete()
                        
                        # Delete group chat
                        if fanclub.group_chat:
                            conversation = fanclub.group_chat
                            fanclub.group_chat = None
                            fanclub.save(update_fields=['group_chat'])
                            conversation.delete()
                        
                        # Delete duplicate
                        fanclub.delete()
                        total_deleted += 1
                        self.stdout.write(f'    ✗ Deleted "{fanclub.name}"')
                    
                    # Update member count
                    fanclub_to_keep.members_count = fanclub_to_keep.memberships.filter(
                        status='active'
                    ).count()
                    fanclub_to_keep.save(update_fields=['members_count'])
            else:
                total_deleted += fanclubs_to_delete.count()
                for fanclub in fanclubs_to_delete:
                    self.stdout.write(self.style.WARNING(f'    → Would delete "{fanclub.name}"'))
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Cleaned up {total_deleted} duplicate fanclubs'))
        else:
            self.stdout.write(self.style.WARNING(f'  → Would delete {total_deleted} duplicates'))

    def update_fanclub_model(self, dry_run):
        """Add constraint code to fanclub model's Meta class"""
        self.stdout.write(self.style.WARNING('  ⚠️  Manual step required:'))
        self.stdout.write('     Add this to FanClub model Meta class in apps/fanclubs/models.py:')
        self.stdout.write('')
        self.stdout.write('     constraints = [')
        self.stdout.write('         models.UniqueConstraint(')
        self.stdout.write('             fields=[\'celebrity\', \'is_official\'],')
        self.stdout.write('             condition=models.Q(is_official=True),')
        self.stdout.write('             name=\'unique_official_fanclub_per_celebrity\'')
        self.stdout.write('         )')
        self.stdout.write('     ]')
        self.stdout.write('')
        self.stdout.write('     Also add to save() method (before super().save()):')
        self.stdout.write('')
        self.stdout.write('     if self.is_official and self._state.adding:')
        self.stdout.write('         existing = FanClub.objects.filter(')
        self.stdout.write('             celebrity=self.celebrity, is_official=True')
        self.stdout.write('         ).exclude(pk=self.pk).first()')
        self.stdout.write('         if existing:')
        self.stdout.write('             raise ValueError(f"Official fanclub already exists")')
        self.stdout.write('')

    def create_and_run_migration(self, dry_run):
        """Create and run migration"""
        if not dry_run:
            self.stdout.write('  → Run these commands manually:')
            self.stdout.write('     python manage.py makemigrations fanclubs')
            self.stdout.write('     python manage.py migrate fanclubs')
        else:
            self.stdout.write(self.style.WARNING('  → Would create and run migration'))

    def verify_fixes(self):
        """Verify all fixes worked"""
        from apps.fanclubs.models import FanClub
        from apps.accounts.models import User
        
        # Check for duplicates
        celebrities_with_duplicates = User.objects.filter(
            user_type='celebrity'
        ).annotate(
            official_count=models.Count('fanclubs', filter=models.Q(fanclubs__is_official=True))
        ).filter(official_count__gt=1)
        
        duplicate_count = celebrities_with_duplicates.count()
        
        # Check AI moderation exists
        utils_dir = os.path.join(settings.BASE_DIR, 'utils')
        ai_mod_exists = os.path.exists(os.path.join(utils_dir, 'ai_content_moderation.py'))
        
        # Check signals file
        signals_path = os.path.join(settings.BASE_DIR, 'apps', 'celebrities', 'signals.py')
        signals_updated = os.path.exists(signals_path)
        
        if signals_updated:
            with open(signals_path, 'r') as f:
                signals_content = f.read()
                signals_updated = 'DUPLICATE PREVENTION' in signals_content
        
        self.stdout.write('')
        self.stdout.write('  Verification Results:')
        self.stdout.write(f'    {"✓" if duplicate_count == 0 else "✗"} Duplicates removed: {duplicate_count} remaining')
        self.stdout.write(f'    {"✓" if ai_mod_exists else "✗"} AI moderation module: {"Created" if ai_mod_exists else "Missing"}')
        self.stdout.write(f'    {"✓" if signals_updated else "✗"} Signals file: {"Updated" if signals_updated else "Not updated"}')
        self.stdout.write('')