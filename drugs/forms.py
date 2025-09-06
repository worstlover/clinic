from django import forms
from drugs.models import (
    Drug, DrugRequest, DrugRequestItem, PurchaseInvoice, PurchaseInvoiceItem, DrugBatch, Supplier
)
# from visits.forms import PostVisitTaskForm # این خط به drugs.forms ربطی ندارد و باعث وابستگی متقابل می‌شود. حذف شد.
from django.contrib.auth.models import User
import jdatetime
import datetime
import sys
from django.forms import ModelForm, inlineformset_factory
from django.core.exceptions import ValidationError # برای مدیریت خطاهای ولیدیشن
from django import forms
from .models import Drug, DrugBatch
from django.db.models import Max # برای تولید خودکار کد
from django.utils import timezone 
from datetime import date # اضافه کردن
from persiantools import jdatetime 
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from persiantools.jdatetime import JalaliDate
from django import forms
from .models import PurchaseInvoice, PurchaseInvoiceItem, Drug, Supplier
# برای فیلد تاریخ شمسی در فرم
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
# برای نمایش و تبدیل تاریخ
from persiantools.jdatetime import JalaliDate # <--- این خط اصلاح شد
from datetime import date, datetime
from django.core.exceptions import ValidationError
from decimal import Decimal # برای کار با مقادیر پولی
from django_select2.forms import Select2Widget, Select2MultipleWidget
query = forms.CharField(
        label='جستجو',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام یا کد دارو را برای جستجو وارد کنید...'
        })
    )
# --------------------------------------------------
# فرم‌های مدیریت داروها (Drug Forms) - CORRECTED
# --------------------------------------------------

