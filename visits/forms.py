from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import Visit, VisitItem, ReasonForVisit, TreatmentResult
from core.models import Patient
from persiantools.jdatetime import JalaliDateTime
from jalali_date import datetime2jalali
from datetime import datetime
from django.contrib.auth import get_user_model
import jdatetime
from drugs.models import Drug
# -----------------------------------------------------------------------------
# Visit Form
# -----------------------------------------------------------------------------
class VisitForm(forms.ModelForm):
    visit_date_jalali = forms.CharField(
        label="تاریخ ویزیت (شمسی)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1402/01/01 10:30'})
    )

    class Meta:
        model = Visit
        fields = [
            'patient', 'visit_date_jalali', 'reason_for_visit', 'incident_type',
            'height_cm', 'weight_kg', 'blood_pressure', 'heart_rate', 
            'temperature', 'blood_sugar', 'ecg_interpretation', 'treatment_result', 'notes'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['reason_for_visit'].required = True
        self.fields['treatment_result'].required = True
        
        # خالی کردن لیست اولیه برای جلوگیری از سنگینی (Load on Demand)
        if not self.is_bound and not self.instance.pk:
            self.fields['patient'].queryset = Patient.objects.none()
        elif self.instance.pk:
            self.fields['patient'].queryset = Patient.objects.filter(pk=self.instance.patient.pk)

        # تاریخ شمسی
        if self.instance and self.instance.pk and self.instance.visit_date:
            self.fields['visit_date_jalali'].initial = datetime2jalali(self.instance.visit_date).strftime('%Y/%m/%d %H:%M')
        else:
            self.fields['visit_date_jalali'].initial = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')

    def clean(self):
        cleaned_data = super().clean()
        jalali_str = cleaned_data.get('visit_date_jalali')
        if jalali_str:
            try:
                # تبدیل اعداد فارسی به انگلیسی قبل از پردازش (سمت سرور)
                persian_digits = '۰۱۲۳۴۵۶۷۸۹'
                english_digits = '0123456789'
                table = str.maketrans(persian_digits, english_digits)
                jalali_str = jalali_str.translate(table)
                
                date_obj = jdatetime.datetime.strptime(jalali_str, '%Y/%m/%d %H:%M')
                cleaned_data['visit_date'] = date_obj.togregorian()
            except ValueError:
                self.add_error('visit_date_jalali', 'فرمت تاریخ نامعتبر است.')
        return cleaned_data

class VisitItemForm(forms.ModelForm):
    class Meta:
        model = VisitItem
        fields = ['drug', 'quantity', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk:
            self.fields['drug'].queryset = Drug.objects.none()
        elif self.instance.pk:
            self.fields['drug'].queryset = Drug.objects.filter(pk=self.instance.drug.pk)

VisitItemFormSet = inlineformset_factory(Visit, VisitItem, form=VisitItemForm, extra=1, can_delete=True)
# VisitReferralForm
# -----------------------------------------------------------------------------
User = get_user_model()

class VisitReferralForm(forms.ModelForm):
    """
    فرم برای ارجاع ویزیت به کاربر دیگر.
    """
    class Meta:
        model = Visit
        fields = ['assigned_to']
        labels = {'assigned_to': 'ارجاع به کاربر'}
        widgets = {'assigned_to': forms.Select(attrs={'class': 'form-control'})}

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        if current_user:
            self.fields['assigned_to'].queryset = queryset.exclude(pk=current_user.pk)
        else:
            self.fields['assigned_to'].queryset = queryset

