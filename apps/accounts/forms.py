# apps/accounts/forms.py

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import User, UserPreferences
import re

# Countries list for forms
COUNTRIES = [
    ('', 'Select your country'),
    ('nepal', 'Nepal'),
    ('india', 'India'),
    ('usa', 'United States'),
    ('uk', 'United Kingdom'),
    ('canada', 'Canada'),
    ('australia', 'Australia'),
    ('germany', 'Germany'),
    ('france', 'France'),
    ('japan', 'Japan'),
    ('south_korea', 'South Korea'),
    ('china', 'China'),
    ('uae', 'United Arab Emirates'),
    ('saudi_arabia', 'Saudi Arabia'),
    ('other', 'Other')
]

class FanRegistrationForm(UserCreationForm):
    """Registration form for fans with country selection"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

    country = forms.ChoiceField(
        choices=COUNTRIES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        help_text='Select your country for regional content and support'
    )

    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your city (optional)'
        }),
        help_text='Optional: Enter your city for localized content'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',
                 'first_name', 'last_name', 'phone', 'country', 'city', 'bio', 'profile_picture')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number (optional)'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us about yourself...',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make country required
        self.fields['country'].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'fan'
        user.email = self.cleaned_data['email']
        user.country = self.cleaned_data['country']
        user.city = self.cleaned_data.get('city', '')

        if commit:
            user.save()
            # Create user preferences if not exists
            UserPreferences.objects.get_or_create(user=user)
            # Award initial points
            user.add_points(10, "Welcome bonus")

        return user

    def clean_country(self):
        """Validate country field"""
        country = self.cleaned_data.get('country')
        if not country:
            raise ValidationError('Country is required.')
        return country


class CelebrityRegistrationForm(UserCreationForm):
    """Registration form for celebrities with country and category selection"""

    from django.conf import settings

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

    country = forms.ChoiceField(
        choices=COUNTRIES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        help_text='Select your country for regional SubAdmin assignment'
    )

    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your city (optional)'
        }),
        help_text='Optional: Enter your city for more specific regional assignment'
    )

    category = forms.ChoiceField(
        choices=settings.MANTRA_SETTINGS['CELEBRITY_CATEGORIES'],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        help_text='Select your primary category/genre'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',
                 'first_name', 'last_name', 'phone', 'country', 'city', 'bio', 'profile_picture')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number (optional)'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us about yourself...',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields clear
        self.fields['country'].required = True
        self.fields['category'].required = True

    def save(self, commit=True):
        from apps.celebrities.models import CelebrityProfile

        user = super().save(commit=False)
        user.user_type = 'celebrity'
        user.email = self.cleaned_data['email']
        user.country = self.cleaned_data['country']
        user.city = self.cleaned_data.get('city', '')
        user.category = self.cleaned_data['category']
        
        # Set verification status to pending for celebrities
        user.verification_status = 'pending'

        if commit:
            user.save()
            UserPreferences.objects.get_or_create(user=user)

            # Create or update celebrity profile with category
            celeb_profile, created = CelebrityProfile.objects.get_or_create(user=user)
            celeb_profile.categories = [self.cleaned_data['category']]
            celeb_profile.save()

            user.add_points(50, "Celebrity welcome bonus")

        return user

    def clean_country(self):
        """Validate country field"""
        country = self.cleaned_data.get('country')
        if not country:
            raise ValidationError('Country is required for celebrity registration.')
        return country

    def clean_category(self):
        """Validate category field"""
        category = self.cleaned_data.get('category')
        if not category:
            raise ValidationError('Category is required for celebrity registration.')
        return category


class SignUpForm(forms.ModelForm):
    """User registration form"""

    USER_TYPE_CHOICES = [
        ('fan', 'Fan - Follow and support your favorite celebrities'),
        ('celebrity', 'Celebrity - Connect with your fans'),
    ]

    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'user-type-radio'}),
        initial='fan'
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        }),
        min_length=8,
        help_text='Password must be at least 8 characters long'
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )

    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(),
        label='I agree to the Terms of Service and Privacy Policy'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type',
                 'password', 'confirm_password', 'date_of_birth', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a unique username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            })
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Check if username is alphanumeric with underscores only
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('Username can only contain letters, numbers, and underscores.')

        # Check minimum length
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters long.')

        # Check if username exists
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken.')

        return username.lower()

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')

        return email.lower()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError('Passwords do not match.')

            # Check password strength
            if not re.search(r'[A-Z]', password):
                raise ValidationError('Password must contain at least one uppercase letter.')

            if not re.search(r'[a-z]', password):
                raise ValidationError('Password must contain at least one lowercase letter.')

            if not re.search(r'[0-9]', password):
                raise ValidationError('Password must contain at least one number.')

        return cleaned_data


class LoginForm(forms.Form):
    """User login form"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(),
        label='Remember me'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Allow login with email or username
        if '@' in username:
            try:
                user = User.objects.get(email__iexact=username)
                return user.username
            except User.DoesNotExist:
                raise ValidationError('No account found with this email.')

        return username.lower()


