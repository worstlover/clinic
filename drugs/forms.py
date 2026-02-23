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
from .models import  DrugBarcode, DRUG_UNIT_CHOICES

# برای فیلد تاریخ شمسی در فرم
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
# برای نمایش و تبدیل تاریخ
from persiantools.jdatetime import JalaliDate # <--- این خط اصلاح شد
from datetime import date, datetime
from django.core.exceptions import ValidationError
from decimal import Decimal # برای کار با مقادیر پولی
from django_select2.forms import Select2Widget, Select2MultipleWidget
from django.core.validators import MinValueValidator
from django.contrib.auth.models import Group
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
query = forms.CharField(
        label='جستجو',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام یا کد دارو را برای جستجو وارد کنید...'
        })
    )

class DrugReceiveForm(forms.Form):
    # این فیلدها در HTML وجود ندارند، اما برای اعتبارسنجی در اینجا تعریف می‌شوند
    drug_name = forms.CharField(label="نام دارو", required=False)
    batch_number = forms.CharField(label="شماره بچ", max_length=100)
    expiry_date = forms.DateField(label="تاریخ انقضا")
    
    # تغییر اصلی: استفاده از IntegerField و اضافه کردن validator
    quantity = forms.IntegerField(
        label="تعداد دریافتی", 
        validators=[MinValueValidator(1, message="تعداد دریافتی باید حداقل ۱ باشد.")]
    )
    
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), label="تامین‌کننده")
# --------------------------------------------------
# فرم‌های مدیریت داروها (Drug Forms) - CORRECTED
# --------------------------------------------------

DRUG_FORM_CHOICES = [
    ('tablet', 'قرص'),
    ('capsule', 'کپسول'),
    ('syrup', 'شربت'),
    ('ampoule', 'آمپول'),
    ('injection', 'تزریقی'), # Added 'injection' as a valid choice
    ('vial', 'ویال'),
    ('inhaler', 'اسپری تنفسی'),
    ('aerosol', 'آئروسل'),
    ('solution', 'محلول'),
    ('ointment', 'پماد'),
    ('cream', 'کرم'),
    ('gel', 'ژل'),
    ('suspension', 'سوسپانسیون'),
    ('drop', 'قطره'),
    ('suppository', 'شیاف'),
    ('patch', 'چسب ترانس درمال'),
    ('granules', 'گرانول'),
    ('other', 'سایر')
]


