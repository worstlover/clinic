# visits/signals.py

from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.db import transaction
from .models import Visit
from drugs.models import DrugBatch, Drug
from clinic_messages.models import Notification # فرض می‌شود مدل نوتیفیکیشن در اپ clinic_messages قرار دارد

# ایمپورت تابع ارسال نوتیفیکیشن
from .notification_utils import send_visit_referral_notification 

@receiver(pre_save, sender=Visit)
def handle_stock_on_visit_completion(sender, instance, **kwargs):
    """
    موجودی انبار را فقط در زمان تغییر وضعیت ویزیت به "تکمیل شده" یا برگشت از آن، مدیریت می‌کند.
    این سیگنال قبل از ذخیره آبجکت اجرا می‌شود.
    """
    if not instance.pk:
        # اگر آبجکت جدید است، نیازی به بررسی تغییر وضعیت نیست
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        # اگر آبجکت قدیمی پیدا نشد (نباید اتفاق بیفتد مگر در شرایط خاص)، کاری نمی‌کنیم
        return

    # سناریو ۱: ویزیت در حال "تکمیل شدن" است (از وضعیت غیرتکمیل به تکمیل)
    if instance.status == 'completed' and old_instance.status != 'completed':
        with transaction.atomic():
            for item in instance.items.all():
                try:
                    # فراخوانی متد برای کسر از بچ‌های دارو
                    # DrugBatch.remove_from_batches باید logic خطا را شامل شود و خطا را raise کند
                    DrugBatch.remove_from_batches(item.drug, item.quantity)
                except Exception as e:
                    print(f"Error decreasing stock for {item.drug.name}: {e}")
                    # مهم: اگر نمی‌خواهید ویزیت تکمیل شود، باید اینجا خطا را raise کنید
                    raise Exception(f"موجودی داروی {item.drug.name} کافی نیست یا خطایی رخ داد: {e}")

    # سناریو ۲: ویزیت "تکمیل شده" به وضعیت دیگری برمی‌گردد (فقط توسط ادمین)
    elif old_instance.status == 'completed' and instance.status != 'completed':
        with transaction.atomic():
            for item in instance.items.all():
                try:
                    # فراخوانی متد برای بازگرداندن به بچ‌های دارو
                    DrugBatch.add_to_batches(item.drug, item.quantity, is_return=True)
                except Exception as e:
                    print(f"Error increasing stock for {item.drug.name} on status revert: {e}")

# برای جلوگیری از تداخل، نوتیفیکیشن ارجاع را در post_save مجدداً بررسی می‌کنیم
# با این حال، نیاز داریم که assigned_to قبلی را بدانیم
@receiver(post_save, sender=Visit)
def create_referral_notification(sender, instance, created, **kwargs):
    """
    زمانی که یک ویزیت به کاربر جدیدی ارجاع داده می‌شود، یک نوتیفیکیشن ایجاد و ارسال می‌کند.
    """
    # در زمان ایجاد ویزیت جدید
    if created:
        # اگر ویزیت تازه ایجاد شده و assigned_to دارد (که در visit_create تنظیم می‌شود)
        if instance.assigned_to:
            # ارسال نوتیفیکیشن برای کاربر مسئول اولیه (اگر متفاوت از doctor باشد، یا همیشه)
            # اینجا فرض می‌کنیم doctor همان ایجاد کننده است و assigned_to کسی است که ویزیت به او سپرده شده
            send_visit_referral_notification(instance, instance.assigned_to, instance.doctor)
            print(f"DEBUG: Initial referral notification sent for new visit {instance.pk} to {instance.assigned_to.username}")
        return # پایان کار برای created

    # در زمان آپدیت ویزیت
    try:
        # دریافت نسخه قدیمی آبجکت برای مقایسه
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return # نباید اتفاق بیفتد مگر مشکل در دیتابیس

    # اگر وضعیت ویزیت به 'referred' تغییر کرده باشد
    # و کاربر مسئول جدیدی (مغایر با قبلی) تعیین شده باشد
    if (old_instance.status != 'referred' and instance.status == 'referred' and
        old_instance.assigned_to != instance.assigned_to and instance.assigned_to):
        
        # فرستنده نوتیفیکیشن کاربری است که ارجاع را انجام داده (همان assigned_to قبلی)
        sender_user = old_instance.assigned_to if old_instance.assigned_to else instance.doctor # اگر قبلا assigned_to نبوده، doctor فرستنده است
        
        # ارسال نوتیفیکیشن برای کاربر مسئول جدید
        send_visit_referral_notification(instance, instance.assigned_to, sender_user)
        print(f"DEBUG: Referral notification sent for updated visit {instance.pk} to {instance.assigned_to.username}")

    # اگر assigned_to تغییر کرده باشد ولی وضعیت هنوز 'pending' است (یا هر وضعیت غیر از 'referred')
    # و کاربر جدیدی تعیین شده باشد
    elif (old_instance.assigned_to != instance.assigned_to and instance.assigned_to and
          instance.status != 'referred'):
        # این حالت می‌تواند به معنی تغییر مسئول بدون ارجاع رسمی باشد،
        # مثلاً اگر یک ویزیت در حال بررسی به کس دیگری سپرده شود.
        # می‌توانید نوتیفیکیشن متفاوتی برای این حالت ارسال کنید یا اصلاً ارسال نکنید.
        # برای سادگی، فعلا فقط در حالت 'referred' نوتیفیکیشن ارجاع ارسال می‌شود.
        pass