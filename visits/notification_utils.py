# D:\final\visits\notification_utils.py

from fcm_django.models import FCMDevice
from django.db import transaction
from django.conf import settings # برای دسترسی به تنظیمات پروژه
import os

def send_visit_referral_notification(visit_instance, recipient_user, sender_user):
    """
    ارسال یک نوتیفیکیشن FCM به کاربر مسئول جدید هنگام ارجاع ویزیت.
    """
    # عنوان نوتیفیکیشن
    title = f"ویزیت جدید ارجاعی: {visit_instance.patient.full_name}"
    
    # پیام نوتیفیکیشن
    body = f"ویزیت بیمار {visit_instance.patient.full_name} توسط دکتر {sender_user.get_full_name()} به شما ارجاع داده شد."
    
    # URLی که با کلیک روی نوتیفیکیشن باز می‌شود
    # از آدرس سرور شما که قبلا اشاره کردید استفاده می‌کنم.
    # برای محیط توسعه، اگر از IP استفاده می‌کنید، مطمئن شوید که مرورگر کاربر به آن دسترسی دارد.
    notification_url = f"http://94.101.177.176/visits/?view=referred_to_me" # این باید URL صحیح شما باشد

    # داده‌های اضافی که می‌توانید به نوتیفیکیشن اضافه کنید
    data = {
        "visit_id": str(visit_instance.pk),
        "patient_name": visit_instance.patient.full_name,
        "sender_name": sender_user.get_full_name(),
        "click_action": notification_url, # این برای هندل کردن کلیک در Service Worker مفید است.
        "sound": "default" # می‌توانید اینجا نام فایل صوتی دلخواه را قرار دهید،
                            # و Service Worker شما باید آن را به صورت دستی پخش کند
                            # (یا از صدای پیش‌فرض مرورگر استفاده کند).
    }

    try:
        # دریافت دستگاه‌های FCM ثبت شده برای کاربر گیرنده
        # اگر ONE_DEVICE_PER_USER در settings=True باشد، فقط آخرین دستگاه فعال را می‌گیرد.
        devices = FCMDevice.objects.filter(user=recipient_user, active=True)
        
        if not devices.exists():
            print(f"DEBUG: No active FCM devices found for user {recipient_user.username}. Notification not sent.")
            return

        # ارسال نوتیفیکیشن به تمام دستگاه‌های فعال کاربر
        # از transaction.atomic استفاده می‌کنیم تا اگر ارسال به مشکلی خورد، لاگ شود
        with transaction.atomic():
            for device in devices:
                try:
                    # 'data_message' برای ارسال داده به Service Worker است، نه فقط نمایش نوتیفیکیشن.
                    # 'message' (یا 'notification') برای نمایش مستقیم نوتیفیکیشن به کاربر است.
                    # ما هم 'message' (برای نمایش نوتیفیکیشن) و هم 'data_message' (برای Service Worker) را می‌دهیم.
                    device.send_message(
                        title=title,
                        body=body,
                        data=data,
                        sound="default", # این صدای پیش‌فرض سیستم را پخش می‌کند، اگر دستگاه پشتیبانی کند.
                                         # برای پخش صدای سفارشی که در Service Worker تنظیم کردید،
                                         # Service Worker باید data.sound را بخواند و آن را پخش کند.
                        click_action=notification_url # این به مرورگر می‌گوید چه کاری انجام دهد.
                                                     # Service Worker کد خود را override می‌کند.
                    )
                    print(f"DEBUG: FCM notification sent to device {device.device_id} for user {recipient_user.username}")
                except Exception as e:
                    print(f"ERROR: Failed to send FCM message to device {device.device_id} for user {recipient_user.username}: {e}")
                    # در محیط پروداکشن، می‌توانید اینجا logging دقیق‌تری انجام دهید
                    # و یا دستگاه را غیرفعال کنید اگر خطای مداوم وجود دارد.

    except Exception as e:
        print(f"ERROR: An unexpected error occurred while preparing FCM notification for visit {visit_instance.pk}: {e}")