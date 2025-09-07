# D:\final\core\forms.py - بازنویسی شده برای PatientForm
from django import forms
from .models import Patient, Company
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from django.core.exceptions import ValidationError
from datetime import date, datetime
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import Profile
from .utils import convert_fa_numbers_to_en # <--- وارد کردن تابع کمکی


class PatientForm(forms.ModelForm):
    date_of_birth = JalaliDateField(
        label="تاریخ تولد (شمسی)",
        widget=AdminJalaliDateWidget(),
        required=False,
        help_text="مثال: ۱۳۷۰/۰۱/۱۵"
    )

    last_periodic_examination_date = JalaliDateField(
        label="آخرین معاینه دوره ای (شمسی)",
        widget=AdminJalaliDateWidget(),
        required=False,
        help_text="تاریخ آخرین معاینه دوره ای به شمسی"
    )

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'national_code', 'passport_number',
            'is_foreign_national', 'phone_number', 'gender', 'company',
            'insurance_type', 'blood_type', 'address', 'profile_picture',
            'allergies', 'medical_history', 'occupation', 'personnel_number',
            'is_monitored',
            'date_of_birth',
            'last_periodic_examination_date',
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'national_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: ۰۰۱۴۷۸۵۲۳۶'}),
            'passport_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'برای اتباع خارجی'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: ۰۹۱۲۳۴۵۶۷۸۹'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'insurance_type': forms.Select(attrs={'class': 'form-control'}),
            'blood_type': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'allergies': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: پنی‌سیلین، گرده گل'}),
            'medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات مربوط به سوابق پزشکی...'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: مهندس، کارگر'}),
            # اگر personnel_number در مدل CharField است، NumberInput ممکن است اخطار دهد. 
            # اگر فقط شامل عدد است، TextInput هم کار می‌کند و بهتر است.
            'personnel_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'فقط برای پرسنل شرکت'}), 
            'is_foreign_national': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_monitored': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True)

    # متدهای clean برای تبدیل اعداد فارسی به انگلیسی
    def clean_national_code(self):
        national_code = self.cleaned_data.get('national_code')
        if national_code:
            return convert_fa_numbers_to_en(national_code)
        return national_code

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            return convert_fa_numbers_to_en(phone_number)
        return phone_number

    def clean_personnel_number(self):
        personnel_number = self.cleaned_data.get('personnel_number')
        if personnel_number:
            # از آنجایی که personnel_number در مدل شما CharField است، فقط تبدیل رقم انجام می‌شود.
            # اگر قرار است صرفاً عدد باشد و از CharField به IntegerField در مدل تغییر دهید،
            # باید اینجا یک try-except برای int(personnel_number) اضافه شود.
            return convert_fa_numbers_to_en(personnel_number)
        return personnel_number
        
    def clean(self):
        cleaned_data = super().clean()
        national_code = cleaned_data.get('national_code')
        passport_number = cleaned_data.get('passport_number')
        is_foreign_national = cleaned_data.get('is_foreign_national')

        # منطق اعتبارسنجی کد ملی/پاسپورت
        if not is_foreign_national:
            # اگر تبعه خارجی نیست، کد ملی اجباری است
            if not national_code:
                self.add_error('national_code', 'کد ملی برای اتباع ایرانی اجباری است.')
            # اگر کد ملی دارد، پاسپورت نباید وارد شود
            if passport_number:
                self.add_error('passport_number', 'برای اتباع ایرانی، شماره پاسپورت نباید وارد شود.')
        else:
            # اگر تبعه خارجی است، شماره پاسپورت اجباری است
            if not passport_number:
                self.add_error('passport_number', 'شماره پاسپورت برای اتباع خارجی اجباری است.')
            # اگر پاسپورت دارد، کد ملی نباید وارد شود
            if national_code:
                self.add_error('national_code', 'برای اتباع خارجی، کد ملی نباید وارد شود.')
        
        return cleaned_data
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی'
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']
        labels = {
            'image': 'عکس پروفایل'
        }

class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'    