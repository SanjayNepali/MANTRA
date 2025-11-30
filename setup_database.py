#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Setup Script for MANTRA
Creates initial data including superuser, categories, and sample data
"""

import os
import sys
import django

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.celebrities.models import CelebrityCategory
from apps.merchandise.models import MerchandiseCategory
from django.conf import settings

User = get_user_model()

def create_superuser():
    """Create superuser if it doesn't exist"""
    print("Creating superuser...")

    if User.objects.filter(username='admin').exists():
        print("  ✓ Superuser 'admin' already exists")
        return

    admin = User.objects.create_superuser(
        username='admin',
        email='admin@mantra.com',
        password='admin123',
        user_type='admin',
        first_name='Admin',
        last_name='User'
    )
    print(f"  ✓ Superuser created: admin / admin123")

def create_celebrity_categories():
    """Create celebrity categories"""
    print("\nCreating celebrity categories...")

    categories = [
        ('actor', 'Actor', 'bx-movie'),
        ('singer', 'Singer', 'bx-music'),
        ('rapper', 'Rapper', 'bx-microphone'),
        ('comedian', 'Comedian', 'bx-laugh'),
        ('athlete', 'Athlete', 'bx-football'),
        ('influencer', 'Influencer', 'bx-camera'),
        ('model', 'Model', 'bx-user'),
        ('musician', 'Musician', 'bx-guitar-amp'),
        ('dancer', 'Dancer', 'bx-body'),
        ('writer', 'Writer', 'bx-book'),
    ]

    for slug, name, icon in categories:
        category, created = CelebrityCategory.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'icon': icon,
                'is_active': True
            }
        )
        if created:
            print(f"  ✓ Created category: {name}")
        else:
            print(f"  - Category exists: {name}")

def create_merchandise_categories():
    """Create merchandise categories"""
    print("\nCreating merchandise categories...")

    categories = [
        ('clothing', 'Clothing', 'T-shirts, hoodies, jackets', 'bx-closet'),
        ('accessories', 'Accessories', 'Hats, bags, jewelry', 'bx-shopping-bag'),
        ('collectibles', 'Collectibles', 'Limited edition items', 'bx-collection'),
        ('posters', 'Posters', 'Posters and prints', 'bx-image'),
        ('music', 'Music', 'CDs, vinyl, digital downloads', 'bx-music'),
        ('books', 'Books', 'Books and magazines', 'bx-book'),
        ('electronics', 'Electronics', 'Tech gadgets', 'bx-laptop'),
        ('other', 'Other', 'Other merchandise', 'bx-package'),
    ]

    for slug, name, description, icon in categories:
        category, created = MerchandiseCategory.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'description': description,
                'icon': icon
            }
        )
        if created:
            print(f"  ✓ Created category: {name}")
        else:
            print(f"  - Category exists: {name}")

def create_sample_users():
    """Create sample users for testing"""
    print("\nCreating sample users...")

    # Sample Fan
    if not User.objects.filter(username='fan_user').exists():
        fan = User.objects.create_user(
            username='fan_user',
            email='fan@example.com',
            password='password123',
            user_type='fan',
            first_name='Test',
            last_name='Fan'
        )
        print(f"  ✓ Created fan user: fan_user / password123")
    else:
        print(f"  - Fan user exists: fan_user")

    # Sample Celebrity
    if not User.objects.filter(username='celebrity_user').exists():
        celebrity = User.objects.create_user(
            username='celebrity_user',
            email='celebrity@example.com',
            password='password123',
            user_type='celebrity',
            first_name='Test',
            last_name='Celebrity',
            is_verified=True
        )

        # Create celebrity profile
        from apps.celebrities.models import CelebrityProfile
        CelebrityProfile.objects.get_or_create(
            user=celebrity,
            defaults={
                'category': 'singer',
                'bio_extended': 'Sample celebrity for testing',
                'verification_status': 'approved'
            }
        )
        print(f"  ✓ Created celebrity user: celebrity_user / password123")
    else:
        print(f"  - Celebrity user exists: celebrity_user")

def main():
    """Main setup function"""
    print("=" * 60)
    print("MANTRA Database Setup")
    print("=" * 60)

    try:
        create_superuser()
        create_celebrity_categories()
        create_merchandise_categories()
        create_sample_users()

        print("\n" + "=" * 60)
        print("✓ Database setup completed successfully!")
        print("=" * 60)
        print("\nYou can now:")
        print("  1. Run the server: python manage.py runserver")
        print("  2. Login to admin: http://localhost:8000/admin")
        print("     - Username: admin")
        print("     - Password: admin123")
        print("\n  3. Test accounts:")
        print("     - Fan: fan_user / password123")
        print("     - Celebrity: celebrity_user / password123")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
