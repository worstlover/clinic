# D:\final\drugs\signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import Q # اگر برای فیلتر کردن پیشرفته تر نقش ها نیاز شد
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Drug
from django.db.models import Max
# ایمپورت مدل DrugRequest از همین اپلیکیشن drugs
from .models import DrugRequest

# ایمپورت مدل Notification از اپلیکیشن clinic_messages
from clinic_messages.models import Notification
from clinic_messages.models import Message
# ایمپورت FCMDevice برای ارسال پوش نوتیفیکیشن
from fcm_django.models import Device

User = get_user_model()



@receiver(pre_save, sender=Drug)
def generate_drug_code(sender, instance, **kwargs):
    """
    تولید کد دارو به صورت خودکار (عددی) قبل از ذخیره یک داروی جدید.
    اگر drug_code قبلاً پر نشده باشد، آخرین کد موجود را به اضافه 1 می‌کند.
    اگر هیچ دارویی موجود نباشد، از 1001 شروع می‌کند.
    """
    if not instance.drug_code: # اگر کد دارو هنوز تنظیم نشده است
        # پیدا کردن بزرگترین کد داروی موجود در دیتابیس
        last_code = sender.objects.all().aggregate(Max('drug_code'))['drug_code__max']

        if last_code is not None:
            # اگر کدی قبلاً وجود داشت، یکی به آن اضافه کن
            instance.drug_code = last_code + 1
        else:
            # اگر هیچ کدی وجود نداشت (اولین دارو)، از 1001 شروع کن
            instance.drug_code = 1001        