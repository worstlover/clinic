# D:\final\lab_results\models.py
from django.db import models
from django.contrib.auth.models import User
from datetime import date
import jdatetime # برای تبدیل تاریخ شمسی (اگر نیاز به ورودی شمسی دارید)

# فرض می‌کنیم مدل Patient در اپلیکیشن 'core' قرار دارد
# حتماً باید این خط را اضافه کنید تا مدل Patient قابل دسترسی باشد
from core.models import Patient 


# --- مدل‌های پایه و دسته‌بندی کننده ---

# 1. مدل گزارش معاینه دوره‌ای (PeriodicExamination)
# این مدل به عنوان والد اصلی برای تمام نتایج معاینات و آزمایشات در یک تاریخ مشخص برای یک بیمار عمل می‌کند.
class PeriodicExamination(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name="بیمار")
    exam_date = models.DateField(verbose_name="تاریخ معاینه دوره‌ای")
    
    # فیلدهای عمومی که در تصاویر قبلی بودند و به یک گزارش کلی مربوط می‌شوند
    admission_date = models.DateField(blank=True, null=True, verbose_name="تاریخ پذیرش") # از تصاویر اکسل شما
    final_opinion_conditions = models.TextField(blank=True, null=True, verbose_name="نظریه نهایی - شرایط") # از تصاویر اکسل شما
    final_opinion_date = models.DateField(blank=True, null=True, verbose_name="نظریه نهایی - تاریخ صدور") # از تصاویر اکسل شما
    final_opinion_doctor = models.CharField(max_length=200, blank=True, null=True, verbose_name="نظریه نهایی - نام پزشک") # از تصاویر اکسل شما
    overall_notes = models.TextField(blank=True, null=True, verbose_name="علائم و توضیحات ثبت شده کلی") # از لیست شما

    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت در سیستم")
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ثبت کننده")

    class Meta:
        verbose_name = "معاینه دوره‌ای"
        verbose_name_plural = "معاینات دوره‌ای"
        unique_together = ('patient', 'exam_date') # هر بیمار در یک تاریخ فقط یک معاینه دوره‌ای دارد
        ordering = ['-exam_date'] # جدیدترین‌ها اول نمایش داده شوند

    def __str__(self):
        return f"معاینه دوره‌ای {self.patient.full_name} در {self.exam_date}"


# 2. مدل نوع آزمایش/پارامتر (TestType)
# برای تعریف انواع مختلف آزمایش‌ها یا پارامترها (مثل هموگلوبین، وزن، قد، FBS و غیره)
class TestType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام پارامتر/آزمایش")
    unit = models.CharField(max_length=50, blank=True, null=True, verbose_name="واحد اندازه‌گیری")
    normal_range_min = models.FloatField(blank=True, null=True, verbose_name="حد نرمال حداقل")
    normal_range_max = models.FloatField(blank=True, null=True, verbose_name="حد نرمال حداکثر")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    class Meta:
        verbose_name = "نوع پارامتر/آزمایش"
        verbose_name_plural = "انواع پارامتر/آزمایشات"

    def __str__(self):
        return self.name


# --- مدل‌های اندازه‌گیری‌ها و نتایج آزمایشات ---

# 3. مدل اندازه‌گیری‌های بالینی (ClinicalMeasurement)
# این مدل شامل وزن، قد، فشارخون و نبض است.
class ClinicalMeasurement(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, verbose_name="معاینه دوره‌ای", primary_key=True)
    # هر معاینه دوره‌ای فقط یک مجموعه اندازه‌گیری بالینی دارد.

    weight = models.FloatField(blank=True, null=True, verbose_name="وزن (کیلوگرم)")
    height = models.FloatField(blank=True, null=True, verbose_name="قد (سانتی‌متر)")
    bmi = models.FloatField(blank=True, null=True, verbose_name="BMI")
    systolic_bp = models.IntegerField(blank=True, null=True, verbose_name="فشارخون سیستولیک")
    diastolic_bp = models.IntegerField(blank=True, null=True, verbose_name="فشارخون دیاستولیک")
    pulse = models.IntegerField(blank=True, null=True, verbose_name="نبض")

    class Meta:
        verbose_name = "اندازه‌گیری بالینی"
        verbose_name_plural = "اندازه‌گیری‌های بالینی"

    def __str__(self):
        return f"اندازه‌گیری‌های بالینی برای {self.periodic_exam.patient.full_name} در {self.periodic_exam.exam_date}"


