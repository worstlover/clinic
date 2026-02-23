from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import RawVisitScan  # مدلی که در مرحله قبل تعریف کردیم
from drugs.models import Drug     # استفاده از مدل دارو که ارسال کردید
# فرض بر اینکه مدل بیمار در core.models است
# from core.models import Patient 

from django.shortcuts import render, get_object_or_404, redirect
from .models import RawVisitScan
import re
from django.shortcuts import render, get_object_or_404
from .models import RawVisitScan
from drugs.models import Drug
import json
from django.db import transaction
from visits.models import Visit, VisitItem # نام مدل‌های خود را چک کنید
# from core.models import Patient
import re
import easyocr
import numpy as np
import cv2
from django.shortcuts import render, get_object_or_404
from .models import RawVisitScan
from drugs.models import Drug
import jdatetime
from django.db import transaction
from django.shortcuts import redirect
from django.contrib import messages
from core.models import Patient, Company
from visits.models import Visit, VisitItem
from rapidfuzz import process, fuzz
def preprocess_image(image_path):
    # خواندن تصویر
    img = cv2.imread(image_path)
    # تبدیل به خاکستری
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # افزایش کنتراست و حذف نویز
    processed_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return processed_img
def convert_to_en(text):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    table = str.maketrans(persian_digits, english_digits)
    return text.translate(table)







def final_confirm(request):
    if request.method == 'POST':
        # دریافت لیست داده‌ها از قالب results_preview
        national_codes = request.POST.getlist('national_code')
        names = request.POST.getlist('patient_name')
        drugs_json_list = request.POST.getlist('drugs_json')

        try:
            with transaction.atomic():
                for i in range(len(national_codes)):
                    n_code = national_codes[i]
                    full_name = names[i]
                    
                    # ۱. هندل کردن بیمار (Patient)
                    # جستجو بر اساس کد ملی (فیلد national_code در فرم شما)
                    patient = Patient.objects.filter(national_code=n_code).first()
                    
                    if not patient:
                        # تفکیک نام و نام خانوادگی برای ساخت بیمار جدید
                        name_parts = full_name.split(' ', 1)
                        f_name = name_parts[0]
                        l_name = name_parts[1] if len(name_parts) > 1 else "ثبت شده هوشمند"
                        
                        patient = Patient.objects.create(
                            first_name=f_name,
                            last_name=l_name,
                            national_code=n_code,
                            is_foreign_national=False, # پیش‌فرض طبق منطق فرم شما
                            is_monitored=False
                        )

                    # ۲. ثبت ویزیت (Visit) - هماهنگ با VisitForm شما
                    # فیلدهای اجباری reason_for_visit و treatment_result لحاظ شده‌اند
                    new_visit = Visit.objects.create(
                        patient=patient,
                        visit_date=timezone.now(), # ذخیره میلادی (جایگزین visit_date_jalali در مدل)
                        reason_for_visit="ثبت خودکار از طریق پردازش تصویر (AI)",
                        treatment_result="در حال بررسی",
                        incident_type='none', # مقدار پیش‌فرض
                        notes=f"استخراج شده در تاریخ {timezone.now()}"
                    )

                    # ۳. ثبت اقلام دارویی (VisitItem) - هماهنگ با VisitItemForm
                    if i < len(drugs_json_list):
                        try:
                            drugs_data = json.loads(drugs_json_list[i])
                            for d in drugs_data:
                                if d.get('id'): # فقط اگر دارو در دیتابیس Drug یافت شده باشد
                                    VisitItem.objects.create(
                                        visit=new_visit,
                                        drug_id=d['id'],
                                        quantity=d.get('qty', 1),
                                        notes=f"دوز استخراج شده: {d.get('dosage')}"
                                    )
                        except json.JSONDecodeError:
                            continue

            messages.success(request, f"تعداد {len(national_codes)} پرونده با موفقیت در سیستم ثبت و به وضعیت 'در حال بررسی' منتقل شد.")
            return redirect('visits:visit_list')

        except Exception as e:
            messages.error(request, f"خطا در ثبت نهایی اطلاعات: {str(e)}")
            return redirect('aiapp:upload')

    return redirect('aiapp:upload')
def upload_visit_scan(request):
    # اگر POST بود یعنی فایلی ارسال شده
    if request.method == 'POST':
        image = request.FILES.get('image')
        if image:
            scan_obj = RawVisitScan.objects.create(image=image)
            # بعد از ذخیره، دوباره همان صفحه را با شیء ذخیره شده نشان می‌دهیم
            return render(request, 'aiapp/upload.html', {'scan_obj': scan_obj})
    
    return render(request, 'aiapp/upload.html')

