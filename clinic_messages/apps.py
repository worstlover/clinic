# D:\final\clinic_messages\apps.py

from django.apps import AppConfig

class ClinicMessagesConfig(AppConfig): # نام کلاس را تغییر دهید
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clinic_messages' # نام اپ را تغییر دهید
    verbose_name = "پیام‌های کلینیک" # نام نمایشی را تغییر دهید

    def ready(self):
        import clinic_messages.signals # مسیر ایمپورت سیگنال را تغییر دهید