# 4. مدل جزئیات آزمایشگاهی/پارامترهای عمومی (LabParameterResult)
# این مدل برای ذخیره نتایج آزمایشگاهی مانند Lipid Panel, FBS, Creat, AST, ALT, CBC و Thyroid Function
# و همچنین می‌تواند برای سایر پارامترهای عمومی "Key-Value" که در TestType تعریف شده‌اند، استفاده شود.
class LabParameterResult(models.Model):
    periodic_exam = models.ForeignKey(PeriodicExamination, on_delete=models.CASCADE, related_name='lab_parameters', verbose_name="معاینه دوره‌ای")
    test_type = models.ForeignKey(TestType, on_delete=models.CASCADE, verbose_name="نوع پارامتر آزمایش") # مثلاً TestType با نام "Chol - Lipid Panel"
    result_value = models.CharField(max_length=255, verbose_name="مقدار نتیجه")

    class Meta:
        verbose_name = "نتیجه پارامتر آزمایشگاهی"
        verbose_name_plural = "نتایج پارامترهای آزمایشگاهی"
        unique_together = ('periodic_exam', 'test_type') # هر نوع پارامتر فقط یک بار در یک معاینه دوره‌ای ثبت می‌شود

    def __str__(self):
        return f"{self.periodic_exam.patient.full_name} - {self.test_type.name}: {self.result_value}"


# --- مدل‌های معاینات پزشکی ---

# تعریف بخش‌های معاینه برای Choices
EXAMINATION_SECTION_CHOICES = [
    ('general', 'عمومی'),
    ('eye', 'چشم'),
    ('skin_hair_nails', 'پوست، مو و ناخن'),
    ('ent', 'گوش، حلق، بینی و دهان'),
    ('head_neck', 'سر و گردن'),
    ('lung', 'ریه'),
    ('cardiovascular', 'قلب و عروق'),
    ('abdomen_pelvis', 'شکم و لگن'),
    ('urinary_genital', 'کلیه و مجاری ادراری، تناسلی'),
    ('musculoskeletal', 'اسکلتی و عضلانی'),
    ('nervous_system', 'سیستم عصبی'),
    ('psychiatric', 'اعصاب و روان'),
    ('undefined', 'نامشخص'), # برای 'معاینات - undefined'
]

# 5. مدل جزئیات معاینه (ExaminationDetail)
# این مدل هر Sign, Symptom و توضیحات را برای یک بخش خاص از معاینه نگهداری می‌کند.
class ExaminationDetail(models.Model):
    periodic_exam = models.ForeignKey(PeriodicExamination, on_delete=models.CASCADE, related_name='examination_details', verbose_name="معاینه دوره‌ای")
    section = models.CharField(max_length=50, choices=EXAMINATION_SECTION_CHOICES, verbose_name="بخش معاینه")
    sign = models.TextField(blank=True, null=True, verbose_name="Sign")
    symptom = models.TextField(blank=True, null=True, verbose_name="Symptom")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    class Meta:
        verbose_name = "جزئیات معاینه"
        verbose_name_plural = "جزئیات معاینات"
        unique_together = ('periodic_exam', 'section') # هر بخش در یک معاینه دوره‌ای فقط یک بار
        # اگر یک بخش می‌تواند چندین Sign/Symptom/توضیح داشته باشد، unique_together را حذف کنید.

    def __str__(self):
        return f"{self.get_section_display()} برای {self.periodic_exam.patient.full_name} در {self.periodic_exam.exam_date}"


