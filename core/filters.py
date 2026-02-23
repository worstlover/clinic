# core/filters.py - REVISED AND CORRECTED

import django_filters
from django import forms
from django.db.models import Q
from django.contrib.auth import get_user_model

# --- ایمپورت‌های بهینه شده از اپ‌های مختلف ---
from core.models import Patient, Company, GENDER_CHOICES, BLOOD_TYPE_CHOICES, INSURANCE_TYPE_CHOICES
from drugs.models import Drug, Supplier, DRUG_FORM_CHOICES
from visits.models import Visit, ReasonForVisit, TreatmentResult, VISIT_STATUS_CHOICES

User = get_user_model()

# --------------------------------------------------
# 1. PatientFilter
# --------------------------------------------------
class PatientFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_by_patient_query', label="جستجوی کلی بیمار")
    
    class Meta:
        model = Patient
        fields = {
            'first_name': ['icontains'],
            'last_name': ['icontains'],
            'national_code': ['exact'],
            'personnel_number': ['exact'],
            'company': ['exact'],
            
        }

    def filter_by_patient_query(self, queryset, name, value):
        return queryset.filter(
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(national_code__icontains=value) |
            Q(personnel_number__icontains=value) |
            Q(company__name__icontains=value)|
            Q(phone_number__icontains=value)
        )

# --------------------------------------------------
# 2. DrugFilter
# --------------------------------------------------
class DrugFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_by_drug_query', label="جستجوی کلی دارو")
    
    # فرض بر این است که مدل Drug شما فیلد total_quantity را دارد
    stock_min = django_filters.NumberFilter(field_name='total_quantity', lookup_expr='gte', label="موجودی از")
    stock_max = django_filters.NumberFilter(field_name='total_quantity', lookup_expr='lte', label="موجودی تا")

    class Meta:
        model = Drug
        fields = {
            'name': ['icontains'],
            'generic_name': ['icontains'],
            'drug_code': ['exact'],
            #'form': ['exact'],
            # 'supplier': ['exact'], # اگر فیلد تامین‌کننده در مدل Drug دارید
        }

    def filter_by_drug_query(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(generic_name__icontains=value) |
            Q(drug_code__icontains=value)
        )


# --------------------------------------------------
# 3. VisitFilter (با اصلاحات کامل)
# --------------------------------------------------
class VisitFilter(django_filters.FilterSet):
    q_patient = django_filters.CharFilter(
        method='filter_by_patient_details', 
        label="جستجوی بیمار (نام، کد ملی/پرسنلی)",
    )
    
    visit_date__gte = django_filters.DateFilter(field_name='visit_date', lookup_expr='date__gte', label="تاریخ ویزیت از")
    visit_date__lte = django_filters.DateFilter(field_name='visit_date', lookup_expr='date__lte', label="تاریخ ویزیت تا")
    
    # اصلاح شد: استفاده از ModelChoiceFilter به جای ChoiceFilter
    reason_for_visit = django_filters.ModelChoiceFilter(
        queryset=ReasonForVisit.objects.all(),
        label="علت مراجعه"
    )
    
    # اصلاح شد: استفاده از ModelChoiceFilter به جای ChoiceFilter
    treatment_result = django_filters.ModelChoiceFilter(
        queryset=TreatmentResult.objects.all(),
        label="نتیجه درمان"
    )

    class Meta:
        model = Visit
        fields = [
            'q_patient',
            'doctor', 
            'visit_date__gte', 
            'visit_date__lte',
            'patient__company',  # فیلتر مستقیم بر اساس شرکت بیمار
            'reason_for_visit',  # اصلاح شد: استفاده از نام فیلتر صحیح
            'treatment_result',  # اصلاح شد: استفاده از نام فیلتر صحیح
            'status', 
            'assigned_to',
            'incident_type', # فیلتر بر اساس نوع حادثه
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # افزودن کلاس 'form-control' به همه فیلترها برای استایل‌دهی یکسان
        for field_name, field in self.filters.items():
            field.field.widget.attrs.update({'class': 'form-control'})
        # لیبل فیلتر شرکت را فارسی می‌کنیم
        if 'patient__company' in self.filters:
            self.filters['patient__company'].label = "شرکت بیمار"


    def filter_by_patient_details(self, queryset, name, value):
        return queryset.filter(
            Q(patient__first_name__icontains=value) |
            Q(patient__last_name__icontains=value) |
            Q(patient__national_code__icontains=value) |
            Q(patient__personnel_number__icontains=value)
        ).distinct()