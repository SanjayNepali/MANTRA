#!/bin/bash

# MANTRA - Celebrity Fan Portal Management System
# Deployment and Setup Script
# This script automates the setup process for the MANTRA Django project

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# ASCII Art Banner
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   ███╗   ███╗ █████╗ ███╗   ██╗████████╗██████╗  █████╗  ║
║   ████╗ ████║██╔══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔══██╗ ║
║   ██╔████╔██║███████║██╔██╗ ██║   ██║   ██████╔╝███████║ ║
║   ██║╚██╔╝██║██╔══██║██║╚██╗██║   ██║   ██╔══██╗██╔══██║ ║
║   ██║ ╚═╝ ██║██║  ██║██║ ╚████║   ██║   ██║  ██║██║  ██║ ║
║   ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ║
║                                                            ║
║       Celebrity Fan Portal Management System              ║
║                  Setup & Deployment Script                ║
╚════════════════════════════════════════════════════════════╝
EOF

echo ""
print_status "Starting MANTRA setup process..."
echo ""

# Check Python version
print_status "Checking Python version..."
python_version=$(python --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    print_status "Python $python_version detected (OK)"
else
    print_error "Python $python_version detected. Python 3.9+ is required."
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Using existing environment."
else
    print_status "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/Scripts/Activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install requirements
print_status "Installing requirements (this may take a few minutes)..."
pip install -r requirements.txt

# Install NLTK data
print_status "Downloading NLTK data for sentiment analysis..."
python -c "
import nltk
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
    
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('vader_lexicon', quiet=True)
print('NLTK data downloaded successfully')
"

# Check if .env file exists
if [ -f ".env" ]; then
    print_warning ".env file already exists. Skipping creation."
else
    print_status "Creating .env file..."
    cat > .env << EOL
# Django Settings
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite for development)
DATABASE_URL=sqlite:///db.sqlite3

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (Console backend for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Media Files
MEDIA_ROOT=media/
MEDIA_URL=/media/

# Static Files
STATIC_ROOT=staticfiles/
STATIC_URL=/static/

# Security
CSRF_TRUSTED_ORIGINS=http://localhost:8000

# Payment Simulation
PAYMENT_SIMULATION_MODE=True
EOL
    print_status ".env file created with default settings"
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p media/profiles
mkdir -p media/posts
mkdir -p media/events
mkdir -p media/merchandise
mkdir -p media/fanclubs
mkdir -p media/qr_codes
mkdir -p staticfiles
mkdir -p logs

# Run database migrations
print_status "Running database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# Check if superuser exists
print_status "Checking for superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print("No superuser found.")
    exit(1)
else:
    print("Superuser exists.")
    exit(0)
EOF

if [ $? -ne 0 ]; then
    print_warning "No superuser found. Creating one now..."
    echo "Please enter superuser credentials:"
    python manage.py createsuperuser
else
    print_status "Superuser already exists."
fi

# Create sample data (optional)
read -p "Do you want to create sample data? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Creating sample data..."
    python manage.py shell << EOF
from apps.accounts.models import User
from apps.celebrities.models import CelebrityProfile
from apps.posts.models import Post
import random

# Create sample celebrities
celebrities_created = 0
for i in range(5):
    username = f"celebrity{i+1}"
    if not User.objects.filter(username=username).exists():
        celeb = User.objects.create_user(
            username=username,
            email=f"celebrity{i+1}@example.com",
            password="testpass123",
            user_type="celebrity",
            first_name=f"Celebrity",
            last_name=f"Star{i+1}",
            is_verified=True
        )
        CelebrityProfile.objects.create(
            user=celeb,
            category=random.choice(['actor', 'singer', 'athlete', 'influencer'])[0],
            bio=f"Famous {celeb.get_user_type_display()}",
            verification_status='approved'
        )
        celebrities_created += 1

# Create sample fans
fans_created = 0
for i in range(10):
    username = f"fan{i+1}"
    if not User.objects.filter(username=username).exists():
        fan = User.objects.create_user(
            username=username,
            email=f"fan{i+1}@example.com",
            password="testpass123",
            user_type="fan",
            first_name=f"Fan",
            last_name=f"User{i+1}"
        )
        fans_created += 1

print(f"Created {celebrities_created} celebrities and {fans_created} fans")
EOF
    print_status "Sample data created successfully"
fi

# Check Redis
print_status "Checking Redis connection..."
python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print('Redis is running')
except:
    print('Warning: Redis is not running. Some features may not work.')
" || print_warning "Redis is not running. Start it with: redis-server"

echo ""
print_status "Setup completed successfully!"
echo ""
echo "======================================"
echo "          NEXT STEPS                  "
echo "======================================"
echo ""
echo "1. Start Redis server (if not running):"
echo "   redis-server"
echo ""
echo "2. Start the development server:"
echo "   python manage.py runserver"
echo ""
echo "3. Access the application:"
echo "   http://localhost:8000"
echo ""
echo "4. Admin panel:"
echo "   http://localhost:8000/admin"
echo ""
echo "5. For WebSocket support, use:"
echo "   daphne -b 0.0.0.0 -p 8000 config.asgi:application"
echo ""
echo "======================================"
echo "Default Test Accounts (if sample data created):"
echo "Username: celebrity1, Password: testpass123"
echo "Username: fan1, Password: testpass123"
echo "======================================"
echo ""
print_status "Happy coding! 🚀"