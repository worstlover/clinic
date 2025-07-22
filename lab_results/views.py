# D:\final\lab_results\views.py

from django.shortcuts import render, get_object_or_404
import pandas as pd
import jdatetime
import os
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.utils.translation import gettext_lazy 
import traceback 

# فرض می‌کنیم مدل Patient در اپلیکیشن 'core' قرار دارد.
from core.models import Patient 
# مدل‌های مربوط به اپلیکیشن lab_results
from .models import (
    PeriodicExamination, ClinicalMeasurement, TestType, LabParameterResult, 
    EXAMINATION_SECTION_CHOICES, ExaminationDetail, OptometryResult, AudiometryResult, SpirometryResult, 
    ECGResult, SonographyResult
)

# --- توابع کمکی (Helper Functions) ---

def convert_jalali_to_gregorian(jalali_date_str):
    """
    تبدیل تاریخ شمسی (YYYY/MM/DD یا YYYY-MM-DD) به آبجکت تاریخ میلادی.
    """
    if pd.isna(jalali_date_str) or not jalali_date_str:
        return None
    try:
        j_datetime_obj = jdatetime.datetime.strptime(str(jalali_date_str).strip(), '%Y/%m/%d')
        return j_datetime_obj.togregorian().date()
    except ValueError:
        try:
            j_datetime_obj = jdatetime.datetime.strptime(str(jalali_date_str).strip(), '%Y-%m-%d')
            return j_datetime_obj.togregorian().date()
        except ValueError:
            try:
                # Fallback for year-only format if applicable, assuming Jan 1st
                year_part = str(jalali_date_str).strip().split('/')[0]
                if year_part.isdigit():
                    year = int(year_part)
                    return jdatetime.date(year, 1, 1).togregorian()
                return None
            except Exception:
                return None


def convert_persian_to_english_nums(text):
    """
    تبدیل ارقام فارسی در یک رشته به ارقام انگلیسی.
    """
    if text is None:
        return None
    text = str(text) 
    persian_to_english_map = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    }
    translated_text = ''.join(persian_to_english_map.get(char, char) for char in text)
    return translated_text.strip()


# --- نگاشت ستون‌های اکسل به فیلدهای مدل‌های جنگو ---

# نگاشت ستون‌های اکسل به فیلدهای مدل Patient
# فیلدهای سوابق بیماری و حساسیت ها به صورت دستی در بخش پردازش تجمیع می شوند
# فیلدهای 'محل تولد', 'وضعیت تاهل', 'تعداد فرزندان', 'تحصیلات' در مدل Patient شما وجود ندارند.
# اگر نیاز دارید اینها وارد شوند، باید ابتدا آنها را به مدل Patient اضافه کنید.
patient_column_map = {
    'کد ملی': 'national_code',
    'شماره پاسپورت': 'passport_number',
    'نام': 'first_name',
    'نام خانوادگی': 'last_name',
    'نام پدر': 'father_name',
    'جنسیت': 'gender', 
    'تاریخ تولد': 'date_of_birth', 
    'موبایل': 'phone_number', # اطمینان از نگاشت صحیح
    'آدرس': 'address',
    'شغل': 'occupation', 
    'گروه خونی': 'blood_type',
}

# نگاشت ستون‌های اکسل به فیلدهای مدل PeriodicExamination
periodic_exam_column_map = {
    'تاریخ معاینه': 'exam_date', 
    'تاریخ پذیرش': 'admission_date', # اطمینان از نگاشت صحیح
    'ویزیت پزشک': 'final_opinion_doctor', 
    'نظریه نهایی - نظریه': 'final_opinion_conditions',
    'نظریه نهایی - شروط': 'final_opinion_description', 
    'تاریخ نظر نهایی': 'final_opinion_date', 
    'معاینات - علائم و توضیحات ثبت شده': 'overall_notes', 
}

# نگاشت ستون‌های اکسل به فیلدهای مدل ClinicalMeasurement
clinical_measurement_column_map = {
    'اندازه‌گیری‌های بالینی - وزن': 'weight',
    'اندازه‌گیری‌های بالینی - قد': 'height',
    'اندازه‌گیری‌های بالینی - BMI': 'bmi',
    'اندازه‌گیری‌های بالینی - فشارخون سیستولیک': 'systolic_bp', 
    'اندازه‌گیری‌های بالینی - فشارخون دیاستولیک': 'diastolic_bp', 
    'اندازه‌گیری‌های بالینی - نبض': 'pulse',
}

