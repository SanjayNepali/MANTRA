"""
MANTRA Sample Data Generator
Creates comprehensive test data for the entire platform including:
- Users (celebrities, fans, admins)
- Posts (all types)
- Events
- Merchandise
- Subscriptions
- Orders
- Comments, likes, follows
- Messages
- Notifications
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.models import UserFollowing, UserPreferences
from apps.celebrities.models import CelebrityProfile, Subscription, CelebrityEarning
from apps.fans.models import FanProfile
from apps.posts.models import Post, Like, Comment, Share
from apps.events.models import Event, EventBooking
from apps.merchandise.models import Merchandise, MerchandiseCategory, MerchandiseOrder, OrderItem
from apps.fanclubs.models import FanClub, FanClubMembership
from apps.notifications.models import Notification
from django.db.models import Sum

User = get_user_model()

# Sample data lists
FIRST_NAMES = ['Emma', 'Liam', 'Olivia', 'Noah', 'Ava', 'Ethan', 'Sophia', 'Mason', 'Isabella', 'William',
               'Mia', 'James', 'Charlotte', 'Benjamin', 'Amelia', 'Lucas', 'Harper', 'Henry', 'Evelyn', 'Alexander',
               'Priya', 'Raj', 'Ananya', 'Arjun', 'Diya', 'Rohan', 'Aisha', 'Karan', 'Shreya', 'Vikram']

LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
              'Sharma', 'Patel', 'Kumar', 'Singh', 'Gupta', 'Khan', 'Reddy', 'Chopra', 'Verma', 'Mehta']

CELEBRITY_CATEGORIES = ['actor', 'musician', 'athlete', 'influencer', 'artist', 'writer', 'comedian', 'chef']

POST_TYPES = ['regular', 'announcement', 'celebration', 'question']

POST_CONTENTS = [
    "Just finished an amazing photoshoot! Can't wait to share the results with you all! 📸[*]",
    "Thank you so much for all the love and support! You guys are the best! 💖",
    "New project coming soon... Stay tuned! 🎬🎭",
    "Had an incredible workout session today. Feeling energized! 💪",
    "Spending quality time with family today. These moments are precious! 👨‍👩‍👧‍👦",
    "Just tried the most amazing food! Foodies, you need to check this out! 🍕🍝",
    "Behind the scenes from today's shoot. The team did an amazing job! 🎥",
    "Grateful for another beautiful day. Life is good! 🌅",
    "Working on something special for you all. Can't reveal much yet! 🤫",
    "Remember to take care of yourself. Mental health matters! 🧘‍♀️",
    "Throwback to some amazing memories! Time flies! 📷",
    "New music dropping soon! Who's excited? 🎵🎶",
    "Just landed in a new city! Adventure time! ✈️🌍",
    "Coffee and good vibes to start the day! ☕",
    "Thank you for 1 million followers! This is unbelievable! 🎉",
]

EVENT_NAMES = [
    "Meet & Greet Session",
    "Live Concert Experience",
    "Fan Appreciation Night",
    "Q&A and Photo Opportunity",
    "Exclusive Dinner Event",
    "Virtual Fan Meetup",
    "Album Launch Party",
    "Charity Fundraiser Gala",
    "Movie Premiere Screening",
    "Fitness Workshop",
    "Cooking Masterclass",
    "Art Exhibition Opening",
]

MERCHANDISE_NAMES = [
    "Autographed Poster",
    "Limited Edition T-Shirt",
    "Photo Album Collection",
    "Signed Cap",
    "Exclusive Hoodie",
    "Coffee Mug Set",
    "Phone Case",
    "Tote Bag",
    "Notebook & Pen Set",
    "Wristband Pack",
    "Keychain Collection",
    "Water Bottle",
]

MERCHANDISE_DESCRIPTIONS = [
    "Official merchandise from the latest collection. Limited quantities available!",
    "Premium quality with exclusive design. A must-have for true fans!",
    "Handpicked by the artist. Get yours before they're gone!",
    "Celebrate your fandom with this exclusive item!",
    "Made with high-quality materials. Perfect gift for any fan!",
]


class SampleDataGenerator:
    def __init__(self):
        self.celebrities = []
        self.fans = []
        self.posts = []
        self.events = []
        self.merchandise_items = []
        self.fanclubs = []

        print("🚀 Starting MANTRA Sample Data Generation...")
        print("=" * 60)

    def create_users(self):
        """Create sample users (celebrities and fans)"""
        print("\n👥 Creating Users...")

        # Create celebrities
        for i in range(15):
            username = f"celeb_{FIRST_NAMES[i].lower()}_{i}"
            email = f"{username}@example.com"

            # Check if user exists
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                print(f"  OK Celebrity exists: {username}")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='password123',
                    first_name=FIRST_NAMES[i],
                    last_name=LAST_NAMES[i % len(LAST_NAMES)],
                    user_type='celebrity',
                    is_verified=True,
                    bio=f"Professional {CELEBRITY_CATEGORIES[i % len(CELEBRITY_CATEGORIES)]} | Verified Account",
                    points=random.randint(1000, 10000)
                )

                # Create celebrity profile
                category = CELEBRITY_CATEGORIES[i % len(CELEBRITY_CATEGORIES)]
                CelebrityProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'category': category,
                        'subscription_fee': Decimal(random.choice([9.99, 14.99, 19.99, 24.99])),
                        'total_posts': 0,
                        'total_earnings': Decimal('0.00')
                    }
                )

                print(f"  OK Created celebrity: {username} ({category})")

            self.celebrities.append(user)

        # Create fans
        for i in range(30):
            username = f"fan_{FIRST_NAMES[i % len(FIRST_NAMES)].lower()}_{i}"
            email = f"{username}@example.com"

            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                print(f"  OK Fan exists: {username}")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='password123',
                    first_name=FIRST_NAMES[i % len(FIRST_NAMES)],
                    last_name=LAST_NAMES[i % len(LAST_NAMES)],
                    user_type='fan',
                    bio=f"Fan of great content!",
                    points=random.randint(100, 1000)
                )

                # Create fan profile
                FanProfile.objects.get_or_create(user=user)

                print(f"  OK Created fan: {username}")

            self.fans.append(user)

        print(f"\n[Done] Created {len(self.celebrities)} celebrities and {len(self.fans)} fans")

    def create_follows(self):
        """Create follower relationships"""
        print("\n🔗 Creating Follower Relationships...")

        created = 0
        for fan in self.fans:
            # Each fan follows 3-8 random celebrities
            num_follows = random.randint(3, min(8, len(self.celebrities)))
            celebs_to_follow = random.sample(self.celebrities, num_follows)

            for celeb in celebs_to_follow:
                UserFollowing.objects.get_or_create(
                    follower=fan,
                    following=celeb
                )
                created += 1

        # Celebrities follow each other
        for celeb in self.celebrities:
            num_follows = random.randint(2, 5)
            other_celebs = [c for c in self.celebrities if c != celeb]
            celebs_to_follow = random.sample(other_celebs, min(num_follows, len(other_celebs)))

            for other_celeb in celebs_to_follow:
                UserFollowing.objects.get_or_create(
                    follower=celeb,
                    following=other_celeb
                )
                created += 1

        print(f"[Done] Created {created} follow relationships")

    def create_posts(self):
        """Create sample posts"""
        print("\n📝 Creating Posts...")

        for celeb in self.celebrities:
            # Each celebrity creates 5-15 posts
            num_posts = random.randint(5, 15)

            for i in range(num_posts):
                post_type = random.choice(POST_TYPES)
                content = random.choice(POST_CONTENTS)

                # Random date within last 60 days
                days_ago = random.randint(0, 60)
                created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))

                post = Post.objects.create(
                    author=celeb,
                    content=content,
                    post_type=post_type,
                    is_exclusive=random.choice([True, False]) if random.random() > 0.7 else False,
                    likes_count=0,
                    comments_count=0,
                    shares_count=0,
                    views_count=random.randint(50, 5000),
                    created_at=created_at,
                    sentiment_score=random.uniform(-1, 1),
                    sentiment_label=random.choice(['positive', 'neutral', 'negative']),
                    tags=['celebrity', 'update', post_type]
                )

                self.posts.append(post)

            # Update celebrity profile post count
            celeb.celebrity_profile.total_posts = num_posts
            celeb.celebrity_profile.save()

            print(f"  OK Created {num_posts} posts for {celeb.username}")

        print(f"\n[Done] Created {len(self.posts)} total posts")

    def create_engagement(self):
        """Create likes, comments, and shares"""
        print("\n💬 Creating Post Engagement...")

        likes_created = 0
        comments_created = 0
        shares_created = 0

        for post in self.posts:
            # Random number of likes (20-80% of fans)
            num_likes = random.randint(int(len(self.fans) * 0.2), int(len(self.fans) * 0.8))
            fans_who_like = random.sample(self.fans, num_likes)

            for fan in fans_who_like:
                Like.objects.get_or_create(
                    user=fan,
                    post=post
                )
                likes_created += 1

            # Update like count
            post.likes_count = num_likes

            # Random number of comments (5-15% of fans)
            num_comments = random.randint(int(len(self.fans) * 0.05), int(len(self.fans) * 0.15))
            fans_who_comment = random.sample(self.fans, min(num_comments, len(self.fans)))

            comment_texts = [
                "Amazing! 🔥", "Love this! 💖", "Great post!", "Can't wait! 🎉",
                "This is so cool!", "Thank you for sharing!", "Inspiring! [*]",
                "Wow! 😍", "Keep up the great work!", "This made my day!",
                "Absolutely love it!", "So talented! 👏", "Beautiful! 💕"
            ]

            for fan in fans_who_comment:
                Comment.objects.create(
                    post=post,
                    author=fan,
                    content=random.choice(comment_texts)
                )
                comments_created += 1

            # Update comment count
            post.comments_count = num_comments

            # Random shares (2-10% of fans)
            num_shares = random.randint(int(len(self.fans) * 0.02), int(len(self.fans) * 0.10))
            fans_who_share = random.sample(self.fans, min(num_shares, len(self.fans)))

            for fan in fans_who_share:
                Share.objects.get_or_create(
                    user=fan,
                    post=post,
                    defaults={'text': 'Check this out!'}
                )
                shares_created += 1

            # Update share count
            post.shares_count = num_shares
            post.save()

        print(f"[Done] Created {likes_created} likes, {comments_created} comments, {shares_created} shares")

    def create_subscriptions(self):
        """Create celebrity subscriptions"""
        print("\n💳 Creating Subscriptions...")

        created = 0
        for fan in self.fans[:20]:  # 20 fans have subscriptions
            # Subscribe to 1-3 celebrities
            num_subs = random.randint(1, 3)
            celebs = random.sample(self.celebrities, num_subs)

            for celeb in celebs:
                start_date = timezone.now() - timedelta(days=random.randint(1, 60))

                Subscription.objects.get_or_create(
                    subscriber=fan,
                    celebrity=celeb.celebrity_profile,
                    defaults={
                        'start_date': start_date,
                        'end_date': start_date + timedelta(days=30),
                        'amount_paid': celeb.celebrity_profile.subscription_fee,
                        'payment_method': random.choice(['credit_card', 'paypal', 'upi']),
                        'status': 'active'
                    }
                )

                # Add earnings to celebrity
                CelebrityEarning.objects.create(
                    celebrity=celeb.celebrity_profile,
                    amount=celeb.celebrity_profile.subscription_fee,
                    source_type='subscription',
                    description=f"Subscription from {fan.username}"
                )

                created += 1

        print(f"[Done] Created {created} subscriptions")

    def create_merchandise_categories(self):
        """Create merchandise categories"""
        print("\n🏷️ Creating Merchandise Categories...")

        categories = [
            ('apparel', 'Apparel'),
            ('accessories', 'Accessories'),
            ('collectibles', 'Collectibles'),
            ('home', 'Home & Living'),
            ('tech', 'Tech Accessories'),
        ]

        for slug, name in categories:
            MerchandiseCategory.objects.get_or_create(
                slug=slug,
                defaults={'name': name}
            )

        print(f"[Done] Created {len(categories)} merchandise categories")

    def create_merchandise(self):
        """Create merchandise items"""
        print("\n🛍️ Creating Merchandise...")

        categories = list(MerchandiseCategory.objects.all())

        for celeb in self.celebrities:
            # Each celebrity has 3-7 merchandise items
            num_items = random.randint(3, 7)

            for i in range(num_items):
                item_base = random.choice(MERCHANDISE_NAMES)
                name = f"{celeb.first_name}'s {item_base}"

                # Make unique slug by adding celebrity username, index, and timestamp
                from django.utils.text import slugify
                import time
                slug = slugify(f"{name}-{celeb.username}-{i}-{int(time.time() * 1000)}")

                merch = Merchandise.objects.create(
                    celebrity=celeb,
                    name=name,
                    slug=slug,
                    description=random.choice(MERCHANDISE_DESCRIPTIONS),
                    category=random.choice(categories),
                    price=Decimal(random.choice([9.99, 14.99, 19.99, 24.99, 29.99, 39.99, 49.99])),
                    discount_percentage=random.choice([0, 5, 10, 15, 20]) if random.random() > 0.5 else 0,
                    subscriber_discount=random.choice([0, 5, 10, 15]),
                    stock_quantity=random.randint(10, 100),
                    total_sold=0,
                    status='available',
                    is_featured=random.random() > 0.7
                )

                self.merchandise_items.append(merch)

            print(f"  OK Created {num_items} merchandise items for {celeb.username}")

        print(f"\n[Done] Created {len(self.merchandise_items)} total merchandise items")

    def create_orders(self):
        """Create merchandise orders"""
        print("\n📦 Creating Orders...")

        order_statuses = ['pending', 'processing', 'shipped', 'delivered']

        created = 0
        for fan in self.fans[:25]:  # 25 fans made purchases
            # Each fan makes 1-3 orders
            num_orders = random.randint(1, 3)

            for _ in range(num_orders):
                # Select 1-4 random items
                num_items = random.randint(1, 4)
                items = random.sample(self.merchandise_items, num_items)

                # Calculate total
                total = sum(item.price for item in items)

                # Create order
                order_date = timezone.now() - timedelta(days=random.randint(1, 45))

                order = MerchandiseOrder.objects.create(
                    user=fan,
                    total_amount=total,
                    order_status=random.choice(order_statuses),
                    payment_status=random.choice(['pending', 'completed', 'failed']),
                    payment_method=random.choice(['credit_card', 'paypal', 'upi']),
                    shipping_address=f"{random.randint(1, 999)} Main St",
                    shipping_city="Sample City",
                    shipping_country="Sample Country",
                    shipping_postal_code=f"{random.randint(10000, 99999)}",
                    contact_number=f"+1{random.randint(1000000000, 9999999999)}",
                    created_at=order_date
                )

                # Create order items
                for item in items:
                    quantity = random.randint(1, 3)
                    OrderItem.objects.create(
                        order=order,
                        merchandise=item,
                        quantity=quantity,
                        price=item.price
                    )

                    # Update merchandise stats
                    item.total_sold += quantity
                    item.stock_quantity = max(0, item.stock_quantity - quantity)
                    item.save()

                created += 1

        print(f"[Done] Created {created} orders")

    def create_events(self):
        """Create events"""
        print("\n🎭 Creating Events...")

        for celeb in self.celebrities:
            # Each celebrity has 2-5 events
            num_events = random.randint(2, 5)

            for i in range(num_events):
                # Random future date (0-90 days)
                days_ahead = random.randint(0, 90)
                start_date = timezone.now() + timedelta(days=days_ahead, hours=random.randint(10, 20))

                event_name = random.choice(EVENT_NAMES)
                title = f"{celeb.first_name}'s {event_name}"

                # Create unique slug
                from django.utils.text import slugify
                import time
                slug = slugify(f"{title}-{celeb.username}-{int(time.time() * 1000)}")

                event = Event.objects.create(
                    celebrity=celeb,
                    title=title,
                    slug=slug,
                    description=f"Join {celeb.get_full_name()} for an exclusive event! Limited spots available.",
                    event_type=random.choice(['meet_greet', 'concert', 'workshop', 'virtual', 'other']),
                    event_date=start_date,
                    start_datetime=start_date,
                    end_datetime=start_date + timedelta(hours=random.randint(2, 4)),
                    venue_name=f"The Grand {random.choice(['Hall', 'Arena', 'Theater', 'Studio'])}",
                    address=f"{random.randint(100, 999)} Event Blvd",
                    city="Sample City",
                    country="Sample Country",
                    total_capacity=random.randint(50, 500),
                    available_tickets=0,
                    ticket_price=Decimal(random.choice([0, 19.99, 29.99, 49.99, 99.99])),
                    status='published' if days_ahead > 0 else 'completed',
                    is_featured=random.random() > 0.7
                )

                # Create registrations for past/current events
                if days_ahead <= 30:
                    num_registrations = random.randint(5, min(30, event.total_capacity))
                    fans_registered = random.sample(self.fans, num_registrations)

                    for idx, fan in enumerate(fans_registered):
                        import time
                        booking_code = f"BK-{int(time.time() * 1000)}-{fan.id}-{idx}"
                        EventBooking.objects.create(
                            event=event,
                            user=fan,
                            status=random.choice(['confirmed', 'attended']) if days_ahead <= 0 else 'confirmed',
                            total_amount=event.ticket_price,
                            booking_code=booking_code
                        )
                        time.sleep(0.001)  # Small delay to ensure unique timestamps

                    event.tickets_sold = num_registrations
                    event.available_tickets = max(0, event.total_capacity - num_registrations)
                    event.save()

                self.events.append(event)

            print(f"  OK Created {num_events} events for {celeb.username}")

        print(f"\n[Done] Created {len(self.events)} total events")

    def create_fanclubs(self):
        """Create fan clubs"""
        print("\n🎪 Creating Fan Clubs...")

        for celeb in self.celebrities[:10]:  # 10 celebrities have fan clubs
            from django.utils.text import slugify
            import time
            slug = slugify(f"{celeb.first_name}-official-fan-club-{int(time.time() * 1000)}")

            fanclub = FanClub.objects.create(
                celebrity=celeb,
                name=f"{celeb.first_name} Official Fan Club",
                slug=slug,
                description=f"The official fan club for {celeb.get_full_name()}. Join to connect with other fans!",
                membership_fee=Decimal(random.choice([0, 4.99, 9.99, 14.99])),
                is_paid=random.choice([True, False])
            )

            # Add members
            num_members = random.randint(10, 25)
            members = random.sample(self.fans, min(num_members, len(self.fans)))

            for fan in members:
                FanClubMembership.objects.create(
                    fanclub=fanclub,
                    user=fan,
                    status='active',
                    role=random.choice(['member', 'member', 'member', 'moderator'])  # More members than mods
                )

            self.fanclubs.append(fanclub)
            print(f"  OK Created fan club for {celeb.username} with {num_members} members")

        print(f"\n[Done] Created {len(self.fanclubs)} fan clubs")

    def create_notifications(self):
        """Create sample notifications"""
        print("\n🔔 Creating Notifications...")

        notification_types = ['like', 'comment', 'follow', 'subscription', 'event', 'system']
        messages_list = [
            'liked your post',
            'commented on your post',
            'started following you',
            'subscribed to your content',
            'registered for your event',
            'mentioned you in a post',
        ]

        created = 0
        for user in self.celebrities + self.fans[:10]:
            num_notifications = random.randint(5, 15)

            for _ in range(num_notifications):
                sender = random.choice(self.fans + self.celebrities)
                if sender == user:
                    continue

                Notification.objects.create(
                    recipient=user,
                    sender=sender,
                    notification_type=random.choice(notification_types),
                    message=f"{sender.username} {random.choice(messages_list)}",
                    is_read=random.random() > 0.5
                )
                created += 1

        print(f"[Done] Created {created} notifications")

    def update_statistics(self):
        """Update user statistics"""
        print("\n📊 Updating Statistics...")

        for user in self.celebrities + self.fans:
            # Update follower/following counts
            user.total_followers = user.followers.count()
            user.total_following = user.following.count()
            user.save()

        # Update celebrity earnings
        for celeb in self.celebrities:
            total_earnings = CelebrityEarning.objects.filter(
                celebrity=celeb.celebrity_profile
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            celeb.celebrity_profile.total_earnings = total_earnings
            celeb.celebrity_profile.save()

        print("[Done] Statistics updated")

    def run(self):
        """Run all data generation"""
        try:
            self.create_users()
            self.create_follows()
            self.create_posts()
            self.create_engagement()
            self.create_subscriptions()
            self.create_merchandise_categories()
            self.create_merchandise()
            self.create_orders()
            self.create_events()
            self.create_fanclubs()
            self.create_notifications()
            self.update_statistics()

            print("\n" + "=" * 60)
            print("🎉 SAMPLE DATA GENERATION COMPLETE!")
            print("=" * 60)
            print("\n📋 Summary:")
            print(f"  - Users: {len(self.celebrities)} celebrities, {len(self.fans)} fans")
            print(f"  - Posts: {len(self.posts)}")
            print(f"  - Events: {len(self.events)}")
            print(f"  - Merchandise: {len(self.merchandise_items)}")
            print(f"  - Fan Clubs: {len(self.fanclubs)}")
            print("\n🔐 Test Credentials:")
            print("  Celebrity: celeb_emma_0 / password123")
            print("  Fan: fan_emma_0 / password123")
            print("\n[*] You can now test the entire system!")

        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    generator = SampleDataGenerator()
    generator.run()
