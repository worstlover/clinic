# lab_results/admin.py
from django.contrib import admin
# نیازی به import کردن Patient از core نیست، چون آنجا ثبت شده است
# from core.models import Patient # این خط را هم می‌توانید حذف کنید اگر فقط Patient را import کرده بودید

from .models import (
    PeriodicExamination, ClinicalMeasurement, TestType, LabParameterResult, 
    ExaminationDetail, OptometryResult, AudiometryResult, SpirometryResult, 
    ECGResult, SonographyResult
)

# مدل Patient اینجا ثبت نمی‌شود، چون در core/admin.py ثبت شده است

# ثبت مدل PeriodicExamination در پنل ادمین
@admin.register(PeriodicExamination)
class PeriodicExaminationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'exam_date', 'admission_date', 'final_opinion_conditions')
    search_fields = ('patient__national_code', 'patient__first_name', 'patient__last_name')
    list_filter = ('exam_date',)
    raw_id_fields = ('patient',) 

# ثبت سایر مدل‌ها:
@admin.register(ClinicalMeasurement)
class ClinicalMeasurementAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'weight', 'height', 'bmi')
    raw_id_fields = ('periodic_exam',)

@admin.register(LabParameterResult)
class LabParameterResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'test_type', 'result_value')
    list_filter = ('test_type',)
    raw_id_fields = ('periodic_exam', 'test_type',)

@admin.register(ExaminationDetail)
class ExaminationDetailAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'section', 'sign', 'symptom')
    list_filter = ('section',)
    raw_id_fields = ('periodic_exam',)

# و سایر مدل‌ها را که در lab_results/models.py تعریف کرده‌اید، اینجا ثبت کنید:
@admin.register(OptometryResult)
class OptometryResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'va_distant_r_uncorrected', 'va_distant_l_uncorrected')
    raw_id_fields = ('periodic_exam',)

@admin.register(AudiometryResult)
class AudiometryResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'right_ac_500', 'left_ac_500')
    raw_id_fields = ('periodic_exam',)

@admin.register(SpirometryResult)
class SpirometryResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'result')
    raw_id_fields = ('periodic_exam',)

@admin.register(ECGResult)
class ECGResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'diagnoses')
    raw_id_fields = ('periodic_exam',)

@admin.register(SonographyResult)
class SonographyResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'result')
    raw_id_fields = ('periodic_exam',)

@admin.register(TestType)
class TestTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)