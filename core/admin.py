

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Company, Patient
from .forms import PatientForm
from django import forms
from django.db import models
from jalali_date.admin import ModelAdminJalaliMixin 
import jalali_date.admin as jdatetime

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'is_active')
    search_fields = ('name', 'phone', 'email')
    list_filter = ('is_active',)

# برای مدل Patient
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'personnel_number', 'national_code', 'passport_number',
        'phone_number', 'gender', 'company', 'is_approved', 'registered_at' # 👈 is_approved رو اضافه کن
    )
    list_filter = ('gender', 'blood_type', 'insurance_type', 'company', 'is_foreign_national', 'is_approved') # 👈 is_approved رو اضافه کن
    search_fields = ('first_name', 'last_name', 'national_code', 'passport_number', 'personnel_number', 'phone_number')
    raw_id_fields = ('company', 'registered_by') # برای انتخاب راحت‌تر ForeignKey‌ها
    date_hierarchy = 'registered_at'
    readonly_fields = ('registered_at', 'registered_by', 'age') # age که property هست
    
    # 👈👈👈 فیلدهایی که در فرم ادمین نمایش داده می‌شوند
    fieldsets = (
        (None, {'fields': ('first_name', 'last_name', 'gender', 'phone_number', 'date_of_birth', 'profile_picture')}),
        ('اطلاعات هویتی', {'fields': ('is_foreign_national', 'national_code', 'passport_number', 'personnel_number')}),
        ('اطلاعات پزشکی', {'fields': ('blood_type', 'insurance_type', 'allergies', 'medical_history', 'last_periodic_examination_date', 'is_monitored')}),
        ('اطلاعات سازمانی', {'fields': ('company', 'occupation', 'address')}),
        ('وضعیت سیستم', {'fields': ('is_approved', 'registered_by')}), # 👈 is_approved اینجا قابل ویرایش است
    )