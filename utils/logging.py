# utils/logging.py

import logging
from django.core.mail import mail_admins
from django.utils import timezone

logger = logging.getLogger('mantra')

class ErrorNotificationHandler(logging.Handler):
    """Send email to admins on critical errors"""
    
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            subject = f"MANTRA Error: {record.getMessage()}"
            message = self.format(record)
            mail_admins(subject, message, fail_silently=True)

def log_user_action(user, action, details=None):
    """Log user actions for audit trail"""
    logger.info(f"User {user.username} performed {action}", extra={
        'user_id': user.id,
        'action': action,
        'details': details,
        'timestamp': timezone.now()
    })