# --- مدل‌های معاینات تخصصی ---

# 6. مدل نتیجه اپتومتری (OptometryResult)
class OptometryResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, verbose_name="معاینه دوره‌ای", primary_key=True)

    # حدت بینایی - دید دور - بدون اصلاح
    va_distant_r_uncorrected = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - R - بدون اصلاح")
    va_distant_l_uncorrected = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - L - بدون اصلاح")
    va_distant_ou_uncorrected = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - دوچشمی - بدون اصلاح")

    # حدت بینایی - دید دور - با اصلاح
    va_distant_r_corrected = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - R - با اصلاح")
    va_distant_l_corrected = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - L - با اصلاح")
    va_distant_ou_corrected = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - دوچشمی - با اصلاح")

    # حدت بینایی - دید دور - FC, HM, LP
    va_distant_fc_r = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - FC - R")
    va_distant_fc_l = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - FC - L")
    va_distant_fc_ou = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - FC - دوچشمی")

    va_distant_hm_r = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - HM - R")
    va_distant_hm_l = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - HM - L")
    va_distant_hm_ou = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - HM - دوچشمی")

    va_distant_lp_r = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - LP - R")
    va_distant_lp_l = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - LP - L")
    va_distant_lp_ou = models.CharField(max_length=50, blank=True, null=True, verbose_name="حدت بینایی - دید دور - LP - دوچشمی")

    # دید رنگی
    color_vision_r = models.CharField(max_length=100, blank=True, null=True, verbose_name="دید رنگی - R")
    color_vision_l = models.CharField(max_length=100, blank=True, null=True, verbose_name="دید رنگی - L")
    color_vision_field_r = models.CharField(max_length=100, blank=True, null=True, verbose_name="دید رنگی - Field Test - R")
    color_vision_field_l = models.CharField(max_length=100, blank=True, null=True, verbose_name="دید رنگی - Field Test - L")
    color_vision_test_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="دید رنگی - Test Type")

    # میدان بینایی
    visual_field_r = models.CharField(max_length=100, blank=True, null=True, verbose_name="میدان بینایی - R")
    visual_field_l = models.CharField(max_length=100, blank=True, null=True, verbose_name="میدان بینایی - L")
    visual_field_test_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="میدان بینایی - Test Type")

    # سایر
    depth_perception = models.FloatField(blank=True, null=True, verbose_name="عمق دید (ثانیه آرک)")
    uses_glasses = models.BooleanField(default=False, verbose_name="استفاده از عینک")
    uses_contact_lens = models.BooleanField(default=False, verbose_name="استفاده از لنز طبی")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات اپتومتری")

    class Meta:
        verbose_name = "نتیجه اپتومتری"
        verbose_name_plural = "نتایج اپتومتری"

    def __str__(self):
        return f"اپتومتری {self.periodic_exam.patient.full_name} در {self.periodic_exam.exam_date}"


