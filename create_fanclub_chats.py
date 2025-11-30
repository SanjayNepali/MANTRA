"""
Script to create group chat conversations for existing fan clubs
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.fanclubs.models import FanClub, FanClubMembership
from apps.messaging.models import Conversation

def create_fanclub_chats():
    """Create group chats for all existing fan clubs"""
    print("Creating group chats for existing fan clubs...")

    fanclubs_without_chat = FanClub.objects.filter(group_chat__isnull=True)
    count = 0

    for fanclub in fanclubs_without_chat:
        # Create group conversation
        conversation = Conversation.objects.create(
            title=fanclub.name,
            is_group=True,
            group_admin=fanclub.celebrity,
            group_image=fanclub.icon
        )

        # Add celebrity as first participant
        conversation.participants.add(fanclub.celebrity)

        # Add all active members to the conversation
        active_memberships = FanClubMembership.objects.filter(
            fanclub=fanclub,
            status='active'
        ).select_related('user')

        for membership in active_memberships:
            conversation.participants.add(membership.user)

        # Link the conversation to the fan club
        fanclub.group_chat = conversation
        fanclub.save(update_fields=['group_chat'])

        count += 1
        print(f"  Created group chat for: {fanclub.name} ({active_memberships.count()} members)")

    print(f"\nDone! Created {count} group chats")

if __name__ == '__main__':
    create_fanclub_chats()
