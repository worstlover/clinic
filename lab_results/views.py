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
from django.db.models.functions import Trim 
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
from jalali_date import date2jalali
from core.models import Patient 
from .models import (
    PeriodicExamination, ClinicalMeasurement, TestType, LabParameterResult, 
    EXAMINATION_SECTION_CHOICES, ExaminationDetail, OptometryResult, AudiometryResult, SpirometryResult, 
    ECGResult, SonographyResult
)

# --- توابع کمکی (Helper Functions) ---

def format_national_id(nid):
    """
    کد ملی را به یک رشته ۱۰ رقمی با صفرهای پیشوندی تبدیل می‌کند.
    """
    if nid is None:
        return None
    nid_str = str(nid).strip()
    return nid_str.zfill(10)

def convert_jalali_to_gregorian(jalali_date_str):
    """
    تاریخ شمسی (با فرمت YYYY/MM/DD) را به تاریخ میلادی تبدیل می‌کند.
    """
    if not jalali_date_str:
        return None
    try:
        # فرض می‌کنیم فرمت ورودی YYYY/MM/DD است
        year, month, day = map(int, jalali_date_str.split('/'))
        # ایجاد شیء تاریخ شمسی
        jalali_date_obj = jdatetime.date(year, month, day)
        # تبدیل به تاریخ میلادی
        gregorian_date_obj = jalali_date_obj.togregorian()
        return gregorian_date_obj
    except ValueError:
        # در صورتی که فرمت تاریخ ورودی اشتباه باشد
        return None
# --- Views ---

def view_patient_lab_results(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    periodic_examinations = PeriodicExamination.objects.filter(patient=patient).order_by('-exam_date')
    
    final_opinions = PeriodicExamination.objects.annotate(
        opinion_clean=Trim('final_opinion_text')
    ).values_list('opinion_clean', flat=True).distinct().exclude(opinion_clean__exact='')

    # Loop through examinations to add jalali dates
    for exam in periodic_examinations:
        # Convert exam_date to Jalali
        if exam.exam_date:
            exam.jalali_exam_date = date2jalali(exam.exam_date).strftime('%Y/%m/%d')
        else:
            exam.jalali_exam_date = '-'

        # Convert admission_date to Jalali
        if exam.admission_date:
            exam.jalali_admission_date = date2jalali(exam.admission_date).strftime('%Y/%m/%d')
        else:
            exam.jalali_admission_date = '-'

        # Convert patient's date_of_birth to Jalali
        if exam.patient and exam.patient.date_of_birth:
            exam.patient.jalali_date_of_birth = date2jalali(exam.patient.date_of_birth).strftime('%Y/%m/%d')
        else:
            exam.patient.jalali_date_of_birth = '-'

    context = {
        'patient': patient,
        'periodic_examinations': periodic_examinations,
        'final_opinions': final_opinions,
    }
    return render(request, 'lab_results/patient_lab_results.html', context)

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

def to_bool(value):
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'بله', 'دارد')
    if isinstance(value, (int, float)):
        return bool(value)
    return False


# --- نگاشت ستون‌های اکسل به فیلدهای مدل‌های جنگو ---
# !!! بسیار مهم: نام ستون‌ها در این بخش باید دقیقا با نام ستون‌ها در فایل اکسل شما یکی باشد !!!
patient_column_map = {
    'کد ملی': 'national_code',
    'شماره پاسپورت': 'passport_number',
    'نام': 'first_name',
    'نام خانوادگی': 'last_name',
    'نام پدر': 'father_name',
    'جنسیت': 'gender', 
    'تاریخ تولد': 'date_of_birth', 
    'موبایل': 'phone_number',
    'آدرس': 'address',
    'شغل': 'occupation', 
    'گروه خونی': 'blood_type',
}

