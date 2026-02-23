# D:\final\reports\filters.py

import django_filters
from django import forms
from django.db.models import Q ,Sum
from core.models import Patient, Company, GENDER_CHOICES, BLOOD_TYPE_CHOICES
from visits.models import Visit, ReasonForVisit, TreatmentResult, VISIT_STATUS_CHOICES, INCIDENT_TYPE_CHOICES # INCIDENT_TYPE_CHOICES را ایمپورت کنید
from drugs.models import Drug
from drugs.models import Drug, Supplier, PurchaseInvoice, DrugRequest # 👈 اضافه کردن ایمپورت‌های جدید
from datetime import date , time, timedelta #

from persiantools.jdatetime import JalaliDate
from persiantools import digits

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
import django_filters
from django import forms
from drugs.models import Drug
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column


JALALI_DATE_PICKER_WIDGET = forms.TextInput(attrs={
    'class': 'form-control jalali-datepicker', # <--- کلاس مهم برای جاوا اسکریپت
    'placeholder': 'مثال: ۱۴۰۳/۰۴/۲۴',
    'autocomplete': 'off' # جلوگیری از نمایش تاریخ‌های پیشنهادی مرورگر
})
# !!! ویجت سفارشی برای تایم‌پیکر
TIME_PICKER_WIDGET = forms.TimeInput(attrs={
    'class': 'form-control timepicker', # کلاس برای جاوا اسکریپت
    'placeholder': 'مثال: ۱۲:۰۰',
    'autocomplete': 'off'
})


class JalaliDateFilter(django_filters.DateFilter):
    field_class = forms.CharField

    def filter(self, qs, value):
        if not value:
            return qs
        try:
            value_english_digits = digits.fa_to_en(value)
            parts = [int(p) for p in value_english_digits.split('/')]
            if len(parts) == 3:
                jalali_year, jalali_month, jalali_day = parts
                converted_date = JalaliDate(jalali_year, jalali_month, jalali_day).to_gregorian()
                return super().filter(qs, converted_date)
            else:
                return qs
        except (ValueError, TypeError):
            return qs


class PatientFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(lookup_expr='icontains', label="نام")
    last_name = django_filters.CharFilter(lookup_expr='icontains', label="نام خانوادگی")
    national_code = django_filters.CharFilter(lookup_expr='icontains', label="کد ملی")
    company = django_filters.ModelChoiceFilter(queryset=Company.objects.all(), label="شرکت")
    gender = django_filters.ChoiceFilter(choices=GENDER_CHOICES, label="جنسیت")
    # جدید: فیلتر گروه خونی برای هماهنگی با نمودار
    blood_type = django_filters.ChoiceFilter(choices=BLOOD_TYPE_CHOICES, label="گروه خونی")

    date_of_birth_gte = JalaliDateFilter(
        field_name='date_of_birth', lookup_expr='gte', label="تاریخ تولد از",
        widget=JALALI_DATE_PICKER_WIDGET
    )
    date_of_birth_lte = JalaliDateFilter(
        field_name='date_of_birth', lookup_expr='lte', label="تاریخ تولد تا",
        widget=JALALI_DATE_PICKER_WIDGET
    )
    registered_at_gte = JalaliDateFilter(
        field_name='registered_at', lookup_expr='gte', label="تاریخ ثبت‌نام از",
        widget=JALALI_DATE_PICKER_WIDGET
    )
    registered_at_lte = JalaliDateFilter(
        field_name='registered_at', lookup_expr='lte', label="تاریخ ثبت‌نام تا",
        widget=JALALI_DATE_PICKER_WIDGET
    )

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'national_code', 'company', 'gender', 'blood_type',
            'date_of_birth_gte', 'date_of_birth_lte',
            'registered_at_gte', 'registered_at_lte',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.helper = FormHelper()
        self.form.helper.form_method = 'get'
        self.form.helper.form_tag = False # برای جلوگیری از رندر تگ <form> توسط crispy

        # بازچینی layout و حذف دکمه Submit
        self.form.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-3 mb-3'),
                Column('last_name', css_class='form-group col-md-3 mb-3'),
                Column('national_code', css_class='form-group col-md-3 mb-3'),
                Column('company', css_class='form-group col-md-3 mb-3'),
            ),
            Row(
                Column('gender', css_class='form-group col-md-4 mb-3'),
                Column('blood_type', css_class='form-group col-md-4 mb-3'), # اضافه شدن فیلد گروه خونی به layout
                Column('date_of_birth_gte', css_class='form-group col-md-2 mb-3'),
                Column('date_of_birth_lte', css_class='form-group col-md-2 mb-3'),
            ),
            Row(
                Column('registered_at_gte', css_class='form-group col-md-3 mb-3'),
                Column('registered_at_lte', css_class='form-group col-md-3 mb-3'),
            )
        )
        
        # فعال‌سازی Select2 برای فیلدهای جدید و قدیمی
        self.form.fields['company'].widget.attrs.update({'class': 'select2-enable'})
        self.form.fields['gender'].widget.attrs.update({'class': 'select2-enable'})
        self.form.fields['blood_type'].widget.attrs.update({'class': 'select2-enable'})