# 7. مدل نتیجه اودیومتری (AudiometryResult)
class AudiometryResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, verbose_name="معاینه دوره‌ای", primary_key=True)

    # Right Ear - Air Conduction (AC)
    right_ac_125 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 125")
    right_ac_250 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 250")
    right_ac_500 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 500")
    right_ac_1000 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 1000")
    right_ac_2000 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 2000")
    right_ac_3000 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 3000")
    right_ac_4000 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 4000")
    right_ac_6000 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 6000")
    right_ac_8000 = models.IntegerField(blank=True, null=True, verbose_name="Right AC 8000")

    # Right Ear - Bone Conduction (BC)
    right_bc_500 = models.IntegerField(blank=True, null=True, verbose_name="Right BC 500")
    right_bc_1000 = models.IntegerField(blank=True, null=True, verbose_name="Right BC 1000")
    right_bc_2000 = models.IntegerField(blank=True, null=True, verbose_name="Right BC 2000")
    right_bc_3000 = models.IntegerField(blank=True, null=True, verbose_name="Right BC 3000")
    right_bc_4000 = models.IntegerField(blank=True, null=True, verbose_name="Right BC 4000")

    # Left Ear - Air Conduction (AC)
    left_ac_500 = models.IntegerField(blank=True, null=True, verbose_name="Left AC 500")
    left_ac_1000 = models.IntegerField(blank=True, null=True, verbose_name="Left AC 1000")
    left_ac_2000 = models.IntegerField(blank=True, null=True, verbose_name="Left AC 2000")
    left_ac_3000 = models.IntegerField(blank=True, null=True, verbose_name="Left AC 3000")
    left_ac_4000 = models.IntegerField(blank=True, null=True, verbose_name="Left AC 4000")
    left_ac_6000 = models.IntegerField(blank=True, null=True, verbose_name="Left AC 6000")
    left_ac_8000 = models.IntegerField(blank=True, null=True, verbose_name="Left AC 8000")

    # Left Ear - Bone Conduction (BC)
    left_bc_500 = models.IntegerField(blank=True, null=True, verbose_name="Left BC 500")
    left_bc_1000 = models.IntegerField(blank=True, null=True, verbose_name="Left BC 1000")
    left_bc_2000 = models.IntegerField(blank=True, null=True, verbose_name="Left BC 2000")
    left_bc_3000 = models.IntegerField(blank=True, null=True, verbose_name="Left BC 3000")
    left_bc_4000 = models.IntegerField(blank=True, null=True, verbose_name="Left BC 4000")

    # Results
    right_result = models.CharField(max_length=255, blank=True, null=True, verbose_name="Right Result")
    left_result = models.CharField(max_length=255, blank=True, null=True, verbose_name="Left Result")
    right_result_other = models.TextField(blank=True, null=True, verbose_name="Right Result Other")
    left_result_other = models.TextField(blank=True, null=True, verbose_name="Left Result Other")

    class Meta:
        verbose_name = "نتیجه اودیومتری"
        verbose_name_plural = "نتایج اودیومتری"

    def __str__(self):
        return f"اودیومتری {self.periodic_exam.patient.full_name} در {self.periodic_exam.exam_date}"


# 8. مدل نتیجه اسپیرومتری (SpirometryResult)
class SpirometryResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, verbose_name="معاینه دوره‌ای", primary_key=True)

    result = models.TextField(blank=True, null=True, verbose_name="Result")
    result_other = models.TextField(blank=True, null=True, verbose_name="Result Other")

    class Meta:
        verbose_name = "نتیجه اسپیرومتری"
        verbose_name_plural = "نتایج اسپیرومتری"

    def __str__(self):
        return f"اسپیرومتری {self.periodic_exam.patient.full_name} در {self.periodic_exam.exam_date}"


# 9. مدل نتیجه ECG (ECGResult)
class ECGResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, verbose_name="معاینه دوره‌ای", primary_key=True)

    diagnoses = models.TextField(blank=True, null=True, verbose_name="Diagnoses")

    class Meta:
        verbose_name = "نتیجه ECG"
        verbose_name_plural = "نتایج ECG"

    def __str__(self):
        return f"ECG برای {self.periodic_exam.patient.full_name} در {self.periodic_exam.exam_date}"


# 10. مدل نتیجه سونوگرافی (SonographyResult)
class SonographyResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, verbose_name="معاینه دوره‌ای", primary_key=True)

    result = models.TextField(blank=True, null=True, verbose_name="نتیجه سونوگرافی") # فیلدی که شما اشاره کردید

    class Meta:
        verbose_name = "نتیجه سونوگرافی"
        verbose_name_plural = "نتایج سونوگرافی"

    def __str__(self):
        return f"سونوگرافی برای {self.periodic_exam.patient.full_name} در {self.periodic_exam.exam_date}"