# نگاشت ستون‌های اکسل به نام‌های TestType برای LabParameterResult
lab_parameter_columns_map = {
    'نتایج آزمایش - Lipid Panel - Chol': 'Cholesterol', 
    'نتایج آزمایش - Lipid Panel - TG': 'Triglycerides',
    'نتایج آزمایش - Lipid Panel - HDL': 'HDL',
    'نتایج آزمایش - Lipid Panel - LDL': 'LDL',
    'نتایج آزمایش - Lipid Panel - VLDL': 'VLDL',
    'نتایج آزمایش - Lipid Panel - LDL / HDL': 'LDL/HDL Ratio',
    'نتایج آزمایش - Diabetes Screening - FBS': 'FBS',
    'نتایج آزمایش - Kidney Function - Creat': 'Creatinine',
    'نتایج آزمایش - Liver Function - AST': 'AST',
    'نتایج آزمایش - Liver Function - ALT': 'ALT',
    'نتایج آزمایش - CBC - RBC': 'RBC',
    'نتایج آزمایش - CBC - WBC': 'WBC',
    'نتایج آزمایش - CBC - Hb': 'Hemoglobin',
    'نتایج آزمایش - CBC - Hct': 'Hematocrit',
    'نتایج آزمایش - CBC - Plt': 'Platelets',
    'نتایج آزمایش - Urinalysis - Urine - Color': 'Urine Color',
    'نتایج آزمایش - Urinalysis - Urine - WBC': 'Urine WBC',
    'نتایج آزمایش - Thyroid Function - T4': 'T4',
    'نتایج آزمایش - Thyroid Function - T3': 'T3',
    'نتایج آزمایش - Thyroid Function - TSH': 'TSH',
}

# نگاشت ستون‌های اکسل به فیلدهای مدل ExaminationDetail
# استفاده از EXAMINATION_SECTION_CHOICES از مدل
examination_detail_columns_map = {
    'معاینات - عمومی - Sign': ('general', 'sign'),
    'معاینات - عمومی - Symptom': ('general', 'symptom'),
    'معاینات - عمومی - توضیحات': ('general', 'notes'), 
    
    'معاینات - چشم - Sign': ('eye', 'sign'), 
    'معاینات - چشم - Symptom': ('eye', 'symptom'),
    'معاینات - چشم - توضیحات': ('eye', 'notes'),

    'معاینات - پوست، مو و ناخن - Sign': ('skin_hair_nails', 'sign'),
    'معاینات - پوست، مو و ناخن - Symptom': ('skin_hair_nails', 'symptom'),
    'معاینات - پوست، مو و ناخن - توضیحات': ('skin_hair_nails', 'notes'),

    'معاینات - گوش، حلق، بینی و دهان - Sign': ('ent', 'sign'), 
    'معاینات - گوش، حلق، بینی و دهان - Symptom': ('ent', 'symptom'),
    'معاینات - گوش، حلق، بینی و دهان - توضیحات': ('ent', 'notes'),

    'معاینات - سر و گردن - Sign': ('head_neck', 'sign'),
    'معاینات - سر و گردن - Symptom': ('head_neck', 'symptom'),
    'معاینات - سر و گردن - توضیحات': ('head_neck', 'notes'),

    'معاینات - ریه - Sign': ('lung', 'sign'),
    'معاینات - ریه - Symptom': ('lung', 'symptom'),
    'معاینات - ریه - توضیحات': ('lung', 'notes'),

    'معاینات - قلب و عروق - Sign': ('cardiovascular', 'sign'),
    'معاینات - قلب و عروق - Symptom': ('cardiovascular', 'symptom'),
    'معاینات - قلب و عروق - توضیحات': ('cardiovascular', 'notes'),

    'معاینات - شکم و لگن - Sign': ('abdomen_pelvis', 'sign'),
    'معاینات - شکم و لگن - Symptom': ('abdomen_pelvis', 'symptom'),
    'معاینات - شکم و لگن - توضیحات': ('abdomen_pelvis', 'notes'),

    'معاینات - کلیه و مجاری ادراری، تناسلی - Sign': ('urinary_genital', 'sign'), 
    'معاینات - کلیه و مجاری ادراری، تناسلی - Symptom': ('urinary_genital', 'symptom'),
    'معاینات - کلیه و مجاری ادراری، تناسلی - توضیحات': ('urinary_genital', 'notes'),

    'معاینات - اسکلتی و عضلانی - Sign': ('musculoskeletal', 'sign'), 
    'معاینات - اسکلتی و عضلانی - Symptom': ('musculoskeletal', 'symptom'),
    'معاینات - اسکلتی و عضلانی - توضیحات': ('musculoskeletal', 'notes'),

    'معاینات - سیستم عصبی - Sign': ('nervous_system', 'sign'),
    'معاینات - سیستم عصبی - Symptom': ('nervous_system', 'symptom'),
    'معاینات - سیستم عصبی - توضیحات': ('nervous_system', 'notes'),

    'معاینات - اعصاب و روان - Sign': ('psychiatric', 'sign'), 
    'معاینات - اعصاب و روان - Symptom': ('psychiatric', 'symptom'),
    'معاینات - اعصاب و روان - توضیحات': ('psychiatric', 'notes'),

    'معاینات - undefined - Sign': ('undefined', 'sign'), 
    'معاینات - undefined - Symptom': ('undefined', 'symptom'),
    'معاینات - undefined - توضیحات': ('undefined', 'notes'),
}

