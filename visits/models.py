# visits/models.py - REVISED

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

# فرض بر این است که این مدل‌ها موجود هستند
from core.models import Patient
from drugs.models import Drug # مطمئن شوید مسیر درست است

User = get_user_model()

# --- مدل‌های جدید برای مدیریت گزینه‌ها توسط ادمین ---

class ReasonForVisit(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="عنوان علت مراجعه")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "علت مراجعه"
        verbose_name_plural = "علل مراجعه"
        ordering = ['name']

    def __str__(self):
        return self.name

class TreatmentResult(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="عنوان نتیجه درمان")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "نتیجه درمان"
        verbose_name_plural = "نتایج درمان"
        ordering = ['name']

    def __str__(self):
        return self.name

# --- CHOICES برای فیلدهای جدید ---

INCIDENT_TYPE_CHOICES = [
    ('none', 'بدون حادثه'),
    ('near_miss', 'شبه حادثه (Near Miss)'),
    ('minor', 'حادثه جزئی (Minor)'),
    ('major', 'حادثه ماژور (Major)'),
]

VISIT_STATUS_CHOICES = [
    ('pending', 'در حال بررسی'),
    ('referred', 'ارجاع شده'),
    ('completed', 'تکمیل شده'),
]


class Visit(models.Model):
    # --- فیلدهای اصلی و ارتباطات ---
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits', verbose_name="بیمار")
    # related_name به visits_as_doctor تغییر یافت.
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="پزشک ثبت کننده", related_name='visits_as_doctor')
    visit_date = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ویزیت")
    
    # --- فیلدهای مدیریتی جدید (جایگزین choices استاتیک) ---
    # on_delete به PROTECT تغییر یافت تا حذف علت مراجعه یا نتیجه درمان را در صورت استفاده، جلوگیری کند.
    reason_for_visit = models.ForeignKey(ReasonForVisit, on_delete=models.PROTECT, verbose_name="علت مراجعه", null=True, blank=True)
    treatment_result = models.ForeignKey(TreatmentResult, on_delete=models.PROTECT, verbose_name="نتیجه درمان", null=True, blank=True)

    # --- فیلدهای جدید مربوط به حادثه ---
    incident_type = models.CharField(max_length=20, choices=INCIDENT_TYPE_CHOICES, default='none', verbose_name="نوع حادثه")
    
    # --- فیلدهای جدید برای قد، وزن و علائم حیاتی ---
    # validators اضافه شد.
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, validators=[MinValueValidator(Decimal('0.0'))], null=True, blank=True, verbose_name="قد (سانتی‌متر)")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], null=True, blank=True, verbose_name="وزن (کیلوگرم)")
    blood_pressure = models.CharField(max_length=15, blank=True, null=True, verbose_name="فشار خون (مثال: 120/80)")
    heart_rate = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="ضربان قلب (در دقیقه)")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name="دما (سانتی‌گراد)")
    
    # --- سایر فیلدها ---
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات/شرح حال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد") # verbose_name اضافه شد
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی") # verbose_name اضافه شد
    completed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="تاریخ و زمان تکمیل"
    )
    completed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, # یا models.CASCADE اگر می‌خواهید با حذف کاربر، ویزیت هم حذف شود
        null=True, 
        blank=True, 
        related_name='completed_visits', # نامی برای دسترسی معکوس
        verbose_name="تکمیل کننده"
    )
    # --- فیلدهای وضعیت و ارجاع ---
    status = models.CharField(max_length=20, choices=VISIT_STATUS_CHOICES, default='pending', verbose_name="وضعیت ویزیت")
    # related_name به assigned_visits تغییر یافت.
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="کاربر مسئول فعلی", related_name='assigned_visits')

    class Meta:
        verbose_name = "ویزیت"
        verbose_name_plural = "ویزیت‌ها"
        ordering = ['-visit_date'] # ترتیب نمایش ویزیت‌ها
        permissions = [
            ("change_visit_status", "Can change the status of visits"),
            ("refer_visit", "Can refer visits to other users"),
            ("view_visit_report", "Can view visit reports"), # دسترسی برای گزارش‌ها
        ]

    def __str__(self):
        # نمایش تاریخ ویزیت به همراه ساعت
        return f"ویزیت {self.patient.full_name} در تاریخ {self.visit_date.strftime('%Y-%m-%d %H:%M')}"

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            height_m = self.height_cm / 100
            # دقت محاسباتی را با Decimal حفظ کنید
            return (self.weight_kg / (height_m * height_m)).quantize(Decimal('0.1')) # گرد کردن به یک رقم اعشار
        return None

# مدل VisitItem بدون تغییر باقی می‌ماند
class VisitItem(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='items', verbose_name="ویزیت")
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, verbose_name="داروی تجویز شده")
    quantity = models.PositiveIntegerField(verbose_name="تعداد تجویز شده", validators=[MinValueValidator(1)]) # validator برای حداقل مقدار
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات (برای این دارو)")

    class Meta:
        verbose_name = "آیتم ویزیت"
        verbose_name_plural = "آیتم‌های ویزیت"
        unique_together = ('visit', 'drug')

    def __str__(self):
        return f"{self.quantity} عدد {self.drug.name} برای ویزیت {self.visit.pk}"