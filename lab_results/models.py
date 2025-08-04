# lab_results/models.py

from django.db import models
from django.contrib.auth.models import User
from core.models import Patient  # <-- فقط از اپلیکیشن core ایمپورت می‌شود

# === مدل‌های مرتبط با معاینات و نتایج ===

class PeriodicExamination(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='periodic_examinations', verbose_name="بیمار")
    exam_date = models.DateField(verbose_name="تاریخ معاینه")
    admission_date = models.DateField(null=True, blank=True, verbose_name="تاریخ پذیرش")
    overall_notes = models.TextField(null=True, blank=True, verbose_name="علائم و توضیحات کلی")
    final_opinion_text = models.CharField(max_length=255, null=True, blank=True, verbose_name="متن نظریه نهایی")
    final_opinion_conditions = models.TextField(null=True, blank=True, verbose_name="شروط نظریه نهایی")
    final_opinion_date = models.DateField(null=True, blank=True, verbose_name="تاریخ نظر نهایی")
    final_opinion_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_examinations', verbose_name="پزشک نظر نهایی")
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ثبت کننده")

    class Meta:
        verbose_name = "معاینه دوره‌ای"
        verbose_name_plural = "معاینات دوره‌ای"
        unique_together = ('patient', 'exam_date') # جلوگیری از ثبت معاینه تکراری برای یک فرد در یک روز

    def __str__(self):
        return f"معاینه {self.patient} در تاریخ {self.exam_date}"

class ClinicalMeasurement(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, related_name='clinical_measurements', verbose_name="معاینه دوره‌ای")
    weight = models.FloatField(null=True, blank=True, verbose_name="وزن (kg)")
    height = models.FloatField(null=True, blank=True, verbose_name="قد (cm)")
    bmi = models.FloatField(null=True, blank=True, verbose_name="BMI")
    systolic_bp = models.PositiveIntegerField(null=True, blank=True, verbose_name="فشار خون سیستولیک")
    diastolic_bp = models.PositiveIntegerField(null=True, blank=True, verbose_name="فشار خون دیاستولیک")
    pulse = models.PositiveIntegerField(null=True, blank=True, verbose_name="نبض")

    class Meta:
        verbose_name = "اندازه‌گیری بالینی"
        verbose_name_plural = "اندازه‌گیری‌های بالینی"

class TestType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام تست")
    
    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "نوع تست"
        verbose_name_plural = "انواع تست"

class LabParameterResult(models.Model):
    periodic_exam = models.ForeignKey(PeriodicExamination, on_delete=models.CASCADE, related_name='lab_results', verbose_name="معاینه دوره‌ای")
    test_type = models.ForeignKey(TestType, on_delete=models.CASCADE, verbose_name="نوع تست")
    result_value = models.CharField(max_length=100, verbose_name="مقدار نتیجه")
    
    class Meta:
        verbose_name = "نتیجه پارامتر آزمایشگاهی"
        verbose_name_plural = "نتایج پارامترهای آزمایشگاهی"
        unique_together = ('periodic_exam', 'test_type')

EXAMINATION_SECTION_CHOICES = [
    ('general', 'عمومی'), ('eye', 'چشم'), ('skin_hair_nails', 'پوست، مو و ناخن'),
    ('ent', 'گوش، حلق، بینی و دهان'), ('head_neck', 'سر و گردن'), ('lung', 'ریه'),
    ('cardiovascular', 'قلب و عروق'), ('abdomen_pelvis', 'شکم و لگن'),
    ('urinary_genital', 'کلیه و مجاری ادراری، تناسلی'), ('musculoskeletal', 'اسکلتی و عضلانی'),
    ('nervous_system', 'سیستم عصبی'), ('psychiatric', 'اعصاب و روان'), ('undefined', 'نامشخص'),
]

class ExaminationDetail(models.Model):
    periodic_exam = models.ForeignKey(PeriodicExamination, on_delete=models.CASCADE, related_name='details', verbose_name="معاینه دوره‌ای")
    section = models.CharField(max_length=50, choices=EXAMINATION_SECTION_CHOICES, verbose_name="بخش معاینه")
    sign = models.CharField(max_length=255, null=True, blank=True, verbose_name="Sign")
    symptom = models.CharField(max_length=255, null=True, blank=True, verbose_name="Symptom")
    notes = models.TextField(null=True, blank=True, verbose_name="توضیحات")

    class Meta:
        verbose_name = "جزئیات معاینه"
        verbose_name_plural = "جزئیات معاینات"
        unique_together = ('periodic_exam', 'section')