class DrugForm(forms.ModelForm):
    search_drug = forms.ModelChoiceField(
        queryset=Drug.objects.all(),
        required=False,
        label='جستجوی داروهای موجود',
        widget=forms.Select(attrs={'class': 'select2-drug-search', 'data-placeholder': 'جستجو بر اساس نام یا بارکد'})
    )
    
    # This field is used to track if a drug is new or existing.
    is_new_drug = forms.BooleanField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        instance = kwargs.get('instance')
        
        # Check if the user is a manager based on group membership
        is_manager = False
        if self.request and self.request.user.is_authenticated:
            try:
                managers_group = Group.objects.get(name='مدیران')
                if managers_group in self.request.user.groups.all():
                    is_manager = True
            except Group.DoesNotExist:
                logger.warning("Managers group not found. All users will have full edit access.")
        
        # Make certain fields read-only if the user is not a manager and is editing an existing drug
        if instance and not is_manager:
            self.fields['name'].widget.attrs['readonly'] = 'readonly'
            self.fields['generic_name'].widget.attrs['readonly'] = 'readonly'
            self.fields['company_name'].widget.attrs['readonly'] = 'readonly'

        # Set the choices and label for the `form` field
        self.fields['form'].choices = DRUG_FORM_CHOICES
        self.fields['form'].label = 'شکل دارو'
    
    # NEW: Override this method to make the Select2 search on both name and GTIN.
    # این متد به جنگو می گوید که برای هر گزینه در فیلد، چه متنی را نمایش دهد.
    def label_from_instance(self, obj):
        # بارکدهای مرتبط با دارو را دریافت می‌کنیم
        barcodes = obj.barcodes.all()
        
        # رشته‌ای از بارکدها را ایجاد می‌کنیم تا قابل نمایش باشند
        gtin_str = ", ".join([barcode.gtin for barcode in barcodes])
        
        # اگر بارکدی وجود داشت، آن را به نام دارو اضافه می‌کنیم
        if gtin_str:
            return f"{obj.name} ({gtin_str})"
        
        # در غیر این صورت، فقط نام دارو را برمی‌گردانیم
        return f"{obj.name}"

    class Meta:
        model = Drug
        # تغییر نام فیلد از `unit` به `form` برای هماهنگی با مدل
        fields = [
            'name', 'generic_name', 'form', 'drug_code','unit',
            'min_stock_alert', 'reorder_point', 'description', 'company_name',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'drug_code': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'min_stock_alert': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'form': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'نام دارو',
            'generic_name': 'نام ژنریک',
            'company_name': 'نام شرکت',
            'drug_code': 'کد دارو',
            'min_stock_alert': 'حداقل موجودی هشدار',
            'reorder_point': 'نقطه سفارش مجدد',
            'description': 'توضیحات',
            'form': 'شکل دارو',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Correctly get the selected value for the 'form' field
        form_choice = cleaned_data.get('form')
        name_input = cleaned_data.get('name')

        if form_choice and name_input:
            # Get the human-readable text from the choices list
            form_text = dict(DRUG_FORM_CHOICES).get(form_choice)
            if form_text:
                combined_name = f"{form_text} {name_input}"
                cleaned_data['name'] = combined_name
            else:
                logger.error("Failed to find a matching human-readable name for the selected form.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-generate a new drug code if one doesn't exist
        if not instance.drug_code:
            max_attempts = 1000
            last_drug = Drug.objects.filter(drug_code__regex=r'^\d+$').order_by('-drug_code').first()
            current_max_code = int(last_drug.drug_code) if last_drug and last_drug.drug_code.isdigit() else 1000
            next_code_value = current_max_code + 1
            
            for _ in range(max_attempts):
                prospective_code = str(next_code_value)
                if not Drug.objects.filter(drug_code=prospective_code).exists():
                    instance.drug_code = prospective_code
                    break
                next_code_value += 1
            else:
                raise Exception("Unable to generate a unique drug code after multiple attempts.")
        
        if commit:
            instance.save()
        return instance

class DrugBarcodeForm(forms.ModelForm):
    class Meta:
        model = DrugBarcode
        fields = ['gtin']
        widgets = {
            'gtin': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'gtin': 'بارکد (GTIN)',
        }

DrugBarcodeFormSet = inlineformset_factory(
    parent_model=Drug,
    model=DrugBarcode,
    form=DrugBarcodeForm,
    extra=1,
    can_delete=True
)
class DrugBarcodeForm(forms.ModelForm):
    class Meta:
        model = DrugBarcode
        fields = ['gtin']
        widgets = {
            'gtin': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'gtin': 'بارکد (GTIN)',
        }

DrugBarcodeFormSet = inlineformset_factory(
    Drug,
    DrugBarcode,
    form=DrugBarcodeForm,
    extra=1,
    can_delete=True
)
# استفاده از inlineformset برای مدیریت بارکدهای یک دارو
# این کلاس در views.py برای مدیریت فرم‌ها استفاده می‌شود.

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
        fields = ['invoice_number', 'invoice_date', 'supplier', 'status', 'notes'] # 'status' بازگردانده شد
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control select2-supplier'}),
            'status': forms.Select(attrs={'class': 'form-control'}), # 'status' بازگردانده شد
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'invoice_number': 'شماره فاکتور',
            'supplier': 'تامین‌کننده',
            'status': 'وضعیت', # 'status' بازگردانده شد
            'notes': 'توضیحات',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get('invoice_number'):
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
        }, format='%Y-%m-%d'), # <--- این قسمت حیاتی است: فرمت خروجی جنگو برای HTML
        input_formats=['%Y-%m-%d'], # فرمت ورودی از HTML به جنگو
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
        
        return cleaned_data

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise ValidationError('تعداد نمی‌تواند منفی باشد.')
        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price is not None and unit_price < 0:
            raise ValidationError('قیمت واحد نمی‌تواند منفی باشد.')
        return unit_price

PurchaseInvoiceItemFormSet = inlineformset_factory(
    PurchaseInvoice,
    PurchaseInvoiceItem,
    form=PurchaseInvoiceItemForm,
    extra=1, 
    can_delete=True,
    min_num=1, 
    validate_min=True,
)

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label='فایل اکسل',
                                 help_text='فایل اکسل حاوی اطلاعات آیتم‌های فاکتور را انتخاب کنید.',
                                 required=True)
    
    # متد __init__ را برای اضافه کردن کلاس Bootstrap به فیلد اضافه می‌کنیم
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['excel_file'].widget.attrs.update({'class': 'form-control'})

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
from django import forms
from django.forms import inlineformset_factory
from .models import DrugRequest, DrugRequestItem, Drug
from jalali_date.widgets import AdminJalaliDateWidget
from jalali_date.fields import JalaliDateField

class DrugRequestForm(forms.ModelForm):
    request_date = JalaliDateField(label='تاریخ درخواست', widget=AdminJalaliDateWidget)

    class Meta:
        model = DrugRequest
        fields = ['request_date', 'requested_by', 'assigned_approver', 'status', 'description']
        widgets = {
            # استفاده از Select ساده برای جلوگیری از تداخل با JS
            'requested_by': forms.Select(attrs={'class': 'form-select'}),
            'assigned_approver': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # ۱. غیرفعال کردن فیلد تاریخ و درخواست‌کننده در حالت ویرایش
        if self.instance.pk:
            self.fields['request_date'].widget.attrs['readonly'] = True
            self.fields['request_date'].disabled = True
            self.fields['requested_by'].disabled = True

class DrugRequestItemForm(forms.ModelForm):
    class Meta:
        model = DrugRequestItem
        fields = ['drug', 'requested_quantity', 'approved_quantity', 'notes']
        widgets = {
            'drug': forms.Select(attrs={'class': 'form-select drug-select-field'}),
            'requested_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'approved_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }
DrugRequestItemFormset = inlineformset_factory(
    DrugRequest, DrugRequestItem, 
    form=DrugRequestItemForm,
    extra=0, # بسیار مهم: ردیف خالی اضافه نسازد
    can_delete=True
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