periodic_exam_column_map = {
    'تاریخ معاینه': 'exam_date', 
    'تاریخ پذیرش': 'admission_date',
    'ویزیت پزشک': 'final_opinion_doctor', 
    'نظریه نهایی - نظریه': 'final_opinion_text',
    'نظریه نهایی - شروط': 'final_opinion_conditions', # این ستون برای "دلیل نظر" استفاده خواهد شد
    'تاریخ نظر نهایی': 'final_opinion_date', 
    'معاینات - علائم و توضیحات ثبت شده': 'overall_notes', 
}

# (سایر mapping ها بدون تغییر باقی می‌مانند)
# ...
clinical_measurement_column_map = {
    'اندازه‌گیری‌های بالینی - وزن': 'weight',
    'اندازه‌گیری‌های بالینی - قد': 'height',
    'اندازه‌گیری‌های بالینی - BMI': 'bmi',
    'اندازه‌گیری‌های بالینی - فشارخون سیستولیک': 'systolic_bp', 
    'اندازه‌گیری‌های بالینی - فشارخون دیاستولیک': 'diastolic_bp', 
    'اندازه‌گیری‌های بالینی - نبض': 'pulse',
}
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
examination_detail_columns_map = {
    'معاینات - عمومی - Sign': ('general', 'sign'),
    'معاینات - عمومی - Symptom': ('general', 'symptom'),
    'معاینات - عمومی - توضیحات': ('general', 'notes'), 
    'معاینات - چشم - Sign': ('eye', 'sign'), 
    'معاینات - چشم - Symptom': ('eye', 'symptom'),
    'معاینات - چشم - توضیحات': ('eye', 'notes'),
    'معاینات - پوست، مو و ناخن - Sign': ('skin_hair_nails', 'sign'),
    'معاینات - پوست، مو و ناavin - Symptom': ('skin_hair_nails', 'symptom'),
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
    'اپتometry - دید رنگی - Field Test - L': 'color_vision_field_l', 
    'اپتومتری - دید رنگی - Test Type': 'color_vision_test_type', 
    'اپتومتری - میدان بینایی - R': 'visual_field_r', 
    'اپتومتری - میدان بینایی - L': 'visual_field_l', 
    'اپتومتری - میدان بینایی - Test Type': 'visual_field_test_type', 
    'اپتومتری - عمق دید (ثانیه آرک)': 'depth_perception', 
    'اپتومتری - استفاده از عینک': 'uses_glasses', 
    'اپتومتری - استفاده از لنز طبی': 'uses_contact_lens', 
    'اپتومتری - توضیحات': 'notes', 
}
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
spirometry_column_map = {
    'اسپیرومتری - Result': 'result',
    'اسپیرومتری - Result Other': 'result_other', 
}
ecg_column_map = {
    'ECG - Diagnoses': 'diagnoses',
}
sonography_column_map = {
    'سونوگرافی - نتیجه': 'result',
}


@require_GET
def upload_excel_file(request):
    return render(request, 'lab_results/upload.html')