# نگاشت ستون‌های اکسل به فیلدهای مدل OptometryResult
optometry_column_map = {
    'اپتومتری - حدت بینایی - دید دور - R - بدون اصلاح': 'va_distant_r_uncorrected',
    'اپتومتری - حدت بینایی - دید دور - L - بدون اصلاح': 'va_distant_l_uncorrected',
    'اپتومتری - حدت بینایی - دید دور - دوچشمی - بدون اصلاح': 'va_distant_ou_uncorrected',
    'اپتومتری - حدت بینایی - دید دور - R - با اصلاح': 'va_distant_r_corrected',
    'اپتومتری - حدت بینایی - دید دور - L - با اصلاح': 'va_distant_l_corrected',
    'اپتومتری - حدت بینایی - دید دور - دوچشمی - با اصلاح': 'va_distant_ou_corrected',
    'اپتومتری - حدت بینایی - دید دور - FC - R': 'va_distant_fc_r', 
    'اپتومتری - حدت بینایی - دید دور - FC - L': 'va_distant_fc_l', 
    'اپتومتری - حدت بینایی - دید دور - FC - دوچشمی': 'va_distant_fc_ou', 
    'اپتومتری - حدت بینایی - دید دور - HM - R': 'va_distant_hm_r', 
    'اپتومتری - حدت بینایی - دید دور - HM - L': 'va_distant_hm_l', 
    'اپتومتری - حدت بینایی - دید دور - HM - دوچشمی': 'va_distant_hm_ou', 
    'اپتومتری - حدت بینایی - دید دور - LP - R': 'va_distant_lp_r', 
    'اپتومتری - حدت بینایی - دید دور - LP - L': 'va_distant_lp_l', 
    'اپتومتری - حدت بینایی - دید دور - LP - دوچشمی': 'va_distant_lp_ou', 
    'اپتومتری - دید رنگی - R': 'color_vision_r', 
    'اپتومتری - دید رنگی - L': 'color_vision_l', 
    'اپتومتری - دید رنگی - Field Test - R': 'color_vision_field_r', 
    'اپتومتری - دید رنگی - Field Test - L': 'color_vision_field_l', 
    'اپتومتری - دید رنگی - Test Type': 'color_vision_test_type', 
    'اپتومتری - میدان بینایی - R': 'visual_field_r', 
    'اپتومتری - میدان بینایی - L': 'visual_field_l', 
    'اپتومتری - میدان بینایی - Test Type': 'visual_field_test_type', 
    'اپتومتری - عمق دید (ثانیه آرک)': 'depth_perception', 
    'اپتومتری - استفاده از عینک': 'uses_glasses', 
    'اپتومتری - استفاده از لنز طبی': 'uses_contact_lens', 
    'اپتومتری - توضیحات': 'notes', 
}

