from django.db import models
from django.contrib.auth.models import User
from datetime import date # اضافه شده برای محاسبه سن
import jdatetime # این برای کار با تاریخ جلالی است، اگرچه مستقیماً در مدل استفاده نمی‌شود ولی ممکن است در جاهای دیگر پروژه کاربرد داشته باشد
from django.db.models import Sum # اگر در مدل استفاده نمی‌شود، می‌توان حذف کرد
from django.utils import timezone # اگر در مدل استفاده نمی‌شود، می‌توان حذف کرد
from django.db.models import Max # اگر در مدل استفاده نمی‌شود، می‌توان حذف کرد
from django.db import models
from django.contrib.auth import get_user_model
# --------------------------------------------------
# 0. تعریف Choices های سراسری (قبل از مدل‌ها)
# --------------------------------------------------

GENDER_CHOICES = [
    ('M', 'مرد'),
    ('F', 'زن'),
    # ('O', 'سایر'), # اگر نیاز دارید، می‌توانید این را اضافه کنید
]

BLOOD_TYPE_CHOICES = [
    ('A+', 'A+'), ('A-', 'A-'),
    ('B+', 'B+'), ('B-', 'B-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
    ('O+', 'O+'), ('O-', 'O-'),
]

INSURANCE_TYPE_CHOICES = [
    ('social_security', 'تامین اجتماعی'),
    ('health_services', 'خدمات درمانی'),
    ('armed_forces', 'نیروهای مسلح'),
    ('other', 'سایر'),
    ('none', 'ندارد'),
]

# --------------------------------------------------
# 1. مدل شرکت (Company)
# --------------------------------------------------

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="نام شرکت/مجموعه")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="تلفن")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="ایمیل")
    address = models.TextField(blank=True, null=True, verbose_name="آدرس")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    description = models.CharField(max_length=300, blank=True, null=True, verbose_name="توضیحات")

    class Meta:
        verbose_name = "شرکت/مجموعه"
        verbose_name_plural = "شرکت‌ها/مجموعه‌ها"
        ordering = ['name'] # مرتب سازی بر اساس نام

    def __str__(self):
        return self.name

# --------------------------------------------------
# 2. مدل بیمار (Patient)
# --------------------------------------------------

class Patient(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="نام")
    last_name = models.CharField(max_length=100, verbose_name="نام خانوادگی")
    national_code = models.CharField(
        max_length=10, 
        unique=True, 
        blank=True, 
        null=True, 
        verbose_name="کد ملی",
        help_text="در صورت اتباع خارجی نبودن، کد ملی اجباری است."
    )
    passport_number = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        null=True, 
        verbose_name="شماره پاسپورت",
        help_text="برای اتباع خارجی"
    )
    is_foreign_national = models.BooleanField(default=False, verbose_name="تبعه خارجی")
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="شماره موبایل")
    
    # فیلد تاریخ تولد (میلادی)
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="تاریخ تولد")
    father_name = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="جنسیت")
    
    blood_type = models.CharField(
        max_length=3, 
        choices=BLOOD_TYPE_CHOICES, 
        blank=True, 
        null=True, 
        default="-", 
        verbose_name="گروه خونی"
    )
    insurance_type = models.CharField(
        max_length=20, 
        choices=INSURANCE_TYPE_CHOICES, 
        blank=True, 
        null=True, 
        default='none', 
        verbose_name="نوع بیمه"
    )
    company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="شرکت/مجموعه"
    )

    address = models.TextField(blank=True, null=True, verbose_name="آدرس")
    registered_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    registered_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="ثبت کننده"
    )
    profile_picture = models.ImageField(
        upload_to='patient_pics/', 
        blank=True, 
        null=True, 
        verbose_name="عکس پروفایل"
    )
    allergies = models.CharField(max_length=255, blank=True, verbose_name="حساسیت‌ها") # طول بیشتر برای حساسیت‌ها
    medical_history = models.TextField(blank=True, verbose_name="سوابق پزشکی") # Textarea مناسب‌تر است
    occupation = models.CharField(max_length=100, blank=True, null=True, verbose_name="شغل") # طول بیشتر برای شغل
    last_periodic_examination_date = models.DateField(
        blank=True, 
        null=True, 
        verbose_name="آخرین معاینه دوره‌ای"
    )
    personnel_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="کد پرسنلی") # IntegerField برای کدهای پرسنلی با حروف مشکل ساز می‌شود
    is_approved = models.BooleanField(default=False, verbose_name="تایید شده") 
    is_monitored = models.BooleanField(default=False, verbose_name="نیازمند پایش")

    class Meta:
        verbose_name = "بیمار"
        verbose_name_plural = "بیماران"
        # Ensure that national_code and passport_number are conditionally unique
        # unique_together = ('first_name', 'last_name', 'national_code') # این unique_together ممکن است مشکل ساز شود اگر ملی‌کد یا پاسپورت null باشد
        # بهتر است اعتبارسنجی unique بودن را در clean متد فرم انجام دهید.
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''}"
    
    
    def get_full_name(self):
        """
        برمی‌گرداند نام کامل بیمار (نام و نام خانوادگی).
        """
        # اگر نام خانوادگی وجود دارد، نام کامل را با نام خانوادگی برمی‌گرداند
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        # در غیر این صورت، فقط نام را برمی‌گرداند
        return self.first_name
    @property
    def full_name_and_identifiers(self):
        """
        این پراپرتی برای نمایش در Select2 استفاده می‌شود.
        """
        identifiers = []
        if self.national_code:
            identifiers.append(f"کد ملی: {self.national_code}")
        if self.personnel_number:
            identifiers.append(f"شماره پرسنلی: {self.personnel_number}")
        
        if identifiers:
            return f"{self.first_name} {self.last_name} ({', '.join(identifiers)})"
        return f"{self.first_name} {self.last_name}"
    @property
    def full_name(self):
        """
        Returns the full name of the patient.
        """
        return f"{self.first_name or ''} {self.last_name or ''}"

    @property
    def age(self):
        """
        Calculates the current age of the patient based on their date of birth.
        This age is calculated dynamically and is NOT stored in the database.
        """
        if self.date_of_birth:
            today = date.today()
            age_years = today.year - self.date_of_birth.year
            # اگر هنوز روز تولد در سال جاری نرسیده باشد، یک سال از سن کم کن
            if today.month < self.date_of_birth.month or \
               (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
                age_years -= 1
            return age_years
        return None # اگر تاریخ تولد ثبت نشده باشد، None برمی‌گرداند

User = get_user_model()

def profile_image_upload_path(instance, filename):
    return f'profile_images/{instance.user.username}/{filename}'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.png', upload_to=profile_image_upload_path)

    def __str__(self):
        return f'{self.user.username} Profile'