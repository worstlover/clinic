# D:\final\clinic_messages\models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from visits.models import Visit # مطمئن شوید این ایمپورت وجود دارد
from drugs.models import DrugRequest # مطمئن شوید این ایمپورت وجود دارد

User = get_user_model()

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name="فرستنده")
    subject = models.CharField(max_length=255, blank=True, null=True, verbose_name="موضوع")
    body = models.TextField(verbose_name="متن پیام")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ارسال")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده") # این فیلد ممکن است به MessageRecipient منتقل شود
    
    # فیلدهای جدید که باید به مدل Message اضافه شوند
    
    parent_message = models.ForeignKey(
        'self', # اشاره به خود مدل Message
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name="پیام والد"
    )

    MESSAGE_TYPE_CHOICES = [
        ('general', 'عمومی'),
        ('notification', 'اطلاعیه'),
        ('urgent', 'فوری'),
        ('drug_request', 'درخواست دارو'),
        ('visit_note', 'یادداشت ویزیت'),
    ]
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='general',
        verbose_name="نوع پیام"
    )


    class Meta:
        verbose_name = "پیام"
        verbose_name_plural = "پیام‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"From {self.sender.username}: {self.subject}"

    # متد برای علامت‌گذاری پیام به عنوان خوانده شده (اگر is_read در MessageRecipient مدیریت شود، این متد نیاز به اصلاح دارد)
    def mark_as_read(self, user):
        recipient_entry = MessageRecipient.objects.filter(message=self, recipient=user).first()
        if recipient_entry and not recipient_entry.is_read:
            recipient_entry.is_read = True
            recipient_entry.read_at = timezone.now()
            recipient_entry.save()

# مدل MessageRecipient برای مدیریت گیرندگان چندگانه و وضعیت خوانده شدن هر گیرنده
class MessageRecipient(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='recipients_data', verbose_name="پیام")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', verbose_name="گیرنده")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده است؟")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ خوانده شدن")

    class Meta:
        verbose_name = "گیرنده پیام"
        verbose_name_plural = "گیرندگان پیام"
        unique_together = ('message', 'recipient') # یک گیرنده فقط یک بار برای یک پیام ثبت شود
        ordering = ['-message__created_at'] # مرتب سازی بر اساس تاریخ ایجاد پیام

    def __str__(self):
        return f"پیام {self.message.subject} به {self.recipient.username} (خوانده شده: {self.is_read})"


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments', verbose_name="پیام")
    file = models.FileField(upload_to='message_attachments/', verbose_name="فایل")
    file_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="نام فایل")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")

    class Meta:
        verbose_name = "پیوست پیام"
        verbose_name_plural = "پیوست‌های پیام"

    def __str__(self):
        return self.file_name if self.file_name else self.file.name
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="گیرنده")
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications', verbose_name="فرستنده")
    message = models.TextField(verbose_name="پیام اعلان")
    
    # اگر Notification به Message مرتبط است:
    related_message = models.ForeignKey(
        'Message', # اشاره به مدل Message در همین اپ
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="پیام مرتبط"
    )
    
    # اگر Notification به Visit مرتبط است (مانند PostVisitTask):
    related_visit = models.ForeignKey(
        Visit, # نیاز به ایمپورت Visit از visits.models
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="ویزیت مرتبط"
    )

    # اگر Notification به DrugRequest مرتبط است:
    related_drug_request = models.ForeignKey(
        DrugRequest, # نیاز به ایمپورت DrugRequest از drugs.models
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="درخواست داروی مرتبط"
    )
    
    # برای تعیین نوع اعلان (مثلا: visit_followup, message, general, etc.)
    NOTIFICATION_TYPE_CHOICES = [
        ('general', 'عمومی'),
        ('message', 'پیام جدید'),
        ('visit_followup', 'پیگیری ویزیت'),
        ('drug_request_status', 'وضعیت درخواست دارو'),
        ('system', 'سیستم'),
        # ... انواع دیگر که نیاز دارید
    ]
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        default='general',
        verbose_name="نوع اعلان"
    )

    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ خوانده شدن")
    link = models.URLField(max_length=500, blank=True, null=True, verbose_name="لینک مرتبط")

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"اعلان برای {self.recipient.username}: {self.message[:50]}..."

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    