# نگاشت ستون‌های اکسل به فیلدهای مدل AudiometryResult
audiometry_column_map = {
    'اودیومتری - Right AC 125': 'right_ac_125',
    'اودیومتری - Right AC 250': 'right_ac_250',
    'اودیومتری - Right AC 500': 'right_ac_500',
    'اودیومتری - Right AC 1000': 'right_ac_1000',
    'اودیومتری - Right AC 2000': 'right_ac_2000',
    'اودیومتری - Right AC 3000': 'right_ac_3000',
    'اودیومتری - Right AC 4000': 'right_ac_4000',
    'اودیومتری - Right AC 6000': 'right_ac_6000',
    'اودیومتری - Right AC 8000': 'right_ac_8000',
    'اودیومتری - Right BC 500': 'right_bc_500',
    'اودیومتری - Right BC 1000': 'right_bc_1000',
    'اودیومتری - Right BC 2000': 'right_bc_2000',
    'اودیومتری - Right BC 3000': 'right_bc_3000',
    'اودیومتری - Right BC 4000': 'right_bc_4000',
    
    'اودیومتری - Left AC 500': 'left_ac_500', 
    'اودیومتری - Left AC 1000': 'left_ac_1000',
    'اودیومتری - Left AC 2000': 'left_ac_2000',
    'اودیومتری - Left AC 3000': 'left_ac_3000',
    'اودیومتری - Left AC 4000': 'left_ac_4000',
    'اودیومتری - Left AC 6000': 'left_ac_6000',
    'اودیومتری - Left AC 8000': 'left_ac_8000',
    'اودیومتری - Left BC 500': 'left_bc_500',
    'اودیومتری - Left BC 1000': 'left_bc_1000',
    'اودیومتری - Left BC 2000': 'left_bc_2000',
    'اودیومتری - Left BC 3000': 'left_bc_3000',
    'اودیومتری - Left BC 4000': 'left_bc_4000',

    'اودیومتری - Right Result': 'right_result', 
    'اودیومتری - Left Result': 'left_result', 
    'اودیومتری - Right Result Other': 'right_result_other', 
    'اودیومتری - Left Result Other': 'left_result_other', 
}

# نگاشت ستون‌های اکسل به فیلدهای مدل SpirometryResult
spirometry_column_map = {
    'اسپیرومتری - Result': 'result',
    'اسپیرومتری - Result Other': 'result_other', 
}

# نگاشت ستون‌های اکسل به فیلدهای مدل ECGResult
ecg_column_map = {
    'ECG - Diagnoses': 'diagnoses',
}

# نگاشت ستون‌های اکسل به فیلدهای مدل SonographyResult
sonography_column_map = {
    'سونوگرافی - نتیجه': 'result',
}


# --- View برای نمایش فرم آپلود اکسل ---
@require_GET
def upload_excel_file(request):
    """
    این تابع صرفاً صفحه آپلود فایل اکسل را رندر می‌کند.
    """
    return render(request, 'lab_results/upload.html')