class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = [
            'name', 'generic_name', 'form',
            'min_stock_alert', 'reorder_point', 'description',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'form': forms.Select(attrs={'class': 'form-control'}),
            'min_stock_alert': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': 'نام دارو',
            'generic_name': 'نام ژنریک',
            'form': 'شکل دارو',
            'min_stock_alert': 'حداقل موجودی هشدار',
            'reorder_point': 'نقطه سفارش مجدد',
            'description': 'توضیحات',
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.drug_code: # اگر کد دارو قبلا تنظیم نشده باشد (فقط هنگام ایجاد جدید)
            # یک حلقه برای پیدا کردن اولین کد منحصر به فرد
            max_attempts = 1000 # حداکثر تلاش برای پیدا کردن کد منحصر به فرد
            
            # آخرین کد عددی موجود در دیتابیس را پیدا کن
            # اطمینان حاصل میکنیم که فقط کدهای عددی رو در نظر بگیره
            # و بعد به int تبدیلش کنیم
            last_drug = Drug.objects.order_by('-drug_code').first()
            if last_drug and last_drug.drug_code.isdigit():
                current_max_code = int(last_drug.drug_code)
            else:
                current_max_code = 1000 # شروع از یک عدد پایه نسبتا بالا

            next_code_value = current_max_code + 1
            
            for _ in range(max_attempts):
                # اگر فیلد drug_code در مدل Drug شما CharField هست
                prospective_code = str(next_code_value) 
                # اگر فیلد drug_code در مدل Drug شما IntegerField هست، فقط از next_code_value استفاده کنید

                if not Drug.objects.filter(drug_code=prospective_code).exists():
                    instance.drug_code = prospective_code
                    break
                next_code_value += 1
            else:
                # اگر بعد از max_attempts هم کد منحصر به فرد پیدا نشد
                raise Exception("Unable to generate a unique drug code after multiple attempts.")
                
        if commit:
            instance.save()
        return instance


class DrugBatchForm(forms.ModelForm):
    # ⭐ FIX: نام فیلد شمسی برای مطابقت با مدل به manufacturing_date_jalali تغییر کرد
    manufacturing_date_jalali = forms.CharField(
        label="تاریخ تولید (شمسی)",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control persian-date-picker', 'placeholder': 'YYYY/MM/DD', 'autocomplete': 'off'})
    )
    expiry_date_jalali = forms.CharField(
        label="تاریخ انقضا (شمسی)",
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control persian-date-picker', 'placeholder': 'YYYY/MM/DD', 'autocomplete': 'off'})
    )
    batch_number = forms.CharField(
        label="شماره بچ",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = DrugBatch
        # ⭐ FIX: 'unit_price' حذف و 'production_date' به 'manufacturing_date' اصلاح شد
        fields = [
            'quantity', 'batch_number', 
            'manufacturing_date', 
            'expiry_date',
            'purchase_price', 'selling_price', 'supplier', 'notes'
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            # ⭐ FIX: 'unit_price' حذف شد
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'quantity': 'تعداد',
            # ⭐ FIX: 'unit_price' حذف شد
            'batch_number': 'شماره بچ',
            'manufacturing_date': 'تاریخ تولید', # ⭐ FIX: نام لیبل اصلاح شد
            'expiry_date': 'تاریخ انقضا',
            'purchase_price': 'قیمت خرید',
            'selling_price': 'قیمت فروش',
            'supplier': 'تامین‌کننده',
            'notes': 'ملاحظات',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ⭐ FIX: پر کردن فیلد شمسی با استفاده از manufacturing_date
        if self.instance and self.instance.manufacturing_date:
            try:
                jdate = jdatetime.date.fromgregorian(date=self.instance.manufacturing_date)
                self.initial['manufacturing_date_jalali'] = jdate.strftime('%Y/%m/%d')
            except Exception:
                self.initial['manufacturing_date_jalali'] = ''
        
        if self.instance and self.instance.expiry_date:
            try:
                jdate = jdatetime.date.fromgregorian(date=self.instance.expiry_date)
                self.initial['expiry_date_jalali'] = jdate.strftime('%Y/%m/%d')
            except Exception:
                self.initial['expiry_date_jalali'] = ''

    def clean(self):
        cleaned_data = super().clean()
        
        # ⭐ FIX: پردازش تاریخ تولید شمسی با نام صحیح
        manufacturing_date_str = cleaned_data.get('manufacturing_date_jalali')
        if manufacturing_date_str:
            try:
                parts = manufacturing_date_str.split('/')
                if len(parts) != 3: raise ValueError()
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                jdate_obj = jdatetime.date(year, month, day)
                # ⭐ FIX: ذخیره در فیلد صحیح manufacturing_date
                cleaned_data['manufacturing_date'] = jdate_obj.togregorian()
            except (ValueError, jdatetime.JalaliDateError):
                self.add_error('manufacturing_date_jalali', "فرمت تاریخ تولید شمسی نامعتبر است.")
        elif self.instance._meta.get_field('manufacturing_date').blank == False and cleaned_data.get('manufacturing_date') is None:
             self.add_error('manufacturing_date_jalali', "تاریخ تولید نمی‌تواند خالی باشد.")
        elif not manufacturing_date_str and self.instance._meta.get_field('manufacturing_date').blank == True:
             cleaned_data['manufacturing_date'] = None

        # پردازش تاریخ انقضا شمسی
        expiry_date_str = cleaned_data.get('expiry_date_jalali')
        if expiry_date_str:
            try:
                parts = expiry_date_str.split('/')
                if len(parts) != 3: raise ValueError()
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                jdate_obj = jdatetime.date(year, month, day)
                cleaned_data['expiry_date'] = jdate_obj.togregorian()
            except (ValueError, jdatetime.JalaliDateError):
                self.add_error('expiry_date_jalali', "فرمت تاریخ انقضا شمسی نامعتبر است.")
        else:
            if self.instance._meta.get_field('expiry_date').blank == False and cleaned_data.get('expiry_date') is None:
                self.add_error('expiry_date_jalali', "تاریخ انقضا نمی‌تواند خالی باشد.")

        return cleaned_data




# DrugSearchForm با فیلدهای صحیح مدل Drug شما
class DrugSearchForm(forms.Form):
    q = forms.CharField(required=False, label='جستجو')
    id = forms.IntegerField(required=False)


from django import forms
from drugs.models import PurchaseInvoice, PurchaseInvoiceItem
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from django_select2.forms import Select2Widget
from decimal import Decimal
import pandas as pd
import io
from django.core.exceptions import ValidationError

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="فایل اکسل",
        help_text="فایل اکسل حاوی اطلاعات موجودی موقت را آپلود کنید. (ستون ۱: نام دارو، ستون ۲: شکل دارو)",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

# --------------------------------------------------
# فرم فاکتور خرید (PurchaseInvoice Form)
# --------------------------------------------------
class PurchaseInvoiceForm(forms.ModelForm):
    invoice_date = JalaliDateField(
        label=('تاریخ فاکتور'),
        widget=AdminJalaliDateWidget
    )

    class Meta:
        model = PurchaseInvoice
        fields = ['invoice_number', 'invoice_date', 'supplier', 'status', 'notes']
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control select2-supplier'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'invoice_number': 'شماره فاکتور',
            'supplier': 'تامین‌کننده',
            'status': 'وضعیت',
            'notes': 'توضیحات',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ... بقیه کد مربوط به تولید خودکار شماره فاکتور
        if not self.instance.pk and not self.initial.get('invoice_number'):
            # تولید خودکار شماره فاکتور
            last_invoice = PurchaseInvoice.objects.all().order_by('-id').first()
            if last_invoice and last_invoice.invoice_number:
                try:
                    last_number = int(last_invoice.invoice_number)
                    self.initial['invoice_number'] = str(last_number + 1)
                except ValueError:
                    self.initial['invoice_number'] = '1001'
            else:
                self.initial['invoice_number'] = '1001'
        
        if not self.initial.get('invoice_date'):
            self.initial['invoice_date'] = JalaliDate.today()


# --------------------------------------------------
# فرم آیتم فاکتور خرید (PurchaseInvoiceItem Form)
# --------------------------------------------------
class PurchaseInvoiceItemForm(forms.ModelForm):
    # این فرم باید بتواند داده های raw از اکسل را بپذیرد
    drug = forms.ModelChoiceField(
        queryset=Drug.objects.all(),
        label='دارو',
        widget=forms.Select(attrs={'class': 'form-control select2-drug'}), 
        required=True
    )
    
    expiry_date = forms.DateField(
        label='تاریخ انقضا (میلادی)',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control gregorian-date-input',
            'placeholder': 'مثال: 2025-06-30'
        }),
        required=False
    )

    class Meta:
        model = PurchaseInvoiceItem
        fields = ['drug', 'quantity', 'unit_price', 'batch_number', 'expiry_date']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control item-quantity', 'min': '0', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control item-unit-price', 'min': '0', 'step': '0.01'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'drug': 'دارو',
            'quantity': 'تعداد',
            'unit_price': 'قیمت واحد (ریال)',
            'batch_number': 'شماره بچ',
        }

    total_item_price = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput(),
        initial=Decimal('0.00')
    )
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')
        
        if quantity is not None and unit_price is not None:
            cleaned_data['total_item_price'] = Decimal(quantity) * Decimal(unit_price)
        else:
            cleaned_data['total_item_price'] = Decimal('0.00')
        
        # اعتبارسنجی وجود فیلدهای کلیدی در دیتا
        if not cleaned_data.get('drug'):
            raise forms.ValidationError('فیلد دارو اجباری است.')
        if cleaned_data.get('quantity') is None or cleaned_data.get('quantity') <= 0:
            raise forms.ValidationError('تعداد باید یک عدد مثبت باشد.')
        if cleaned_data.get('unit_price') is None or cleaned_data.get('unit_price') <= 0:
            raise forms.ValidationError('قیمت واحد باید یک عدد مثبت باشد.')
            
        return cleaned_data

