# config/settings.py

import os
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
from pathlib import Path
from decouple import config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = 'django-insecure-your-secret-key-for-development-only-2024'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'daphne',  # For ASGI/WebSocket support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    
    # Custom apps
    'apps.accounts',
    'apps.celebrities',
    'apps.fans',
    'apps.fanclubs',
    'apps.posts',
    'apps.messaging',
    'apps.events',
    'apps.merchandise',
    'apps.payments',
    'apps.notifications',
    'apps.reports',
    'apps.analytics',
    'apps.subadmin',
    'apps.admin_dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                # Custom context processors
                'apps.notifications.context_processors.notifications_count',
                'apps.messaging.context_processors.unread_messages',
            ],
        },
    },
]

# ASGI Configuration for Channels
ASGI_APPLICATION = 'config.asgi.application'

# Channels Layer Configuration (Redis)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

SENTIMENT_ANALYSIS = {
    'TOXICITY_THRESHOLD': 0.7,  # Above this is considered toxic
    'SPAM_THRESHOLD': 0.6,       # Above this is considered spam
    'AUTO_DELETE_THRESHOLD': 0.9, # Auto-delete highly toxic content
    'WARNING_THRESHOLD': 0.5,     # Issue warning above this
    'ADMIN_ALERT_THRESHOLD': 0.8,  # For critical alerts
}

SUBADMIN_MODERATION = {
    'POINTS_DEDUCTION': {
        'warning': 20,
        'content_deletion': 10,
        'suspension': 100,
        'ban': 500,
    },
    'SUSPENSION_DURATIONS': [3, 7, 14, 30],  # Days
    'MAX_WARNINGS_BEFORE_SUSPENSION': 3,
}

# Available Countries for SubAdmin Assignment
AVAILABLE_COUNTRIES = [
    # South Asia
    'nepal', 'india', 'bangladesh', 'sri_lanka', 'pakistan', 'bhutan', 'maldives',

    # Southeast Asia
    'myanmar', 'thailand', 'indonesia', 'malaysia', 'singapore', 'philippines',
    'vietnam', 'cambodia', 'laos',

    # East Asia
    'china', 'japan', 'south_korea', 'hong_kong', 'taiwan',

    # Middle East
    'uae', 'saudi_arabia', 'qatar', 'kuwait', 'oman', 'bahrain', 'turkey',
    'iran', 'iraq', 'jordan', 'lebanon', 'israel',

    # Central Asia
    'kazakhstan', 'uzbekistan', 'turkmenistan', 'kyrgyzstan', 'tajikistan', 'afghanistan',

    # Europe
    'uk', 'france', 'germany', 'italy', 'spain', 'netherlands', 'belgium',
    'switzerland', 'austria', 'sweden', 'norway', 'denmark', 'finland', 'poland',
    'portugal', 'greece', 'ireland', 'czech_republic', 'hungary', 'romania',

    # North America
    'usa', 'canada', 'mexico',

    # South America
    'brazil', 'argentina', 'colombia', 'chile', 'peru', 'venezuela', 'ecuador',

    # Africa
    'south_africa', 'nigeria', 'egypt', 'kenya', 'ghana', 'ethiopia', 'morocco',
    'tanzania', 'uganda', 'algeria', 'tunisia',

    # Oceania
    'australia', 'new_zealand', 'fiji', 'papua_new_guinea',

    # Other
    'other'
]

# Admin Dashboard Settings
ADMIN_DASHBOARD_SETTINGS = {
    'AUTO_REFRESH_INTERVAL': 300,  # seconds
    'CRITICAL_ALERT_THRESHOLD': 10,
    'MAX_EXPORT_SIZE': 100 * 1024 * 1024,  # 100MB
    'EXPORT_EXPIRY_DAYS': 7,
    'AUDIT_LOG_RETENTION_DAYS': 90,
}

# System Health Thresholds
SYSTEM_HEALTH_THRESHOLDS = {
    'CRITICAL': 40,
    'WARNING': 70,
    'GOOD': 90,
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Login URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Email Configuration (Console backend for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# MANTRA Custom Settings
MANTRA_SETTINGS = {
    'FAN_RANKS': [
        ('observer', 'Observer', 0),
        ('enthusiast', 'Enthusiast', 100),
        ('supporter', 'Supporter', 500),
        ('devotee', 'Devotee', 1000),
        ('champion', 'Champion', 5000),
        ('legend', 'Legend', 10000),
        ('icon', 'Icon', 50000),
        ('eternal', 'Eternal', 100000),
    ],
    'CELEBRITY_RANKS': [
        ('novice', 'Novice', 0),
        ('rising', 'Rising Star', 1000),
        ('established', 'Established', 5000),
        ('prominent', 'Prominent', 10000),
        ('acclaimed', 'Acclaimed', 50000),
        ('legendary', 'Legendary', 100000),
        ('iconic', 'Iconic', 500000),
        ('immortal', 'Immortal', 1000000),
    ],
    'CELEBRITY_CATEGORIES': [
        ('actor', 'Actor'),
        ('singer', 'Singer'),
        ('rapper', 'Rapper'),
        ('comedian', 'Comedian'),
        ('athlete', 'Athlete'),
        ('influencer', 'Influencer'),
        ('model', 'Model'),
        ('musician', 'Musician'),
        ('dancer', 'Dancer'),
        ('other', 'Other'),
    ],
    'POINTS_RULES': {
        'post_create': 10,
        'post_like': 2,
        'post_comment': 5,
        'follow': 3,
        'subscription': 50,
        'event_booking': 20,
        'merchandise_purchase': 15,
        'violation_minor': -20,
        'violation_major': -100,
    },
    'PAYMENT_METHODS': [
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
    ],
    'MAX_MESSAGE_LENGTH': 1000,
    'MAX_POST_LENGTH': 5000,
    'MAX_COMMENT_LENGTH': 500,
}

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# eSewa Payment Gateway Configuration
ESEWA_MERCHANT_CODE = config('ESEWA_MERCHANT_CODE', default='EPAYTEST')
ESEWA_SECRET_KEY = config('ESEWA_SECRET_KEY', default='8gBm/:&EnhH.1/q')
ESEWA_MOCK_MODE = config('ESEWA_MOCK_MODE', default=True, cast=bool)
ESEWA_PAYMENT_URL = config('ESEWA_PAYMENT_URL', default='https://rc-epay.esewa.com.np/api/epay/main/v2/form')
ESEWA_STATUS_URL = config('ESEWA_STATUS_URL', default='https://rc-epay.esewa.com.np/api/epay/transaction/status/')
ESEWA_VERIFICATION_URL = ESEWA_STATUS_URL

# Payment Configuration
PAYMENT_SETTINGS = {
    'PLATFORM_FEE_PERCENTAGE': {
        'subscription': 20,
        'event': 15,
        'merchandise': 10,
        'tip': 10,
    },
    'MINIMUM_WITHDRAWAL': 100,
    'PAYMENT_TIMEOUT': 600,
}

# Debug toolbar (for development)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']