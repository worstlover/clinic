from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import Visit, VisitItem, ReasonForVisit, TreatmentResult
from core.models import Patient
from persiantools.jdatetime import JalaliDateTime
from jalali_date import datetime2jalali
from datetime import datetime
from django.contrib.auth import get_user_model

# -----------------------------------------------------------------------------
# Visit Form
# -----------------------------------------------------------------------------
class VisitForm(forms.ModelForm):
    """
    فرم اصلی برای ثبت اطلاعات ویزیت بیمار.
    """
    visit_date_jalali = forms.CharField(
        label="تاریخ ویزیت (شمسی)",
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control jalali-date-picker', 'placeholder': 'YYYY/MM/DD HH:MM'})
    )
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all().order_by('last_name', 'first_name'),
        label="بیمار",
        widget=forms.Select(attrs={'class': 'form-control select2-patient', 'data-placeholder': 'جستجوی بیمار بر اساس نام، کد ملی یا پرسنلی...'})
    )

    reason_for_visit = forms.ModelChoiceField(
        queryset=ReasonForVisit.objects.filter(is_active=True),
        label="علت مراجعه",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    treatment_result = forms.ModelChoiceField(
        queryset=TreatmentResult.objects.filter(is_active=True),
        label="نتیجه درمان",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Visit
        # فیلدها را برای نمایش در قالب به صورت منطقی مرتب می‌کنیم.
        # ترتیب نهایی نمایش فیلدها (مثلا ۴ در ۴) به طراحی قالب HTML شما بستگی دارد.
        fields = [
            # اطلاعات اولیه
            'patient',
            'visit_date_jalali',
            'reason_for_visit',
            'incident_type',
            
            # اطلاعات حیاتی و فیزیکی
            'height_cm',
            'weight_kg',
            'blood_pressure',
            'heart_rate',
            'temperature',
            'blood_sugar',
            
            # نتایج و یادداشت‌ها
            'treatment_result',
            'ecg_interpretation',
            'notes',
        ]
        widgets = {
            'incident_type': forms.Select(attrs={'class': 'form-control'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_height_cm'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_weight_kg'}),
            'blood_pressure': forms.TextInput(attrs={'class': 'form-control'}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # در حالت ویرایش، تاریخ شمسی را مقداردهی اولیه می‌کنیم
        if self.instance and self.instance.pk:
            self.fields['patient'].queryset = Patient.objects.filter(pk=self.instance.patient.pk)
            if self.instance.visit_date:
                self.fields['visit_date_jalali'].initial = datetime2jalali(self.instance.visit_date).strftime('%Y/%m/%d %H:%M')
        else:
            # در حالت ایجاد، تاریخ فعلی را به عنوان مقدار اولیه قرار می‌دهیم
            self.fields['visit_date_jalali'].initial = datetime2jalali(datetime.now()).strftime('%Y/%m/%d %H:%M')

    def clean(self):
        cleaned_data = super().clean()
        visit_date_jalali_str = cleaned_data.get('visit_date_jalali')
        if visit_date_jalali_str:
            try:
                jalali_dt = JalaliDateTime.strptime(visit_date_jalali_str, '%Y/%m/%d %H:%M')
                cleaned_data['visit_date'] = jalali_dt.to_gregorian()
            except ValueError:
                self.add_error('visit_date_jalali', 'فرمت تاریخ و ساعت شمسی صحیح نیست. (مثال: 1403/04/12 15:30)')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.visit_date = self.cleaned_data.get('visit_date', instance.visit_date)
        if commit:
            instance.save()
        return instance

# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# VisitItemForm & FormSet
# -----------------------------------------------------------------------------
class VisitItemForm(forms.ModelForm):
    """
    فرم برای اضافه کردن آیتم‌های ویزیت (مانند داروها).
    """
    class Meta:
        model = VisitItem
        fields = ['drug', 'quantity', 'notes']
        widgets = {
            'drug': forms.Select(attrs={'class': 'form-control select2-drug'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'placeholder': 'ملاحظات مربوط به این دارو'}),
        }
        labels = { 'drug': 'دارو', 'quantity': 'تعداد', 'notes': 'ملاحظات'}

VisitItemFormSet = inlineformset_factory(
    Visit, VisitItem,
    form=VisitItemForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
