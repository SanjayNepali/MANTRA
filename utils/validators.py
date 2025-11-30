# utils/validators.py

import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
import magic
from PIL import Image


# Phone number validator
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

# Username validator
username_regex = RegexValidator(
    regex=r'^[a-zA-Z0-9_]{3,30}$',
    message="Username must be 3-30 characters, containing only letters, numbers, and underscores."
)


def validate_age(date_of_birth):
    """Validate if user is at least 13 years old"""
    if not date_of_birth:
        return
        
    today = timezone.now().date()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    
    if age < 13:
        raise ValidationError("You must be at least 13 years old to use this platform.")
    
    if age > 120:
        raise ValidationError("Please enter a valid date of birth.")


def validate_image_size(image, max_size_mb=5):
    """Validate image file size"""
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Image file size cannot exceed {max_size_mb}MB.")


def validate_image_format(image):
    """Validate image file format"""
    allowed_formats = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    
    # Use python-magic to check actual file type
    file_mime = magic.from_buffer(image.read(1024), mime=True)
    image.seek(0)  # Reset file pointer
    
    if file_mime not in allowed_formats:
        raise ValidationError("Only JPEG, PNG, GIF, and WebP images are allowed.")


def validate_image_dimensions(image, max_width=4000, max_height=4000, min_width=100, min_height=100):
    """Validate image dimensions"""
    img = Image.open(image)
    width, height = img.size
    
    if width > max_width or height > max_height:
        raise ValidationError(f"Image dimensions cannot exceed {max_width}x{max_height} pixels.")
    
    if width < min_width or height < min_height:
        raise ValidationError(f"Image dimensions must be at least {min_width}x{min_height} pixels.")


def validate_video_size(video, max_size_mb=100):
    """Validate video file size"""
    if video.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Video file size cannot exceed {max_size_mb}MB.")


def validate_video_format(video):
    """Validate video file format"""
    allowed_formats = ['video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo']
    
    file_mime = magic.from_buffer(video.read(1024), mime=True)
    video.seek(0)
    
    if file_mime not in allowed_formats:
        raise ValidationError("Only MP4, MPEG, MOV, and AVI videos are allowed.")


def validate_future_date(date):
    """Validate that date is in the future"""
    if date <= timezone.now():
        raise ValidationError("Date must be in the future.")


def validate_event_date(date):
    """Validate event date (must be at least 24 hours in future)"""
    if date < timezone.now() + timedelta(hours=24):
        raise ValidationError("Event must be scheduled at least 24 hours in advance.")


def validate_price(price):
    """Validate price field"""
    if price < 0:
        raise ValidationError("Price cannot be negative.")
    
    if price > 1000000:
        raise ValidationError("Price cannot exceed 1,000,000.")


def validate_percentage(value):
    """Validate percentage values"""
    if value < 0 or value > 100:
        raise ValidationError("Percentage must be between 0 and 100.")


def validate_url_slug(slug):
    """Validate URL slug format"""
    if not re.match(r'^[a-z0-9-]+$', slug):
        raise ValidationError("Slug can only contain lowercase letters, numbers, and hyphens.")
    
    if slug.startswith('-') or slug.endswith('-'):
        raise ValidationError("Slug cannot start or end with a hyphen.")
    
    if '--' in slug:
        raise ValidationError("Slug cannot contain consecutive hyphens.")


def validate_hashtag(hashtag):
    """Validate hashtag format"""
    if not hashtag.startswith('#'):
        raise ValidationError("Hashtag must start with #.")
    
    if len(hashtag) < 2:
        raise ValidationError("Hashtag must contain at least one character after #.")
    
    if not re.match(r'^#[a-zA-Z0-9_]+$', hashtag):
        raise ValidationError("Hashtag can only contain letters, numbers, and underscores.")
    
    if len(hashtag) > 100:
        raise ValidationError("Hashtag cannot exceed 100 characters.")


def validate_bio(bio):
    """Validate user bio"""
    if len(bio) > 500:
        raise ValidationError("Bio cannot exceed 500 characters.")
    
    # Check for spam patterns
    spam_patterns = [
        r'(buy|sell|click|visit)\s+(now|here|this)',
        r'(http|https)://[^\s]+',  # URLs in bio
        r'(\$|€|£)\d+',  # Price mentions
        r'(whatsapp|telegram|viber).*\d{5,}',  # Contact numbers
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, bio, re.IGNORECASE):
            raise ValidationError("Bio contains prohibited content.")


def validate_kyc_document(document):
    """Validate KYC document upload"""
    validate_image_size(document, max_size_mb=10)
    validate_image_format(document)
    
    # Additional KYC-specific validation
    img = Image.open(document)
    width, height = img.size
    
    # Ensure minimum quality for document verification
    if width < 800 or height < 600:
        raise ValidationError("Document image must be at least 800x600 pixels for clear verification.")


def validate_payment_proof(image):
    """Validate payment proof/QR code image"""
    validate_image_size(image, max_size_mb=2)
    validate_image_format(image)
    
    # Check if image contains QR code (basic check)
    img = Image.open(image)
    width, height = img.size
    
    if width < 200 or height < 200:
        raise ValidationError("QR code image is too small. Minimum size is 200x200 pixels.")


def validate_merchandise_stock(stock):
    """Validate merchandise stock quantity"""
    if stock < 0:
        raise ValidationError("Stock quantity cannot be negative.")
    
    if stock > 99999:
        raise ValidationError("Stock quantity cannot exceed 99,999.")


def validate_subscription_duration(duration_days):
    """Validate subscription duration"""
    valid_durations = [30, 90, 180, 365]  # 1 month, 3 months, 6 months, 1 year
    
    if duration_days not in valid_durations:
        raise ValidationError("Invalid subscription duration.")


def validate_message_content(content):
    """Validate message content for chat"""
    if not content or not content.strip():
        raise ValidationError("Message cannot be empty.")
    
    if len(content) > 1000:
        raise ValidationError("Message cannot exceed 1000 characters.")
    
    # Check for spam/abuse patterns
    spam_patterns = [
        r'(.)\1{10,}',  # Repeated characters
        r'[A-Z\s]{20,}',  # All caps spam
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, content):
            raise ValidationError("Message contains spam-like content.")


def validate_rating(rating):
    """Validate rating value (1-5 stars)"""
    if rating < 1 or rating > 5:
        raise ValidationError("Rating must be between 1 and 5.")


def validate_bank_account(account_number):
    """Validate bank account number format"""
    if not re.match(r'^\d{10,18}$', account_number):
        raise ValidationError("Invalid bank account number format.")


def validate_esewa_id(esewa_id):
    """Validate eSewa ID format"""
    if not re.match(r'^9[0-9]{9}$', esewa_id):
        raise ValidationError("Invalid eSewa ID. Must be a 10-digit number starting with 9.")