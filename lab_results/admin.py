from django.contrib import admin
from .models import (
    PeriodicExamination, ClinicalMeasurement, TestType, LabParameterResult, 
    ExaminationDetail, OptometryResult, AudiometryResult, SpirometryResult, 
    ECGResult, SonographyResult
)
from django.utils.html import format_html

@admin.register(PeriodicExamination)
class PeriodicExaminationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'exam_date', 'final_opinion_text', 'final_opinion_date', 'recorded_by')
    list_filter = ('exam_date', 'final_opinion_text')
    search_fields = ('patient__full_name', 'patient__national_code', 'final_opinion_text')
    autocomplete_fields = ('patient', 'final_opinion_doctor', 'recorded_by')

@admin.register(ClinicalMeasurement)
class ClinicalMeasurementAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'weight', 'height', 'bmi', 'systolic_bp', 'diastolic_bp')
    search_fields = ('periodic_exam__patient__full_name',)

@admin.register(TestType)
class TestTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(LabParameterResult)
class LabParameterResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'test_type', 'result_value')
    list_filter = ('test_type',)
    search_fields = ('periodic_exam__patient__full_name', 'test_type__name')
    autocomplete_fields = ('periodic_exam', 'test_type')

@admin.register(ExaminationDetail)
class ExaminationDetailAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'section', 'sign', 'symptom')
    list_filter = ('section',)
    search_fields = ('periodic_exam__patient__full_name',)

@admin.register(OptometryResult)
class OptometryResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'va_distant_r_corrected', 'va_distant_l_corrected', 'color_vision_r', 'color_vision_l')
    search_fields = ('periodic_exam__patient__full_name',)

@admin.register(AudiometryResult)
class AudiometryResultAdmin(admin.ModelAdmin):
    # --- CHANGE START: فیلدهای ناموجود حذف شدند ---
    list_display = ('periodic_exam', 'right_result', 'left_result')
    # --- CHANGE END ---
    search_fields = ('periodic_exam__patient__full_name', 'right_result', 'left_result')

@admin.register(SpirometryResult)
class SpirometryResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'result')
    search_fields = ('periodic_exam__patient__full_name', 'result')

@admin.register(ECGResult)
class ECGResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'diagnoses')
    search_fields = ('periodic_exam__patient__full_name',)

@admin.register(SonographyResult)
class SonographyResultAdmin(admin.ModelAdmin):
    list_display = ('periodic_exam', 'result')
    search_fields = ('periodic_exam__patient__full_name',)