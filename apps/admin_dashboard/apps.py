# apps/admin_dashboard/apps.py
"""
Admin Dashboard App Configuration
"""

from django.apps import AppConfig


class AdminDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.admin_dashboard'
    verbose_name = 'Admin Dashboard'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signal handlers if they exist
        try:
            from . import signals
        except ImportError:
            pass

        # Schedule periodic tasks if using Celery
        try:
            from .tasks import schedule_periodic_tasks
            schedule_periodic_tasks()
        except ImportError:
            pass