# مدل‌های تخصصی
class OptometryResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, related_name='optometry_result')
    va_distant_r_uncorrected = models.CharField(max_length=20, null=True, blank=True)
    va_distant_l_uncorrected = models.CharField(max_length=20, null=True, blank=True)
    va_distant_ou_uncorrected = models.CharField(max_length=20, null=True, blank=True)
    va_distant_r_corrected = models.CharField(max_length=20, null=True, blank=True)
    va_distant_l_corrected = models.CharField(max_length=20, null=True, blank=True)
    va_distant_ou_corrected = models.CharField(max_length=20, null=True, blank=True)
    color_vision_r = models.CharField(max_length=50, null=True, blank=True)
    color_vision_l = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    va_distant_fc_r = models.CharField(max_length=20, null=True, blank=True)
    va_distant_fc_l = models.CharField(max_length=20, null=True, blank=True)
    va_distant_fc_ou = models.CharField(max_length=20, null=True, blank=True)
    va_distant_hm_r = models.CharField(max_length=20, null=True, blank=True)
    va_distant_hm_l = models.CharField(max_length=20, null=True, blank=True)
    va_distant_hm_ou = models.CharField(max_length=20, null=True, blank=True)
    va_distant_lp_r = models.CharField(max_length=20, null=True, blank=True)
    va_distant_lp_l = models.CharField(max_length=20, null=True, blank=True)
    va_distant_lp_ou = models.CharField(max_length=20, null=True, blank=True)
    color_vision_field_r = models.CharField(max_length=50, null=True, blank=True)
    color_vision_field_l = models.CharField(max_length=50, null=True, blank=True)
    color_vision_test_type = models.CharField(max_length=100, null=True, blank=True)
    visual_field_r = models.CharField(max_length=100, null=True, blank=True)
    visual_field_l = models.CharField(max_length=100, null=True, blank=True)
    visual_field_test_type = models.CharField(max_length=100, null=True, blank=True)
    depth_perception = models.PositiveIntegerField(null=True, blank=True)
    uses_glasses = models.BooleanField(null=True, blank=True)
    uses_contact_lens = models.BooleanField(null=True, blank=True)
    
class AudiometryResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, related_name='audiometry_result')
    right_result = models.CharField(max_length=100, null=True, blank=True, verbose_name="نتیجه گوش راست")
    left_result = models.CharField(max_length=100, null=True, blank=True, verbose_name="نتیجه گوش چپ")
    # فیلدهای مربوط به فرکانس‌های شنوایی‌سنجی از IntegerField به CharField تغییر یافتند
    right_ac_125 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_250 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_500 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_1000 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_2000 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_3000 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_4000 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_6000 = models.CharField(max_length=10, null=True, blank=True)
    right_ac_8000 = models.CharField(max_length=10, null=True, blank=True)
    right_bc_500 = models.CharField(max_length=10, null=True, blank=True)
    right_bc_1000 = models.CharField(max_length=10, null=True, blank=True)
    right_bc_2000 = models.CharField(max_length=10, null=True, blank=True)
    right_bc_3000 = models.CharField(max_length=10, null=True, blank=True)
    right_bc_4000 = models.CharField(max_length=10, null=True, blank=True)
    left_ac_500 = models.CharField(max_length=10, null=True, blank=True)
    left_ac_1000 = models.CharField(max_length=10, null=True, blank=True)
    left_ac_2000 = models.CharField(max_length=10, null=True, blank=True)
    left_ac_3000 = models.CharField(max_length=10, null=True, blank=True)
    left_ac_4000 = models.CharField(max_length=10, null=True, blank=True)
    left_ac_6000 = models.CharField(max_length=10, null=True, blank=True)
    left_ac_8000 = models.CharField(max_length=10, null=True, blank=True)
    left_bc_500 = models.CharField(max_length=10, null=True, blank=True)
    left_bc_1000 = models.CharField(max_length=10, null=True, blank=True)
    left_bc_2000 = models.CharField(max_length=10, null=True, blank=True)
    left_bc_3000 = models.CharField(max_length=10, null=True, blank=True)
    left_bc_4000 = models.CharField(max_length=10, null=True, blank=True)
    right_result_other = models.CharField(max_length=100, null=True, blank=True)
    left_result_other = models.CharField(max_length=100, null=True, blank=True)

class SpirometryResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, related_name='spirometry_result')
    result = models.CharField(max_length=100, null=True, blank=True, verbose_name="نتیجه")
    result_other = models.CharField(max_length=255, null=True, blank=True)

class ECGResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, related_name='ecg_result')
    diagnoses = models.TextField(null=True, blank=True, verbose_name="تشخیص‌ها")
    
class SonographyResult(models.Model):
    periodic_exam = models.OneToOneField(PeriodicExamination, on_delete=models.CASCADE, related_name='sonography_result')
    result = models.TextField(null=True, blank=True, verbose_name="نتیجه")