PurchaseInvoiceItemFormSet = inlineformset_factory(
    PurchaseInvoice,
    PurchaseInvoiceItem,
    form=PurchaseInvoiceItemForm,
    extra=1, 
    can_delete=True,
    min_num=1, 
    validate_min=True,
)


# ویجت سفارشی برای دیت‌پیکر شمسی (مفید برای فیلدهای تاریخ)
JALALI_DATE_PICKER_WIDGET = forms.TextInput(attrs={
    'class': 'form-control jalali-datepicker', # <--- کلاس مهم برای جاوا اسکریپت
    'placeholder': 'مثال: ۱۴۰۳/۰۴/۲۴',
    'autocomplete': 'off' # جلوگیری از نمایش تاریخ‌های پیشنهادی مرورگر
})

# --------------------------------------------------
# فرم‌های مدیریت درخواست دارو (Drug Request Forms)
# --------------------------------------------------

class DrugRequestAnalysisForm(forms.Form):
    start_date = JalaliDateField(label="تاریخ شروع تحلیل", widget=AdminJalaliDateWidget(attrs={'autocomplete': 'off'}))
    end_date = JalaliDateField(label="تاریخ پایان تحلیل", widget=AdminJalaliDateWidget(attrs={'autocomplete': 'off'}))
    
    # چویس‌ها اصلاح شدند و گزینه اضافی حذف شد
    SUGGESTION_METHOD_CHOICES = [
        ('consumption', 'تحلیل مصرف در دوره مشخص شده'),
        ('low_stock', 'داروهای با موجودی کمتر از آستانه'),
        ('reorder_point', 'داروهایی که به نقطه سفارش رسیده‌اند'),
    ]
    suggestion_method = forms.MultipleChoiceField(
        label="روش‌های پیشنهادی برای ایجاد درخواست",
        choices=SUGGESTION_METHOD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="حداقل یک روش را برای تحلیل انتخاب کنید."
    )
    
    percentage_increase = forms.DecimalField(
        label="درصد افزایش احتمالی برای پیش‌بینی", required=False, initial=0.0, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 10 برای 10% افزایش'})
    )
    
    low_stock_threshold = forms.IntegerField(
        label="آستانه موجودی کم", required=False, initial=10, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.")
        return cleaned_data

class DrugRequestItemForm(forms.ModelForm):
    drug = forms.ModelChoiceField(
        queryset=Drug.objects.all(),
        label='دارو',
        widget=Select2Widget(attrs={'data-placeholder': 'انتخاب دارو'}),
        required=True
    )
    class Meta:
        model = DrugRequestItem
        fields = ['drug', 'requested_quantity', 'notes']
        widgets = {
            'requested_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'drug': 'دارو',
            'requested_quantity': 'تعداد درخواستی',
            'notes': 'ملاحظات',
        }

# --------------------------------------------------
# فرم درخواست دارو (DrugRequest Form)
# --------------------------------------------------
class DrugRequestForm(forms.ModelForm):
    request_date = JalaliDateField(
        label=('تاریخ درخواست'),
        widget=AdminJalaliDateWidget
    )
    requested_by = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label='درخواست‌کننده',
        widget=Select2Widget(attrs={'data-placeholder': 'انتخاب درخواست‌کننده'}),
        required=True
    )
    assigned_approver = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label='تاییدکننده ارجاع شده',
        widget=Select2Widget(attrs={'data-placeholder': 'انتخاب تاییدکننده'}),
        required=False
    )

    class Meta:
        model = DrugRequest
        fields = [
            'request_date', 'requested_by', 'assigned_approver',
            'status', 'description'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'request_date': 'تاریخ درخواست',
            'requested_by': 'درخواست‌کننده',
            'assigned_approver': 'تاییدکننده ارجاع شده',
            'status': 'وضعیت',
            'description': 'توضیحات درخواست',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None) 
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.request_date:
            try:
                jdate = jdatetime.date.fromgregorian(date=self.instance.request_date)
                self.initial['request_date'] = jdate.strftime('%Y/%m/%d')
            except Exception:
                self.initial['request_date'] = ''
        
        if not self.instance.pk:
            today_jdate = jdatetime.date.today()
            year_prefix = str(today_jdate.year)[-2:]
            
            last_request = DrugRequest.objects.filter(request_code__startswith=f'REQ-{year_prefix}-').order_by('-request_code').first()
            
            if last_request and last_request.request_code:
                try:
                    last_sequential_number = int(last_request.request_code.split('-')[-1])
                except ValueError:
                    last_sequential_number = 0
            else:
                last_sequential_number = 0
            
            self.initial['request_code'] = f'REQ-{year_prefix}-{last_sequential_number + 1:04d}'
        
        self.fields['requested_by'].widget.attrs['class'] = 'form-control django-select2'
        self.fields['assigned_approver'].widget.attrs['class'] = 'form-control django-select2'
        
    def clean_request_code(self):
        if self.instance.pk:
            return self.instance.request_code
        return self.cleaned_data['request_code']

