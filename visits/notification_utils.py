# D:\final\visits\notification_utils.py

from fcm_django.models import FCMDevice
from clinic_messages.models import Notification # فرض می‌کنیم این مدل وجود دارد
from django.urls import reverse # برای ساخت لینک به ویزیت
from django.conf import settings # برای دسترسی به مدل User


def send_visit_referral_notification(visit_instance, recipient_user, sender_user):
    """
    تابع کمکی برای ارسال نوتیفیکیشن ارجاع ویزیت.
    نوتیفیکیشن را در دیتابیس ذخیره کرده و به صورت پوش (FCM) ارسال می‌کند.
    """
    message_title = "ویزیت جدید به شما ارجاع شد!"
    message_body = (
        f"ویزیت بیمار {visit_instance.patient.get_full_name()} "
        f"(تاریخ: {visit_instance.visit_date.strftime('%Y/%m/%d - %H:%M')}) "
        "به شما ارجاع داده شد. لطفاً آن را بررسی کنید."
    )
    
    # اطمینان از وجود get_absolute_url یا ساخت لینک دستی
    try:
        link_to_visit = visit_instance.get_absolute_url()
    except AttributeError:
        link_to_visit = reverse('visits:visit_detail', args=[visit_instance.pk])

    # 1. ذخیره نوتیفیکیشن در دیتابیس (مدل Notification)
    try:
        Notification.objects.create(
            recipient=recipient_user,
            sender=sender_user,
            message=message_body,
            link=link_to_visit,
            notification_type='referral',
            is_read=False # اطمینان از مقداردهی is_read به False در زمان ایجاد
        )
        print(f"DEBUG: Database Notification created for {recipient_user.username}.")
    except Exception as e:
        print(f"ERROR: Error creating database notification for {recipient_user.username}: {e}")

    # 2. ارسال نوتیفیکیشن پوش با FCM
    devices = FCMDevice.objects.filter(user=recipient_user, active=True)
    if devices.exists():
        try:
            # ارسال پیام به تمام دستگاه‌های فعال این کاربر
            devices.send_message(
                title=message_title, 
                body=message_body,
                data={
                    "visit_id": str(visit_instance.pk), # دیتا باید استرینگ باشد
                    "type": "referral",
                    "link": link_to_visit 
                } 
            )
            print(f"DEBUG: FCM Notification sent to {recipient_user.username} for visit {visit_instance.pk}.")
        except Exception as e:
            print(f"ERROR: Error sending FCM notification to {recipient_user.username}: {e}")
    else:
        print(f"DEBUG: No active FCM devices found for user {recipient_user.username} to send notification for visit {visit_instance.pk}.")