# visits/apps.py

from django.apps import AppConfig

class VisitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'visits'

    def ready(self):
        # این خط برای فعال‌سازی سیگنال‌ها ضروری است
        import visits.signals
        