class ProfileUpdateForm(forms.ModelForm):
    """Profile update form"""

    remove_profile_picture = forms.BooleanField(
        required=False,
        label='Remove current profile picture'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'profile_picture',
                 'cover_image', 'country', 'city', 'website', 'date_of_birth']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://yourwebsite.com'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')

        if picture:
            # Check file size (max 5MB)
            if picture.size > 5 * 1024 * 1024:
                raise ValidationError('Profile picture must be less than 5MB.')

            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            import os
            ext = os.path.splitext(picture.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Invalid file format. Use JPG, PNG, GIF, or WEBP.')

        return picture

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.cleaned_data.get('remove_profile_picture'):
            instance.profile_picture = None

        if commit:
            instance.save()

        return instance


class PreferencesForm(forms.ModelForm):
    """User preferences form"""

    class Meta:
        model = UserPreferences
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'who_can_message': forms.Select(attrs={'class': 'form-control'}),
            'who_can_see_posts': forms.Select(attrs={'class': 'form-control'}),
            'who_can_see_followers': forms.Select(attrs={'class': 'form-control'}),
            'who_can_tag': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Group fields by category for better template organization
        self.privacy_fields = [
            'who_can_message', 'who_can_see_posts',
            'who_can_see_followers', 'who_can_tag'
        ]

        self.notification_fields = [
            'email_notifications', 'push_notifications',
            'notify_new_follower', 'notify_likes', 'notify_comments',
            'notify_mentions', 'notify_messages', 'notify_events'
        ]

        self.content_fields = [
            'show_adult_content', 'autoplay_videos', 'high_quality_media'
        ]

        # Add Bootstrap classes to checkbox fields
        for field_name in self.fields:
            field = self.fields[field_name]
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with better validation"""

    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password'
        })
    )

    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password'
        }),
        help_text='Must be at least 8 characters with uppercase, lowercase, and numbers'
    )

    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')

        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')

        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one number.')

        return password


class PasswordResetRequestForm(forms.Form):
    """Password reset request form"""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not User.objects.filter(email__iexact=email).exists():
            raise ValidationError('No account found with this email address.')

        return email.lower()


class KYCVerificationForm(forms.Form):
    """KYC verification form for celebrities"""

    DOCUMENT_TYPES = [
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('national_id', 'National ID Card'),
        ('other', 'Other Government ID'),
    ]

    document_type = forms.ChoiceField(
        choices=DOCUMENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    document_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Document number'
        })
    )

    document_front = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,application/pdf'
        }),
        help_text='Upload front side of document'
    )

    document_back = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,application/pdf'
        }),
        help_text='Upload back side of document (if applicable)'
    )

    selfie_with_document = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text='Upload a selfie holding your document'
    )

    consent = forms.BooleanField(
        required=True,
        label='I consent to the verification of my identity and understand that false information may result in account termination'
    )

    def clean_document_front(self):
        file = self.cleaned_data.get('document_front')

        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size must be less than 10MB.')

        return file


class UnifiedLoginForm(forms.Form):
    """Unified login form - kept for backward compatibility"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    user_type = forms.ChoiceField(
        choices=[
            ('fan', 'Fan'),
            ('celebrity', 'Celebrity'),
            ('admin', 'Admin'),
            ('subadmin', 'Sub-Admin'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )

    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        user_type = cleaned_data.get('user_type')

        if username and password:
            # Check if username is actually an email
            if '@' in username:
                try:
                    user = User.objects.get(email=username)
                    username = user.username
                except User.DoesNotExist:
                    raise forms.ValidationError("Invalid credentials")

            # Authenticate user
            user = authenticate(username=username, password=password)

            if user is None:
                raise forms.ValidationError("Invalid username or password")

            # Check user type (superusers are always admins)
            if user.is_superuser and user_type == 'admin':
                # Superusers can log in as admin
                pass
            elif user.user_type != user_type:
                raise forms.ValidationError(f"This account is not a {user_type} account")

            # Check if user is banned
            if user.check_ban_status():
                raise forms.ValidationError(f"Account banned: {user.ban_reason}")

            # Check if user is active
            if not user.is_active:
                raise forms.ValidationError("Account is inactive")

            cleaned_data['user'] = user

        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile - legacy"""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'bio', 'profile_picture',
                 'cover_image', 'phone', 'country', 'city')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserPreferencesForm(forms.ModelForm):
    """Form for updating user preferences - legacy"""

    class Meta:
        model = UserPreferences
        exclude = ('user',)
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'show_mature_content': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'autoplay_videos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_new_follower': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_new_message': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_new_comment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_new_like': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_celebrity_post': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_event_reminder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'who_can_message': forms.Select(attrs={'class': 'form-select'}),
            'who_can_see_followers': forms.Select(attrs={'class': 'form-select'}),
        }


class SubAdminCreationForm(UserCreationForm):
    """Form for creating sub-admin users"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    assigned_region = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Assigned region (optional)'})
    )
    assigned_areas = forms.MultipleChoiceField(
        choices=[
            ('content_moderation', 'Content Moderation'),
            ('user_verification', 'User Verification'),
            ('analytics', 'Analytics'),
            ('support', 'Support'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = 'sub_admin'
        user.is_staff = True

        if commit:
            user.save()

        return user