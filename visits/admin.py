# visits/admin.py - REVISED

from django.contrib import admin
from .models import Visit, VisitItem, ReasonForVisit, TreatmentResult
from jalali_date.admin import ModelAdminJalaliMixin

# ثبت مدل‌های جدید
@admin.register(ReasonForVisit)
class ReasonForVisitAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(TreatmentResult)
class TreatmentResultAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


class VisitItemInline(admin.TabularInline):
    model = VisitItem
    extra = 1
    raw_id_fields = ['drug']

@admin.register(Visit)
class VisitAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = [
        'patient',
        'visit_date',
        'reason_for_visit', # فیلد جدید
        'incident_type',    # فیلد جدید
        'doctor',
        'status',           # نمایش وضعیت
    ]
    list_filter = [
        'visit_date',
        'status',
        'incident_type',
        'reason_for_visit',
        'treatment_result',
        'doctor',
    ]
    search_fields = [
        'patient__first_name',
        'patient__last_name',
        'patient__national_code',
        'notes',
    ]
    date_hierarchy = 'visit_date'
    ordering = ['-visit_date']
    
    # استفاده از raw_id_fields برای بهبود عملکرد انتخاب بیمار
    raw_id_fields = ['patient', 'doctor', 'assigned_to']

    fieldsets = (
        ("اطلاعات اصلی", {
            'fields': ('patient', 'visit_date', 'doctor', 'assigned_to', 'status')
        }),
        ("جزئیات پزشکی", {
            'fields': (
                'reason_for_visit',
                'incident_type',
                ('height_cm', 'weight_kg'),
                ('blood_pressure', 'heart_rate', 'temperature'),
                'treatment_result',
            )
        }),
        ("یادداشت‌ها", {
            'fields': ('notes',)
        }),
    )

    inlines = [VisitItemInline]

    def save_model(self, request, obj, form, change):
        if not obj.doctor:
            obj.doctor = request.user
        if not obj.assigned_to: # اگر مسئول مشخص نشده بود، خود کاربر ثبت کننده می‌شود
             obj.assigned_to = request.user
        super().save_model(request, obj, form, change)