@require_POST
def process_import(request):
    excel_file = request.FILES.get('excel_file')
    if not excel_file:
        messages.error(request, "فایلی انتخاب نشده است.")
        return redirect('lab_results:upload_excel_file')

    errors, success_count, updated_count = [], 0, 0
    current_user = request.user

    try:
        df = pd.read_excel(excel_file)
        
        for index, row in df.iterrows():
            row_num = index + 2
            try:
                with transaction.atomic():
                    # ۱. پردازش بیمار (Patient)
                    patient_data = {'registered_by': current_user}
                    for col, field in patient_column_map.items():
                        if col in row and pd.notna(row[col]):
                            val = row[col]
                            if field == 'date_of_birth': 
                                patient_data[field] = convert_jalali_to_gregorian(val)
                            elif field == 'gender': 
                                patient_data[field] = 'M' if str(val).strip() == 'مرد' else ('F' if str(val).strip() == 'زن' else None)
                            elif field in ['national_code', 'personnel_number', 'phone_number']: 
                                patient_data[field] = convert_persian_to_english_nums(val)
                            else: 
                                patient_data[field] = val
                    
                    # --- CHANGE START: فرمت کردن کد ملی ---
                    national_code_raw = patient_data.get('national_code')
                    if not national_code_raw: 
                        raise ValueError("کد ملی الزامی است.")
                    
                    national_code = format_national_id(national_code_raw)
                    # --- CHANGE END ---
                    
                    # به روز رسانی یا ایجاد بیمار بر اساس کد ملی فرمت شده
                    patient_obj, created = Patient.objects.update_or_create(
                        national_code=national_code,
                        defaults={k: v for k, v in patient_data.items() if v is not None and k != 'national_code'}
                    )
                    
                    # ۳. پردازش معاینه دوره‌ای (PeriodicExamination)
                    exam_data = {'patient': patient_obj, 'recorded_by': current_user}
                    for col, field in periodic_exam_column_map.items():
                        if col in row and pd.notna(row[col]):
                            val = row[col]
                            if field.endswith('_date'): 
                                exam_data[field] = convert_jalali_to_gregorian(val)
                            else:
                                exam_data[field] = str(val).strip()
                            
                    if not exam_data.get('exam_date'): 
                        raise ValueError("تاریخ معاینه الزامی است.")
                    
                    periodic_exam_obj, _ = PeriodicExamination.objects.update_or_create(
                        patient=patient_obj, exam_date=exam_data['exam_date'],
                        defaults={k: v for k, v in exam_data.items() if v is not None}
                    )
                    
                    # --- پردازش سایر مدل‌ها (بدون تغییر) ---
                    # ۴. پردازش اندازه‌گیری‌های بالینی (ClinicalMeasurement)
                    clinical_data = {}
                    for col, field in clinical_measurement_column_map.items():
                        if col in row and pd.notna(row[col]):
                            clinical_data[field] = convert_persian_to_english_nums(row[col])
                    if clinical_data:
                        ClinicalMeasurement.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=clinical_data)

                    # ۵. پردازش نتایج آزمایشگاهی (LabParameterResult)
                    for col, test_name in lab_parameter_columns_map.items():
                        if col in row and pd.notna(row[col]):
                            test_type, _ = TestType.objects.get_or_create(name=test_name)
                            LabParameterResult.objects.update_or_create(
                                periodic_exam=periodic_exam_obj, test_type=test_type,
                                defaults={'result_value': convert_persian_to_english_nums(row[col])}
                            )

                    # ۶. پردازش جزئیات معاینات (ExaminationDetail)
                    for col, (section, field) in examination_detail_columns_map.items():
                        if col in row and pd.notna(row[col]):
                             obj, _ = ExaminationDetail.objects.get_or_create(periodic_exam=periodic_exam_obj, section=section)
                             setattr(obj, field, str(row[col]))
                             obj.save()

                    # ۷. پردازش بینایی‌سنجی (OptometryResult)
                    optometry_data = {}
                    for col, field in optometry_column_map.items():
                        if col in row and pd.notna(row[col]):
                            val = row[col]
                            if field.startswith('uses_'): optometry_data[field] = to_bool(val)
                            else: optometry_data[field] = val
                    if optometry_data:
                        OptometryResult.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=optometry_data)

                    # ۸. پردازش شنوایی‌سنجی (AudiometryResult)
                    audiometry_data = {}
                    for col, field in audiometry_column_map.items():
                        if col in row and pd.notna(row[col]):
                            if field.startswith(('right_', 'left_')):
                                audiometry_data[field] = convert_persian_to_english_nums(row[col])
                            else:
                                audiometry_data[field] = row[col]
                    if audiometry_data:
                        AudiometryResult.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=audiometry_data)

                    # ۹. پردازش اسپیرومتری, نوار قلب و سونوگرافی
                    specialty_maps = {
                        SpirometryResult: spirometry_column_map,
                        ECGResult: ecg_column_map,
                        SonographyResult: sonography_column_map
                    }
                    for model_class, column_map in specialty_maps.items():
                        model_data = {}
                        for col, field in column_map.items():
                            if col in row and pd.notna(row[col]):
                                model_data[field] = row[col]
                        if model_data:
                            model_class.objects.update_or_create(periodic_exam=periodic_exam_obj, defaults=model_data)
                    
                    if created:
                        success_count += 1
                    else:
                        updated_count += 1
            
            except Exception as e:
                errors.append(f"ردیف {row_num}: {e}")
                print(f"خطا در ردیف {row_num}: {e}")
                traceback.print_exc()

        # نمایش پیام نهایی
        if errors:
            messages.warning(request, f"فایل با {len(errors)} خطا پردازش شد.")
            for err in errors[:5]: messages.error(request, err)
        
        success_message = f"فرآیند تکمیل شد. {success_count} ردیف جدید با موفقیت وارد و {updated_count} ردیف موجود به‌روزرسانی شد."
        messages.success(request, success_message)

    except Exception as e:
        messages.error(request, f"خطای کلی در خواندن یا پردازش فایل: {e}")
        traceback.print_exc()
    
    return redirect('lab_results:upload_excel_file')