# --- VisitFilter اصلاح شده ---
class VisitFilter(django_filters.FilterSet):
    patient_first_name = django_filters.CharFilter(
        field_name='patient__first_name', lookup_expr='icontains', label="نام بیمار"
    )
    patient_last_name = django_filters.CharFilter(
        field_name='patient__last_name', lookup_expr='icontains', label="نام خانوادگی بیمار"
    )
    
    reason_for_visit = django_filters.ModelChoiceFilter(
        queryset=ReasonForVisit.objects.all(),
        field_name='reason_for_visit',
        label="علت مراجعه",
        empty_label="انتخاب کنید..."
    )
    treatment_result = django_filters.ModelChoiceFilter(
        queryset=TreatmentResult.objects.all(),
        field_name='treatment_result',
        label="نتیجه درمان",
        empty_label="انتخاب کنید..."
    )

    visit_date_gte = JalaliDateFilter(
        lookup_expr='gte', field_name='visit_date', label="تاریخ ویزیت از",
        widget=JALALI_DATE_PICKER_WIDGET
    )
    visit_date_lte = JalaliDateFilter(
        lookup_expr='lte', field_name='visit_date', label="تاریخ ویزیت تا",
        widget=JALALI_DATE_PICKER_WIDGET
    )

    # 👈 فیلترهای جدید برای ساعت
    visit_time_gte = django_filters.TimeFilter(
        field_name='visit_date__time', lookup_expr='gte', label="ساعت ویزیت از",
        widget=TIME_PICKER_WIDGET
    )
    visit_time_lte = django_filters.TimeFilter(
        field_name='visit_date__time', lookup_expr='lte', label="ساعت ویزیت تا",
        widget=TIME_PICKER_WIDGET
    )

    patient_company = django_filters.ModelChoiceFilter(
        queryset=Company.objects.all(),
        field_name='patient__company',
        label="شرکت بیمار",
        empty_label="همه شرکت‌ها"
    )

    incident_type = django_filters.ChoiceFilter(
        choices=INCIDENT_TYPE_CHOICES,
        label="نوع حادثه",
        empty_label="انتخاب کنید..."
    )

    blood_pressure = django_filters.CharFilter(
        field_name='blood_pressure', 
        lookup_expr='icontains', 
        label="فشار خون (مثال: 120/80)",
        help_text="مثال: 120/80 یا 120"
    )

    class Meta:
        model = Visit
        fields = [
            'patient_first_name', 'patient_last_name', 
            'reason_for_visit', 'treatment_result',
            'visit_date_gte', 'visit_date_lte',
            'visit_time_gte', 'visit_time_lte', # 👈 اضافه شدن فیلدهای ساعت
            'patient_company',
            'incident_type',
            'blood_pressure',
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.helper = FormHelper()
        self.form.helper.form_method = 'get'
        self.form.helper.form_tag = False
        self.form.helper.layout = Layout(
            Row(
                Column('patient_first_name', css_class='form-group col-md-3 mb-0'),
                Column('patient_last_name', css_class='form-group col-md-3 mb-0'),
                Column('reason_for_visit', css_class='form-group col-md-3 mb-0'),
                Column('treatment_result', css_class='form-group col-md-3 mb-0'),
                css_class='mb-3'
            ),
            Row(
                Column('visit_date_gte', css_class='form-group col-md-3 mb-0'),
                Column('visit_date_lte', css_class='form-group col-md-3 mb-0'),
                Column('visit_time_gte', css_class='form-group col-md-3 mb-0'), # 👈 اضافه شدن به layout
                Column('visit_time_lte', css_class='form-group col-md-3 mb-0'), # 👈 اضافه شدن به layout
                css_class='mb-3'
            ),
            Row(
                Column('patient_company', css_class='form-group col-md-3 mb-0'),
                Column('incident_type', css_class='form-group col-md-3 mb-0'),
                Column('blood_pressure', css_class='form-group col-md-3 mb-0'),
                css_class='mb-3'
            ),
            Row(
                Column(
                    Submit('submit', 'جستجو', css_class='btn btn-primary'),
                    css_class='form-group col-md-12 text-right mt-3'
                )
            )
        )
        # اعمال کلاس select2-enable
        self.form.fields['reason_for_visit'].widget.attrs.update({'class': 'select2-enable'})
        self.form.fields['treatment_result'].widget.attrs.update({'class': 'select2-enable'})
        self.form.fields['patient_company'].widget.attrs.update({'class': 'select2-enable'})
        self.form.fields['incident_type'].widget.attrs.update({'class': 'select2-enable'})
        
        # 👈 تنظیم مقادیر پیش‌فرض برای فیلترهای ساعت
        if not self.data.get('visit_time_gte'):
            self.form.initial['visit_time_gte'] = time(12, 0) # 12:00 PM
        if not self.data.get('visit_time_lte'):
            self.form.initial['visit_time_lte'] = time(23, 59) # 11:59 PM


class DrugFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr='icontains', label="نام دارو",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام دارو را وارد کنید'})
    )
    stock_quantity_gte = django_filters.NumberFilter(
        lookup_expr='gte', label="موجودی از", field_name='stock_quantity'
    )
    stock_quantity_lte = django_filters.NumberFilter(
        lookup_expr='lte', label="موجودی تا", field_name='stock_quantity'
    )
    expiry_date_gte = JalaliDateFilter(
        lookup_expr='gte', field_name='batches__expiry_date', label="تاریخ انقضا از",
        widget=JALALI_DATE_PICKER_WIDGET, distinct=True
    )
    expiry_date_lte = JalaliDateFilter(
        lookup_expr='lte', field_name='batches__expiry_date', label="تاریخ انقضا تا",
        widget=JALALI_DATE_PICKER_WIDGET, distinct=True
    )

    # 👈 **تغییر اصلی اینجاست**
    # تعریف فیلتر به صورت رسمی، اما با یک متد که کاری انجام نمی‌دهد
    show_batch_details = django_filters.BooleanFilter(
        label="نمایش جزئیات هر بچ",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        method='do_nothing'  # اتصال به متد خالی
    )

    class Meta:
        model = Drug
        fields = [
            'name',
            'stock_quantity_gte', 'stock_quantity_lte',
            'expiry_date_gte', 'expiry_date_lte'
        ]

    def do_nothing(self, queryset, name, value):
        """
        این متد برای فیلترهایی استفاده می‌شود که فقط جنبه کنترلی در
        template دارند و نباید خود کوئری‌ست را تغییر دهند.
        """
        return queryset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # حالا دیگر نیازی به افزودن دستی فیلد به فرم نیست، چون به عنوان فیلتر تعریف شده است.
        self.form.helper = FormHelper()
        self.form.helper.form_method = 'get'
        self.form.helper.form_tag = False
        self.form.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-4 mb-0'),
                Column('stock_quantity_gte', css_class='form-group col-md-4 mb-0'),
                Column('stock_quantity_lte', css_class='form-group col-md-4 mb-0'),
                css_class='mb-3'
            ),
            Row(
                Column('expiry_date_gte', css_class='form-group col-md-4 mb-0'),
                Column('expiry_date_lte', css_class='form-group col-md-4 mb-0'),
                # ارجاع مستقیم به نام فیلتر در layout
                Column(
                    Field('show_batch_details', wrapper_class="form-check"),
                    css_class='form-group col-md-4 d-flex align-items-center pt-3'
                ),
                css_class='mb-3'
            )
            # دکمه submit توسط template رندر می‌شود و نیازی به تعریف در layout نیست
        )

TRANSACTION_TYPES = (
    ('all', 'همه موارد'),
    ('in', 'فقط ورودی (خرید)'),
    ('out', 'فقط خروج (مصرف)'),
)

class DrugTransactionFilter(django_filters.FilterSet):
    # این کلاس فقط برای تولید فرم در UI استفاده می‌شود
    transaction_type = django_filters.ChoiceFilter(
        choices=(('all', 'همه موارد'), ('in', 'ورود (+)'), ('out', 'خروج (-)')),
        label="نوع تراکنش",
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    drug = django_filters.ModelMultipleChoiceFilter(
        queryset=Drug.objects.all(),
        label="انتخاب دارو(ها)",
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2-enable'})
    )

    class Meta:
        model = Drug
        fields = [] # فیلد دستی نباید اینجا باشد

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.helper = FormHelper()
        self.form.helper.form_tag = False
        self.form.helper.layout = Layout(
            Row(
                Column('drug', css_class='col-md-9'),
                Column('transaction_type', css_class='col-md-3'),
            )
        )