# --- View برای پردازش و وارد کردن داده‌ها ---
@require_POST
def process_import(request):
    """
    این تابع مسئول خواندن فایل اکسل، پردازش ردیف‌ها و ذخیره داده‌ها در مدل‌های جنگو است.
    """
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, gettext_lazy("فایلی برای پردازش انتخاب نشده است."))
            return redirect('upload_excel_file') 
        
        errors = []
        success_count = 0
        current_user = request.user 

        try:
            df = pd.read_excel(excel_file)
            
            for index, row in df.iterrows():
                row_num = index + 2 
                
                try:
                    with transaction.atomic():
                        # --- 1. پردازش Patient (از اپ core) ---
                        patient_data = {}
                        
                        # پردازش فیلدهای عمومی بیمار
                        for excel_col, model_field in patient_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]): 
                                if model_field == 'date_of_birth':
                                    patient_data[model_field] = convert_jalali_to_gregorian(str(row[excel_col]))
                                elif model_field == 'gender':
                                    gender_val = str(row[excel_col]).strip()
                                    if gender_val == 'مرد': patient_data[model_field] = 'M'
                                    elif gender_val == 'زن': patient_data[model_field] = 'F'
                                    else: patient_data[model_field] = None
                                # اعمال تبدیل اعداد فارسی برای فیلدهای عددی مهم مانند شماره تماس و کد ملی
                                elif model_field in ['national_code', 'passport_number', 'phone_number']: # اضافه شده phone_number
                                    patient_data[model_field] = convert_persian_to_english_nums(row[excel_col])
                                else:
                                    patient_data[model_field] = row[excel_col]

                        # --- تجمیع فیلدهای سوابق بیماری و حساسیت‌ها ---
                        # استفاده از نام فیلدهای واقعی در مدل Patient: medical_history و allergies
                        
                        medical_history_parts = []
                        if 'سابقه شخصی - 1. سابقه بیماری' in row and pd.notna(row['سابقه شخصی - 1. سابقه بیماری']):
                            medical_history_parts.append("سابقه بیماری: " + str(row['سابقه شخصی - 1. سابقه بیماری']).strip())
                        if 'سابقه شخصی - 6. سابقه بستری' in row and pd.notna(row['سابقه شخصی - 6. سابقه بستری']):
                            medical_history_parts.append("سابقه بستری: " + str(row['سابقه شخصی - 6. سابقه بستری']).strip())
                        if 'سابقه شخصی - 7. سابقه عمل جراحی' in row and pd.notna(row['سابقه شخصی - 7. سابقه عمل جراحی']):
                            medical_history_parts.append("سابقه عمل جراحی: " + str(row['سابقه شخصی - 7. سابقه عمل جراحی']).strip())
                        
                        if medical_history_parts:
                            patient_data['medical_history'] = "\n".join(medical_history_parts)

                        if 'سابقه شخصی - 5. حساسیت به غذا، دارو یا ماده خاص' in row and pd.notna(row['سابقه شخصی - 5. حساسیت به غذا، دارو یا ماده خاص']):
                            patient_data['allergies'] = str(row['سابقه شخصی - 5. حساسیت به غذا، دارو یا ماده خاص']).strip()

                        # اطمینان از تبدیل اعداد فارسی برای national_code و passport_number قبل از استفاده
                        national_code = patient_data.get('national_code', '')
                        passport_number = patient_data.get('passport_number', '')

                        if not national_code and not passport_number:
                            raise ValueError(gettext_lazy("کد ملی یا شماره پاسپورت برای بیمار یافت نشد."))
                        
                        patient_obj = None
                        created_patient = False
                        
                        if national_code:
                            patient_obj, created_patient = Patient.objects.get_or_create(
                                national_code=national_code, 
                                defaults={**patient_data, 'registered_by': current_user}
                            )
                            if not created_patient:
                                for k, v in patient_data.items():
                                    if k != 'national_code' and pd.notna(v):
                                        setattr(patient_obj, k, v)
                                patient_obj.save()
                        elif passport_number:
                            patient_obj, created_patient = Patient.objects.get_or_create(
                                passport_number=passport_number, 
                                defaults={**patient_data, 'registered_by': current_user}
                            )
                            if not created_patient:
                                for k, v in patient_data.items():
                                    if k != 'passport_number' and pd.notna(v):
                                        setattr(patient_obj, k, v)
                                patient_obj.save()
                        
                        if not patient_obj:
                            raise ValueError(gettext_lazy(f"خطای ناشناخته در یافتن/ایجاد بیمار."))
                        
                        # --- 2. پردازش PeriodicExamination ---
                        periodic_exam_data = {
                            'patient': patient_obj,
                            'recorded_by': current_user,
                        }
                        
                        for excel_col, model_field in periodic_exam_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                if model_field in ['exam_date', 'admission_date', 'final_opinion_date']:
                                    periodic_exam_data[model_field] = convert_jalali_to_gregorian(str(row[excel_col]))
                                elif excel_col == 'توضیحات نهایی معاینه': 
                                    periodic_exam_data['final_opinion_conditions'] = row[excel_col] 
                                else:
                                    periodic_exam_data[model_field] = row[excel_col]

                        if 'exam_date' not in periodic_exam_data or periodic_exam_data['exam_date'] is None:
                            if 'admission_date' in periodic_exam_data and periodic_exam_data['admission_date'] is not None:
                                periodic_exam_data['exam_date'] = periodic_exam_data['admission_date']
                            else:
                                raise ValueError(gettext_lazy("تاریخ معاینه (exam_date) و تاریخ پذیرش (admission_date) هر دو یافت نشدند."))

                        if periodic_exam_data['exam_date'] is None: 
                             raise ValueError(gettext_lazy("تاریخ معاینه (exam_date) برای PeriodicExamination یافت نشد."))
                        
                        periodic_exam_obj, created_exam = PeriodicExamination.objects.get_or_create(
                            patient=patient_obj,
                            exam_date=periodic_exam_data['exam_date'], 
                            defaults=periodic_exam_data
                        )
                        if not created_exam:
                            for k, v in periodic_exam_data.items():
                                if k not in ['patient', 'exam_date'] and pd.notna(v):
                                    setattr(periodic_exam_obj, k, v)
                            periodic_exam_obj.save()

                        # --- بروزرسانی last_periodic_examination_date در مدل Patient ---
                        if patient_obj.last_periodic_examination_date is None or \
                           (periodic_exam_obj.exam_date and periodic_exam_obj.exam_date > patient_obj.last_periodic_examination_date):
                            patient_obj.last_periodic_examination_date = periodic_exam_obj.exam_date
                            patient_obj.save()
                        
                        # --- 3. پردازش ClinicalMeasurement ---
                        clinical_measurement_data = {}
                        for excel_col, model_field in clinical_measurement_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                if model_field in ['weight', 'height', 'bmi', 'systolic_bp', 'diastolic_bp', 'pulse']:
                                    val = convert_persian_to_english_nums(row[excel_col])
                                    try:
                                        if model_field in ['weight', 'height', 'bmi']: 
                                            clinical_measurement_data[model_field] = float(val)
                                        else: 
                                            clinical_measurement_data[model_field] = int(val)
                                    except ValueError:
                                        clinical_measurement_data[model_field] = None 
                                else:
                                    clinical_measurement_data[model_field] = row[excel_col]
                        
                        if clinical_measurement_data:
                            cleaned_data = {k: v for k, v in clinical_measurement_data.items() if v is not None and v != ''}
                            if cleaned_data: 
                                ClinicalMeasurement.objects.update_or_create(
                                    periodic_exam=periodic_exam_obj,
                                    defaults=cleaned_data 
                                )

                        # --- 4. پردازش LabParameterResult (نتایج آزمایشگاهی) ---
                        for excel_col, test_type_name in lab_parameter_columns_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                parameter_value = convert_persian_to_english_nums(str(row[excel_col]))
                                if not parameter_value: continue

                                test_type_obj, _ = TestType.objects.get_or_create(name=test_type_name)
                                LabParameterResult.objects.update_or_create(
                                    periodic_exam=periodic_exam_obj,
                                    test_type=test_type_obj,
                                    defaults={'result_value': parameter_value}
                                )

                        # --- 5. پردازش ExaminationDetail (جزئیات معاینات) ---
                        examination_details_by_section = {}
                        for excel_col, (section_choice, field_name) in examination_detail_columns_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                value = str(row[excel_col]).strip()
                                if not value: continue

                                if section_choice not in examination_details_by_section:
                                    examination_details_by_section[section_choice] = {}
                                
                                current_value = examination_details_by_section[section_choice].get(field_name, "")
                                if current_value:
                                    examination_details_by_section[section_choice][field_name] = f"{current_value}\n{value}"
                                else:
                                    examination_details_by_section[section_choice][field_name] = value

                        for section_choice, details_data in examination_details_by_section.items():
                            if details_data: 
                                ExaminationDetail.objects.update_or_create(
                                    periodic_exam=periodic_exam_obj,
                                    section=section_choice,
                                    defaults=details_data
                                )

                        # --- 6. پردازش مدل‌های تخصصی (Optometry, Audiometry, Spirometry, ECG, Sonography) ---
                        
                        # Optometry
                        optometry_data = {}
                        for excel_col, model_field in optometry_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                if model_field in ['uses_glasses', 'uses_contact_lens']:
                                    optometry_data[model_field] = str(row[excel_col]).lower() in ['بله', 'true', '1']
                                elif model_field == 'depth_perception': 
                                    val = convert_persian_to_english_nums(row[excel_col])
                                    try:
                                        optometry_data[model_field] = float(val)
                                    except ValueError:
                                        optometry_data[model_field] = None
                                else:
                                    optometry_data[model_field] = row[excel_col]
                        if optometry_data:
                            cleaned_data = {k: v for k, v in optometry_data.items() if v is not None and v != ''}
                            if cleaned_data:
                                OptometryResult.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=cleaned_data)

                        # Audiometry
                        audiometry_data = {}
                        for excel_col, model_field in audiometry_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                if model_field.startswith(('right_ac_', 'left_ac_', 'right_bc_', 'left_bc_')):
                                    val = convert_persian_to_english_nums(row[excel_col])
                                    try:
                                        audiometry_data[model_field] = int(val)
                                    except ValueError:
                                        audiometry_data[model_field] = None
                                else: 
                                    audiometry_data[model_field] = row[excel_col]

                        if audiometry_data:
                            cleaned_data = {k: v for k, v in audiometry_data.items() if v is not None and v != ''}
                            if cleaned_data:
                                AudiometryResult.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=cleaned_data)

                        # Spirometry
                        spirometry_data = {}
                        for excel_col, model_field in spirometry_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                spirometry_data[model_field] = row[excel_col] 
                        if spirometry_data:
                            cleaned_data = {k: v for k, v in spirometry_data.items() if v is not None and v != ''}
                            if cleaned_data:
                                SpirometryResult.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=cleaned_data)

                        # ECG
                        ecg_data = {}
                        for excel_col, model_field in ecg_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                ecg_data[model_field] = row[excel_col]
                        if ecg_data:
                            cleaned_data = {k: v for k, v in ecg_data.items() if v is not None and v != ''}
                            if cleaned_data:
                                ECGResult.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=cleaned_data)

                        # Sonography
                        sonography_data = {}
                        for excel_col, model_field in sonography_column_map.items():
                            if excel_col in row and pd.notna(row[excel_col]):
                                sonography_data[model_field] = row[excel_col]
                        if sonography_data:
                            cleaned_data = {k: v for k, v in sonography_data.items() if v is not None and v != ''}
                            if cleaned_data:
                                SonographyResult.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=cleaned_data)


                        success_count += 1
                        print(f"--- ردیف {row_num} با موفقیت پردازش شد. تعداد موفقیت‌آمیز: {success_count} ---") 

                except Exception as e:
                    print(f"--- خطا در پردازش ردیف {row_num}: {e} ---") 
                    traceback.print_exc() 
                    errors.append(gettext_lazy(f"ردیف {row_num}: خطای پردازش: {e}"))
            
            print(f"--- فرآیند وارد کردن تکمیل شد. ردیف‌های موفق: {success_count}، خطاها: {len(errors)} ---")

            if errors:
                messages.warning(request, gettext_lazy(f"فایل با {len(errors)} خطا پردازش شد."))
                for err_msg in errors:
                    messages.error(request, err_msg)
            
            messages.success(request, gettext_lazy(f"فرآیند وارد کردن تکمیل شد. {success_count} ردیف با موفقیت وارد/به‌روزرسانی شد."))

        except pd.errors.EmptyDataError:
            print("--- EmptyDataError: فایل اکسل خالی است یا فرمت آن صحیح نیست. ---") 
            messages.error(request, gettext_lazy("فایل اکسل خالی است یا فرمت آن صحیح نیست."))
        except Exception as e:
            print(f"--- خطای کلی در خواندن یا پردازش فایل: {e} ---")
            traceback.print_exc() 
            messages.error(request, gettext_lazy(f"خطای کلی در خواندن یا پردازش فایل: {e}"))
        
        return redirect('upload_excel_file')
    
    return render(request, 'lab_results/upload.html')
@require_GET
def view_patient_lab_results(request, patient_id):
    """
    نمایش تمامی معاینات و نتایج آزمایشگاهی یک بیمار مشخص.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    # مرتب‌سازی معاینات از جدیدترین به قدیمی‌ترین
    periodic_examinations = PeriodicExamination.objects.filter(patient=patient).order_by('-exam_date')

    context = {
        'patient': patient,
        'periodic_examinations': periodic_examinations,
    }
    return render(request, 'lab_results/patient_lab_results.html', context)