def view_patient_lab_results(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    periodic_examinations = PeriodicExamination.objects.filter(patient=patient).order_by('-exam_date')
    # Start of CHANGE
    final_opinions = PeriodicExamination.objects.annotate(
        opinion_clean=Trim('final_opinion_text')
    ).values_list('opinion_clean', flat=True).distinct().exclude(opinion_clean__exact='')
    # End of CHANGE
    context = {'patient': patient, 'periodic_examinations': periodic_examinations, 'final_opinions': final_opinions} # Added final_opinions to context
    return render(request, 'lab_results/patient_lab_results.html', context)
def generate_opinion_form(request, exam_id):
    examination = get_object_or_404(PeriodicExamination, id=exam_id)
    patient = examination.patient
    if request.method == 'POST':
        health_expert_name = request.POST.get('health_expert_name', '')
        safety_expert_name = request.POST.get('safety_expert_name', '')
        context = {
            'examination': examination, 'patient': patient,
            'health_expert_name': health_expert_name, 'safety_expert_name': safety_expert_name,
        }
        return render(request, 'lab_results/printable_opinion_form.html', context)
    context = {'examination': examination, 'patient': patient}
    return render(request, 'lab_results/opinion_form_input.html', context)

def handle_uploaded_file(f, directory="signatures"):
    if not f:
        return None
    fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, directory))
    filename = fs.save(f.name, f)
    return fs.url(filename)

