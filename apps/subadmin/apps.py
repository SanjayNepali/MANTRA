# apps/subadmin/apps.py
"""
SubAdmin App Configuration
"""

from django.apps import AppConfig


class SubAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.subadmin'
    verbose_name = 'SubAdmin Management'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signal handlers if needed
        try:
            from . import signals
        except ImportError:
            pass