# apps/celebrities/apps.py

from django.apps import AppConfig

class CelebritiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.celebrities'
    
    def ready(self):
        import apps.celebrities.signals