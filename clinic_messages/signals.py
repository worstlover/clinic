# D:\final\clinic_messages\signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model # تغییر User به get_user_model
from django.urls import reverse
from django.utils import timezone 

from .models import Message, MessageRecipient, Notification 
from drugs.models import DrugRequest 

User = get_user_model() # تعریف User

# تابع placeholder برای ارسال پوش نوتیفیکیشن موبایل (همانند views.py)
#def send_mobile_push_notification(user, title, body, data=None):
  #  """
   # این تابع یک پوش نوتیفیکیشن موبایل ارسال می‌کند.
    #شما باید این تابع را با منطق واقعی سرویس پوش نوتیفیکیشن خود (مثلاً FCM) پیاده‌سازی کنید.
    #"""
 #   print(f"Sending mobile push notification to {user.username} from signal: Title='{title}', Body='{body}'")
  #  if data:
   #     print(f"Data: {data}")
    # اینجا باید کد واقعی برای ارسال نوتیفیکیشن به پلتفرم‌های موبایل (مانند FCM) را اضافه کنید.






# Signal for DrugRequest status change notification
#@receiver(post_save, sender=DrugRequest)
#def create_drug_request_notification(sender, instance, created, **kwargs):
    #if created:
        # وقتی یک درخواست دارو جدید ایجاد می‌شود، به مدیران اطلاع داده شود
        #manager_users = User.objects.filter(is_staff=True) # مثال: همه کارمندان (مدیران)
        #if manager_users.exists():
            #message_body = (
               # f"درخواست داروی جدیدی با شناسه {instance.pk} توسط {instance.requested_by.username} ایجاد شد.\n"
                #f"دارو: {', '.join([item.drug.name for item in instance.items.all()])}, تعداد: {sum([item.requested_quantity for item in instance.items.all()])}.\n" # بهتر است آیتم‌ها را نمایش دهیم
                #f"وضعیت فعلی: {instance.get_status_display()}."
   #         )
            #request_link = reverse('drugs:drug_request_detail', args=[instance.pk])
            #message = Message.objects.create(
              
              #  sender=instance.requested_by, # Person who initiated the request
               # subject=f"تأیید درخواست دارو {instance.pk}",
                #body=message_body,
                #related_drug_request=instance,
           # )
            #for manager in manager_users:
             #   MessageRecipient.objects.create(message=message, recipient=manager)
              #  # --- ایجاد نوتیفیکیشن ---
               # Notification.objects.create(
                #    recipient=manager,
                 #   sender=instance.requested_by,
                  #  message=message_body,
                   # link=request_link,
                    #notification_type='new_drug_request'
                #)
                # --- ارسال پوش نوتیفیکیشن موبایل ---
                #send_mobile_push_notification(
                 #   user=manager,
                  #  title="درخواست داروی جدید",
                   # body=message_body,
                    #data={'drug_request_id': instance.pk, 'type': 'new_drug_request'}
                #)

    # Example: If approved/rejected, notify the original requester
    # این بخش زمانی که last_updated_by اضافه شده است منطقی‌تر است
   # if instance.status in ['approved', 'rejected'] and not created: # اگر وضعیت تغییر کرده باشد
    #    recipient = instance.requested_by # Original requester
     #   
      #  # تعیین sender: اگر last_updated_by وجود دارد، از آن استفاده کن، وگرنه از requested_by (سازنده اصلی)
       # notification_sender = instance.last_updated_by if instance.last_updated_by else instance.requested_by

        #if instance.status == 'approved':
         #   subject = f"تأیید درخواست دارو {instance.pk}"
          #  body = f"درخواست داروی شما (شناسه {instance.pk}) با موفقیت تأیید شد."
           # notification_type = 'drug_request_approved'
        #else: # rejected
         #   subject = f"رد درخواست دارو {instance.pk}"
          #  body = f"درخواست داروی شما (شناسه {instance.pk}) رد شد. لطفا جزئیات را بررسی کنید. دلیل: {instance.doctor_rejection_reason or instance.supervisor_rejection_reason or 'نامشخص'}"
           # notification_type = 'drug_request_rejected'

        #request_link = reverse('drug_request_detail', args=[instance.pk])

        #message = Message.objects.create(
         #   sender=notification_sender, 
          #  subject=subject,
           # body=body,
            #related_drug_request=instance,
        #)
        #MessageRecipient.objects.create(message=message, recipient=recipient)

        # --- ایجاد نوتیفیکیشن ---
        #Notification.objects.create(
         #   recipient=recipient,
          #  sender=notification_sender,
           # message=body,
            #link=request_link,
            #otification_type=notification_type
        #)
        # --- ارسال پوش نوتیفیکیشن موبایل ---
        #send_mobile_push_notification(
         #   user=recipient,
          #  title=subject,
           # body=body,
            #data={'drug_request_id': instance.pk, 'type': notification_type}
        #)