# --- New: Define DrugRequestItemForm ---
class DrugRequestItemForm(forms.ModelForm):
    class Meta:
        model = DrugRequestItem
        # Ensure 'approved_quantity' is included in the fields
        fields = ['drug', 'requested_quantity', 'approved_quantity', 'notes'] 
        widgets = {
            'drug': Select2Widget(attrs={'data-placeholder': 'انتخاب دارو'}),
            'requested_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'approved_quantity': forms.NumberInput(attrs={'class': 'form-control'}), # Added this line
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'drug': 'دارو',
            'requested_quantity': 'تعداد درخواستی',
            'approved_quantity': 'تعداد تایید شده', # Added this line
            'notes': 'ملاحظات',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Select2 class to the drug field for proper rendering
        self.fields['drug'].widget.attrs['class'] = 'form-control django-select2 select2-single-item'

# --- Corrected: DrugRequestItemFormset using the new DrugRequestItemForm ---
DrugRequestItemFormset = inlineformset_factory(
    DrugRequest, DrugRequestItem, form=DrugRequestItemForm,
    extra=1, can_delete=True, min_num=1, validate_min=True,
)
# --------------------------------------------------
DrugRequestItemFormset = inlineformset_factory(
    DrugRequest, DrugRequestItem, form=DrugRequestItemForm,
    extra=1, can_delete=True, min_num=0, validate_min=False, # min_num و validate_min تغییر یافتند
)

class BaseDrugRequestItemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return # Don't bother validating if there are already errors

        drugs = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                drug = form.cleaned_data.get('drug')
                if drug in drugs:
                    # Add a non-field error to the specific form, or to the formset
                    form.add_error('drug', 'این دارو قبلاً در درخواست اضافه شده است.')
                    # Or add a general error to the formset
                    # raise forms.ValidationError("داروهای تکراری در درخواست وجود دارد.")
                drugs.append(drug)

DrugRequestItemFormset = inlineformset_factory(
    DrugRequest, DrugRequestItem, form=DrugRequestItemForm,
    formset=BaseDrugRequestItemFormSet, # Add this line
    extra=1, can_delete=True, min_num=1, validate_min=True,
)
# --------------------------------------------------
# فرم مدیریت تامین‌کننده (Supplier Form)
# --------------------------------------------------
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'notes'] # 'phone' و 'notes' اضافه شد
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 09121234567'}), # 'phone'
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), # اضافه شد
        }
        labels = {
            'name': 'نام تامین‌کننده',
            'contact_person': 'فرد تماس',
            'phone': 'شماره تلفن', # 'phone'
            'email': 'ایمیل',
            'address': 'آدرس',
            'notes': 'ملاحظات', # اضافه شد
        }
        