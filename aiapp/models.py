# aiapp/models.py
from django.db import models

class RawVisitScan(models.Model):
    image = models.ImageField(upload_to='scans/%Y/%m/%d/', verbose_name="تصویر برگه")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    voice=models.ImageField(upload_to='scans/%Y/%m/%d/', verbose_name="تصویر برگه")
    class Meta:
        verbose_name = "اسکن برگه ویزیت"
        verbose_name_plural = "اسکن‌های برگه ویزیت"