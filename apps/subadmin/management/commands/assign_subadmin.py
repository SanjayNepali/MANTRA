# apps/subadmin/management/commands/assign_subadmin.py
"""
Management command to assign SubAdmin to regions
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import SubAdminProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Assign a user as SubAdmin for a specific region'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username of the user to make SubAdmin'
        )
        parser.add_argument(
            'region',
            type=str,
            help='Region to assign (e.g., Kathmandu, Delhi, Mumbai)'
        )
        parser.add_argument(
            '--areas',
            nargs='+',
            help='Additional areas to manage',
            default=[]
        )
        parser.add_argument(
            '--assigned-by',
            type=str,
            help='Username of admin assigning this SubAdmin',
            default=None
        )
    
    def handle(self, *args, **options):
        username = options['username']
        region = options['region']
        areas = options['areas']
        assigned_by_username = options['assigned_by']
        
        try:
            # Get or create user
            user = User.objects.get(username=username)
            
            # Update user type to subadmin
            if user.user_type != 'subadmin':
                user.user_type = 'subadmin'
                user.save()
                self.stdout.write(f'Updated {username} to SubAdmin user type')
            
            # Get admin who is assigning
            assigned_by = None
            if assigned_by_username:
                try:
                    assigned_by = User.objects.get(username=assigned_by_username)
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Admin user {assigned_by_username} not found'))
            
            # Create or update SubAdmin profile
            subadmin_profile, created = SubAdminProfile.objects.update_or_create(
                user=user,
                defaults={
                    'region': region,
                    'assigned_areas': areas or [region],
                    'assigned_by': assigned_by,
                    'responsibilities': f'Regional management for {region}'
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully created SubAdmin profile for {username} in {region}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully updated SubAdmin profile for {username} in {region}'
                ))
            
            # Display assigned areas
            self.stdout.write(f'Assigned areas: {", ".join(subadmin_profile.assigned_areas)}')
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))