def bulk_print_page(request):
    examinations_query = PeriodicExamination.objects.select_related('patient').order_by('patient__personnel_number', 'exam_date')
    final_opinions = PeriodicExamination.objects.annotate(
        opinion_clean=Trim('final_opinion_text')
    ).values_list('opinion_clean', flat=True).distinct().exclude(opinion_clean__exact='')
    
    health_expert_name = ''
    safety_expert_name = ''
    factory_manager_name = ''
    health_expert_signature_url = None
    safety_expert_signature_url = None
    factory_manager_signature_url = None

    if request.method == 'POST' and 'filter' in request.POST:
        health_expert_name = request.POST.get('health_expert_name', '')
        safety_expert_name = request.POST.get('safety_expert_name', '')
        factory_manager_name = request.POST.get('factory_manager_name', '')

        health_expert_signature_file = request.FILES.get('health_expert_signature')
        safety_expert_signature_file = request.FILES.get('safety_expert_signature')
        factory_manager_signature_file = request.FILES.get('factory_manager_signature')
        health_expert_signature_url = handle_uploaded_file(health_expert_signature_file)
        safety_expert_signature_url = handle_uploaded_file(safety_expert_signature_file)
        factory_manager_signature_url = handle_uploaded_file(factory_manager_signature_file)

        opinion_filter = request.POST.get('final_opinion', '')
        opinion_source_departments = request.POST.getlist('opinion_source_department') 
        start_date_jalali = request.POST.get('start_date', '')
        end_date_jalali = request.POST.get('end_date', '')
        start_pid = request.POST.get('start_pid', '')
        end_pid = request.POST.get('end_pid', '')
        job = request.POST.get('job_title', '')
        nid = request.POST.get('national_id', '')

        start_date_gregorian = None
        end_date_gregorian = None
        try:
            if start_date_jalali:
                start_date_gregorian = convert_jalali_to_gregorian(start_date_jalali)
            if end_date_jalali:
                end_date_gregorian = convert_jalali_to_gregorian(end_date_jalali)
            
            if (start_date_jalali and not start_date_gregorian) or (end_date_jalali and not end_date_gregorian):
                raise ValueError("Invalid date format")

        except ValueError:
            messages.error(request, "فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY/MM/DD استفاده کنید.")
            examinations_query = PeriodicExamination.objects.none()
        
        if opinion_filter:
            examinations_query = examinations_query.filter(final_opinion_text__exact=opinion_filter)
        
        if start_date_gregorian and end_date_gregorian:
            examinations_query = examinations_query.filter(exam_date__range=[start_date_gregorian, end_date_gregorian])
        elif start_date_gregorian:
            examinations_query = examinations_query.filter(exam_date__gte=start_date_gregorian)
        elif end_date_gregorian:
            examinations_query = examinations_query.filter(exam_date__lte=end_date_gregorian)

        if start_pid:
            start_pid_en = convert_persian_to_english_nums(start_pid)
            if start_pid_en:
                examinations_query = examinations_query.filter(patient__personnel_number__gte=start_pid_en)
        if end_pid:
            end_pid_en = convert_persian_to_english_nums(end_pid)
            if end_pid_en:
                examinations_query = examinations_query.filter(patient__personnel_number__lte=end_pid_en)
        
        if job:
            examinations_query = examinations_query.filter(patient__occupation__icontains=job)
        
        if nid:
            nid_en = convert_persian_to_english_nums(nid)
            if nid_en:
                # --- CHANGE: فیلتر بر اساس کد ملی فرمت شده ---
                examinations_query = examinations_query.filter(patient__national_code__exact=format_national_id(nid_en))
        print(f"تعداد نتایج یافت شده: {examinations_query.count()}")
        for exam in examinations_query:
            if exam.exam_date:
                exam.jalali_exam_date = date2jalali(exam.exam_date).strftime('%Y/%m/%d')
            else:
                exam.jalali_exam_date = '-'
            
            if exam.patient and exam.patient.date_of_birth:
                exam.patient.jalali_date_of_birth = date2jalali(exam.patient.date_of_birth).strftime('%Y/%m/%d')
            else:
                exam.patient.jalali_date_of_birth = '-'
           
       
        
           #* **بررسی صحت `convert_jalali_to_gregorian`:** مطمئن شوید که تابع `convert_jalali_to_gregorian` به درستی تاریخ‌های شمسی را به میلادی تبدیل می‌کند. اگر این تبدیل اشتباه باشد، فیلترهای تاریخ کار نخواهند کرد. در حال حاضر، تعریف این تابع در کد شما وجود ندارد. اگر قبلاً در `views.py` یا جای دیگر تعریف شده، مطمئن شوید که درست کار می‌کند.
           #* **بررسی تبدیل `personnel_number` و `national_code`:** اطمینان حاصل کنید که `convert_persian_to_english_nums` و `format_national_id` به درستی کار می‌کنند و مقادیر درستی را برای فیلتر کردن تولید می‌کنند. یک `print` برای دیدن مقادیر ورودی و خروجی این توابع نیز می‌تواند مفید باشد.
        context = {
            'examinations': examinations_query,
            'final_opinions': final_opinions,
            'health_expert_name': health_expert_name,
            'safety_expert_name': safety_expert_name,
            'factory_manager_name': factory_manager_name,
            'health_expert_signature_url': health_expert_signature_url,
            'safety_expert_signature_url': safety_expert_signature_url,
            'factory_manager_signature_url': factory_manager_signature_url,
            'opinion_source_departments': opinion_source_departments,
            'form_values': request.POST 
        }
    else:
        context = {
            'examinations': None, 
            'final_opinions': final_opinions,
            'opinion_source_departments': ['physician'],
            'form_values': {}
        }
        
    return render(request, 'lab_results/bulk_print_page.html', context)