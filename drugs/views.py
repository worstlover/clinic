from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q, Sum, F, Count, Case, When, Value, BooleanField
import sys
from django.db import transaction
import jdatetime
import datetime
from persiantools.jdatetime import JalaliDate
from .models import (Drug, DrugRequest, DrugRequestItem, PurchaseInvoice, PurchaseInvoiceItem, DrugBatch, Supplier, DrugRequestWorkflowLog)
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Sum, OuterRef, Subquery, F, Value, Case, IntegerField
from django.forms import inlineformset_factory
from django.utils import timezone
import datetime
from math import ceil
from django_select2.views import AutoResponseView
from .forms import DrugForm, DrugBarcodeFormSet
from .models import Drug, DrugRequest, DrugRequestItem, DrugRequestWorkflowLog
from .forms import DrugRequestAnalysisForm, DrugRequestForm, DrugRequestItemForm
from django.contrib.auth.models import User
# <<<<< تغییر کلیدی: ایمپورت مدل‌ها از اپ visits برای تحلیل مصرف >>>>>
from visits.models import VisitItem
from datetime import timedelta
from .forms import (
    DrugSearchForm,
    PurchaseInvoiceForm, PurchaseInvoiceItemForm,
    DrugForm, DrugBatchForm, SupplierForm,
    DrugRequestForm, DrugRequestItemFormset # اطمینان حاصل کنید که این خط فعال است و DrugRequestForm را ایمپورت می‌کند
)
from django.http import JsonResponse
from django.db import transaction
from django.forms import inlineformset_factory
from django.db.models import Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, F
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from core.models import Patient # فقط برای تست یا ارتباط احتمالی، در این اپ اصلی استفاده نمی‌شود.
from core.serializers import PatientSerializer, DrugSerializer # فقط برای تست یا ارتباط احتمالی
from django_filters.rest_framework import DjangoFilterBackend # pip install django-filter
from .filters import DrugFilter
import django.forms as forms
from .forms import PurchaseInvoiceForm, PurchaseInvoiceItemForm
from persiantools import digits 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import re
from datetime import datetime
from .models import Drug
from .utils import get_drug_info_from_ttac
import re
import datetime
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Drug, DrugBatch
from .forms import DrugReceiveForm
from didrug.views import process_drug_info 
from .models import DrugBarcode
from .serializers import SupplierSerializer, DrugSerializer
from django.db import transaction
from django.db.models import F
import jdatetime
from django.db.models import Sum, Count, Case, When, Value, IntegerField
@login_required
def find_drug_by_barcode_api(request):
    barcode = request.GET.get('barcode', None)
    if not barcode:
        return JsonResponse({'status': 'error', 'message': 'بارکد ارسال نشده است.'}, status=400)

    try:
        # جستجو در مدل بارکدها - استفاده از select_related برای سرعت بیشتر
        barcode_mapping = DrugBarcode.objects.select_related('drug').get(gtin=barcode)
        drug = barcode_mapping.drug
        
        return JsonResponse({
            'status': 'found',
            'drug_id': drug.pk,  # اسکنر به این نیاز دارد
            'drug_name': drug.name, # اسکنر به این نیاز دارد
            'message': f'داروی "{drug.name}" پیدا شد.'
        })
    except DrugBarcode.DoesNotExist:
        # برای اسکنر بهتر است 404 برگردانیم تا جاوااسکریپت خطا ندهد و پیام را نشان دهد
        return JsonResponse({
            'status': 'not_found',
            'drug_id': None,
            'message': 'این بارکد در سیستم ثبت نشده است.'
        }, status=404)


def receive_drug_view(request):
    if request.method == 'POST':
        try:
            supplier = Supplier.objects.get(pk=request.POST.get('supplier'))
            is_temporary = request.POST.get('is_temporary') == 'true'
            
            rows_data = {}
            for key, value in request.POST.items():
                match = re.match(r'rows\[(\d+)\]\[(.*)\]', key)
                if match:
                    row_index, field_name = match.groups()
                    if row_index not in rows_data:
                        rows_data[row_index] = {}
                    rows_data[row_index][field_name] = value
            for key, file in request.FILES.items():
                match = re.match(r'rows\[(\d+)\]\[(.*)\]', key)
                if match:
                    row_index, field_name = match.groups()
                    if row_index not in rows_data:
                        rows_data[row_index] = {}
                    rows_data[row_index][field_name] = file

            with transaction.atomic():
                for row_index, row_data in rows_data.items():
                    processed_data = process_drug_info(row_data)
                    drug_name = processed_data.get('persian_name')
                    expiry_date = processed_data.get('expiry_date')
                    qr_code_content = processed_data.get('qr_code_content')
                    quantity = int(row_data.get('quantity', 0))
                    
                    if not drug_name or not expiry_date:
                        continue 
                    
                    drug, created = Drug.objects.get_or_create(
                        name=drug_name,
                        defaults={}
                    )
                    
                    batch_number = qr_code_content # Assuming qr_code_content is the batch number
                    
                    try:
                        drug_batch = DrugBatch.objects.get(
                            drug=drug,
                            batch_number=batch_number,
                            is_temporary=is_temporary
                        )
                        drug_batch.add_stock(quantity)
                    except DrugBatch.DoesNotExist:
                        DrugBatch.objects.create(
                            drug=drug,
                            batch_number=batch_number,
                            expiry_date=expiry_date,
                            quantity=quantity,
                            supplier=supplier,
                            is_temporary=is_temporary,
                        )
                
            messages.success(request, 'تمامی ردیف‌ها با موفقیت پردازش و ثبت شدند!')
            return JsonResponse({'status': 'success', 'message': 'تمامی ردیف‌ها با موفقیت پردازش و ثبت شدند.'})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطایی در ثبت دسته‌ای رخ داد: {e}'}, status=500)
    
    else:
        suppliers = Supplier.objects.all()
        context = {
            'page_title': 'دریافت و ثبت دسته‌ای دارو',
            'suppliers': suppliers,
        }
        return render(request, 'drugs/receive_drug_form.html', context)

def load_drug_request(request):
    """
    loads drug items from a request and returns them as JSON.
    """
    if request.method == 'GET' and 'request_code' in request.GET:
        request_code = request.GET.get('request_code')
        try:
            drug_request = DrugRequest.objects.get(request_code=request_code)
            items = DrugRequestItem.objects.filter(drug_request=drug_request)
            
            # Format the data for a JSON response
            items_data = []
            for item in items:
                items_data.append({
                    'drug_name': item.drug.name,
                    'requested_quantity': item.requested_quantity,
                })
            
            return JsonResponse({
                'status': 'success',
                'items': items_data,
                'message': f'درخواست با شماره {request_code} با موفقیت بارگذاری شد.'
            })
        except DrugRequest.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'درخواستی با شماره {request_code} یافت نشد.'
            }, status=404)
    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر.'}, status=400)
@csrf_exempt
def add_drug_from_qr(request):
    context = {}

    if request.method == "POST":
        qr_code = request.POST.get("qr_code")
        quantity = request.POST.get("quantity")

        # --- مرحله دوم: ثبت نهایی با تعداد ---
        if quantity:
            try:
                with transaction.atomic():
                    drug_id = request.POST.get("drug_id")
                    lot_number = request.POST.get("lot_number")
                    expiry_date_str = request.POST.get("expiry_date")
                    quantity = int(quantity)

                    drug = Drug.objects.get(pk=drug_id)
                    expiry_date = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d").date()

                    batch, created = DrugBatch.objects.get_or_create(
                        drug=drug,
                        batch_number=lot_number,
                        expiry_date=expiry_date,
                        defaults={'quantity': quantity}
                    )

                    if not created:
                        batch.quantity += quantity
                        batch.save()
                        messages.info(request, f"موجودی بچ موجود برای داروی '{drug.name}' به تعداد {quantity} عدد افزایش یافت.")
                    else:
                        messages.success(request, f"بچ جدید برای داروی '{drug.name}' با تعداد {quantity} با موفقیت ثبت شد.")
                
                # پس از ثبت موفق، به صفحه خالی ریدایرکت می‌کنیم تا برای اسکن بعدی آماده باشد
                return redirect('drugs:add_drug_from_qr')

            except Exception as e:
                messages.error(request, f"خطا در ثبت نهایی بچ: {e}")
            
            return render(request, "drugs/add_drug_from_qr.html", {})

        # --- مرحله اول: اسکن و استعلام اطلاعات ---
        if qr_code:
            # ⭐️⭐️⭐️ شروع بخش اصلاح شده ⭐️⭐️⭐️
            match_gtin = re.search(r"01(\d{14})", qr_code)
            match_exp = re.search(r"17(\d{6})", qr_code)
            match_lot = re.search(r"10(\w+)", qr_code)

            if not match_gtin or not match_lot or not match_exp:
                context["error"] = "کد QR معتبر نیست یا فرمت آن پشتیبانی نمی‌شود. (GTIN, LOT, EXP مورد نیاز است)"
                return render(request, "drugs/add_drug_from_qr.html", context)
            
            # **نکته کلیدی:** تعریف متغیر lot_number قبل از استفاده
            lot_number = match_lot.group(1)
            exp_raw = match_exp.group(1)
            # ⭐️⭐️⭐️ پایان بخش اصلاح شده ⭐️⭐️⭐️
            
            try:
                year = int(exp_raw[0:2])
                year += 2000 if year < 70 else 1900
                day = int(exp_raw[4:6])
                if day == 0:
                    import calendar
                    month = int(exp_raw[2:4])
                    day = calendar.monthrange(year, month)[1]
                    expiration_date = datetime.date(year, month, day)
                else:
                    expiration_date = datetime.datetime.strptime(f"{year}{exp_raw[2:]}", "%Y%m%d").date()
            except ValueError:
                context["error"] = "فرمت تاریخ انقضا در QR کد نامعتبر است."
                return render(request, "drugs/add_drug_from_qr.html", context)

            drug_info_response = get_drug_info_from_ttac(qr_code)
            
            if drug_info_response.get("status") != "success":
                context["error"] = drug_info_response.get("message", "خطا در استعلام اطلاعات دارو از سامانه TTAC.")
                return render(request, "drugs/add_drug_from_qr.html", context)

            gtin_from_api = drug_info_response.get("gtin")
            if not gtin_from_api:
                context["error"] = "پاسخ دریافت شده از TTAC فاقد کد GTIN است."
                return render(request, "drugs/add_drug_from_qr.html", context)

            drug, created = Drug.objects.update_or_create(
                drug_code=gtin_from_api,
                defaults={
                    "name": drug_info_response.get("persianName", "نام نامشخص"),
                    "generic_name": drug_info_response.get("genericCode"),
                }
            )

            if created:
                messages.info(request, f"داروی جدید '{drug.name}' بر اساس اطلاعات سامانه TTAC در سیستم ثبت شد.")

            # حالا این خط بدون خطا اجرا می‌شود چون lot_number به عنوان مقدار پیش‌فرض وجود دارد
            lot_number_from_api = drug_info_response.get("batchCode", lot_number)

            context["scanned_data"] = {
                "drug": drug,
                "lot_number": lot_number_from_api,
                "expiry_date": expiration_date,
            }
            context["success_scan"] = "اطلاعات با موفقیت از سامانه مرکزی استعلام شد. لطفاً تعداد را وارد و ثبت کنید."

    return render(request, "drugs/add_drug_from_qr.html", context)
# from clinic_messages.models import Message, MessageRecipient # اینها مربوط به اپ clinic_messages هستند، اینجا لازم نیستند
DRUG_FORM_CHOICES = [
    ('tablet', 'قرص'),
    ('capsule', 'کپسول'),
    ('syrup', 'شربت'),
    ('injection', 'آمپول/تزریقی'),
    ('cream', 'کرم/پماد'),
    ('gel', 'ژل'),
    ('solution', 'محلول'),
    ('suspension', 'سوسپانسیون'),
    ('drops', 'قطره'),
    ('suppository', 'شیاف'),
    ('aerosol', 'اسپری/افشانه'),
    ('powder', 'پودر'),
    ('vial', 'ویال'),
    ('other', 'سایر'),
]
# --------------------------------------------------
# توابع مربوط به مدیریت داروها (Drug Management)
# --------------------------------------------------



@login_required
def drug_list(request):
    today = datetime.date.today()
    three_months_later = today + datetime.timedelta(days=90)

    # کوئری کامل برای نمایش در وب
    base_queryset = Drug.objects.annotate(
        total_stock=Sum('batches__quantity', default=0),
        # شمارش بچ‌های منقضی شده
        expired_count=Count(
            Case(When(batches__expiry_date__lt=today, batches__quantity__gt=0, then=Value(1))),
            distinct=True
        ),
        # شمارش بچ‌های نزدیک به انقضا (۳ ماه آینده)
        expiring_soon_count=Count(
            Case(When(batches__expiry_date__range=[today, three_months_later], batches__quantity__gt=0, then=Value(1))),
            distinct=True
        ),
        # اولویت‌بندی نمایش (قرص و شربت اول)
        form_priority=Case(
            When(form__icontains='قرص', then=Value(1)),
            When(form__icontains='شربت', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    )

    drug_filter = DrugFilter(request.GET, queryset=base_queryset)
    
    # مرتب‌سازی برای وب: ابتدا موارد بحرانی، سپس اولویت شکل، سپس حروف الفبا
    filtered_drugs = drug_filter.qs.order_by(
        F('expired_count').desc(),
        'form_priority',
        'name'
    )

    # صفحه‌بندی ۱۵ تایی برای وب
    paginator = Paginator(filtered_drugs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'drugs/drug_list.html', {
        'page_obj': page_obj,
        'filter': drug_filter,
    })
@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.add_drug', raise_exception=True)


@login_required
def drug_print_report(request):
    today = datetime.date.today()
    today_jalali = jdatetime.date.today().strftime("%Y/%m/%d")

    base_queryset = Drug.objects.annotate(
        total_stock=Sum('batches__quantity', default=0),
        expired_count=Count(
            Case(When(batches__expiry_date__lt=today, batches__quantity__gt=0, then=Value(1))),
            distinct=True
        ),
        form_priority=Case(
            When(form__icontains='قرص', then=Value(1)),
            When(form__icontains='شربت', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    )

    drug_filter = DrugFilter(request.GET, queryset=base_queryset)
    drugs = drug_filter.qs.order_by(F('expired_count').desc(), 'form_priority', 'form', 'name')

    # تبدیل نام فیلترها به فارسی برای نمایش در گزارش
    active_filters = []
    filter_labels = {
        'name': 'نام دارو',
        'drug_code': 'کد کالا',
        'form': 'شکل دارویی',
        'is_low_stock': 'کمبود موجودی',
        'has_expiring_batches': 'نزدیک انقضا',
        'no_barcode': 'بدون بارکد'
    }

    for key, value in request.GET.items():
        if value and value != '' and key in filter_labels:
            if value == 'on': # برای چک‌باکس‌ها
                active_filters.append(filter_labels[key])
            else:
                active_filters.append(f"{filter_labels[key]}: {value}")

    return render(request, 'drugs/drug_print_report.html', {
        'drugs': drugs,
        'today_jalali': today_jalali,
        'active_filters': active_filters,
    })

def drug_create_or_update(request, pk=None):
    drug_instance = get_object_or_404(Drug, pk=pk) if pk else None
    page_title = f'ویرایش داروی {drug_instance.name}' if drug_instance else 'افزودن داروی جدید'
    
    if request.method == 'POST':
        # نکته: ModelForm استاندارد آرگومان request نمی‌پذیرد.
        # اگر در فرم نیاز به user دارید، باید در save commit=False ست کنید.
        form = DrugForm(request.POST, instance=drug_instance)
        formset = DrugBarcodeFormSet(request.POST, instance=drug_instance)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    drug = form.save() # اگر فیلد drug_code اتوماتیک است، در مدل یا سیگنال هندل شود
                    
                    formset.instance = drug
                    formset.save()
                    
                    messages.success(request, f'داروی "{drug.name}" با موفقیت ذخیره شد.')
                    
                    next_url = request.GET.get('next')
                    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                    
                    # پیشنهاد: بعد از ذخیره جدید، برو به لیست. بعد از ویرایش، در همان صفحه بمان
                    if pk:
                        return redirect('drugs:drug_update', pk=drug.pk)
                    return redirect('drugs:drug_list')
                    
            except Exception as e:
                messages.error(request, f'خطا در تراکنش دیتابیس: {str(e)}')
        else:
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    
    else:
        form = DrugForm(instance=drug_instance)
        formset = DrugBarcodeFormSet(instance=drug_instance)

    context = {
        'page_title': page_title,
        'form': form,
        'formset': formset,
        'drug': drug_instance,
        'is_new_drug': drug_instance is None
    }
    return render(request, 'drugs/drug_form.html', context)


@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_drug', raise_exception=True)
def drug_detail(request, pk):
    drug = get_object_or_404(Drug, pk=pk)
    # اینجا drug.batches.all() را جایگزین drug.drugbatch_set.all() کنید
    batches = drug.batches.all().order_by('-expiry_date', '-created_at')
    
    # Calculate drug requests related to this drug
    drug_request_items = DrugRequestItem.objects.filter(drug=drug).order_by('-drug_request__request_date')
    
    context = {
        'page_title': f'جزئیات دارو: {drug.name}',
        'drug': drug,
        'batches': batches,
        'drug_request_items': drug_request_items,
    }
    return render(request, 'drugs/drug_detail.html', context)


@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.change_drug', raise_exception=True)
def drug_update(request, pk):
    drug = get_object_or_404(Drug, pk=pk)
    if request.method == 'POST':
        form = DrugForm(request.POST, instance=drug)
        if form.is_valid():
            form.save()
            messages.success(request, 'دارو با موفقیت ویرایش شد!')
            return redirect('drugs:drug_detail', pk=pk)
        else:
            messages.error(request, 'خطا در ویرایش دارو. لطفا اطلاعات را بررسی کنید.')
    else:
        form = DrugForm(instance=drug)
    context = {
        'page_title': f'ویرایش دارو: {drug.name}',
        'form': form
    }
    return render(request, 'drugs/drug_form.html', context)


@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.delete_drug', raise_exception=True)
def drug_delete(request, pk):
    drug = get_object_or_404(Drug, pk=pk)
    if request.method == 'POST':
        drug.delete()
        messages.success(request, 'دارو با موفقیت حذف شد!')
        return redirect('drugs:drug_list')
    context = {
        'page_title': 'حذف دارو',
        'object': drug
    }
    return render(request, 'confirm_delete.html', context) # استفاده از تمپلیت عمومی confirm_delete

# --------------------------------------------------
# توابع مربوط به مدیریت بچ‌های دارو (DrugBatch Management)
# --------------------------------------------------

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_drugbatch', raise_exception=True)
def drug_batch_list(request):
    batches = DrugBatch.objects.all().order_by('-expiry_date', '-created_at')
    
    query = request.GET.get('query')
    if query:
        batches = batches.filter(
            Q(drug__name__icontains=query) |
            Q(batch_number__icontains=query) |
            Q(supplier__name__icontains=query)
        )

    paginator = Paginator(batches, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'page_title': 'لیست بچ‌های دارو',
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, 'drugs/drug_batch_list.html', context)




@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.add_drugbatch', raise_exception=True)
def drug_batch_create(request):
    if request.method == 'POST':
        form = DrugBatchForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Save the form directly. This creates the DrugBatch instance
                # with the quantity entered by the user.
                # The Drug.total_quantity property will automatically reflect this addition.
                form.save() # <-- This is the corrected line
            messages.success(request, 'بچ دارو با موفقیت اضافه شد!')
            return redirect('drugs:drug_batch_list')
        else:
            messages.error(request, 'خطا در افزودن بچ دارو. لطفا اطلاعات را بررسی کنید.')
            print(form.errors)
    else:
        form = DrugBatchForm()
    context = {
        'page_title': 'افزودن بچ داروی جدید',
        'form': form
    }
    return render(request, 'drugs/drug_batch_form.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_drugbatch', raise_exception=True)
def drug_batch_detail(request, pk):
    batch = get_object_or_404(DrugBatch, pk=pk)
    context = {
        'page_title': f'جزئیات بچ دارو: {batch.batch_number or batch.drug.name}',
        'batch': batch
    }
    return render(request, 'drugs/drug_batch_detail.html', context)


@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.change_drugbatch', raise_exception=True)
def drug_batch_update(request, pk):
    batch = get_object_or_404(DrugBatch, pk=pk)
    # original_quantity = batch.quantity # No longer needed here

    if request.method == 'POST':
        form = DrugBatchForm(request.POST, instance=batch)
        if form.is_valid():
            with transaction.atomic():
                # Save the form directly. This updates the quantity of the specific batch.
                # The Drug.total_quantity property will automatically reflect this change.
                form.save() # <-- This is the corrected line
            
            messages.success(request, 'بچ دارو با موفقیت ویرایش و موجودی انبار به‌روزرسانی گردید!')
            return redirect('drugs:drug_batch_detail', pk=pk)
        else:
            messages.error(request, 'خطا در ویرایش بچ دارو. لطفا اطلاعات را بررسی کنید.')
            print(form.errors)
    else:
        form = DrugBatchForm(instance=batch)
    context = {
        'page_title': f'ویرایش بچ دارو: {batch.batch_number or batch.drug.name}',
        'form': form
    }
    return render(request, 'drugs/drug_batch_form.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.delete_drugbatch', raise_exception=True)
def drug_batch_delete(request, pk):
    batch = get_object_or_404(DrugBatch, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            # هنگام حذف بچ، باید موجودی دارو را به همان مقدار بچ حذف شده، کاهش دهیم.
            # این کار با فراخوانی remove_from_batches انجام می‌شود.
            # اگر این بچ تنها منبع موجودی باشد و سپس حذف شود، باید مراقب بود.
            # بهتر است ابتدا موجودی را کاهش دهیم سپس بچ را حذف کنیم.
            # اما در عمل، حذف یک بچ به معنی حذف آن مقدار از موجودی کل است.
            # DrugBatch.remove_from_batches(batch.drug, batch.quantity) # این خطا می‌دهد چون از خود بچ کم می‌کند نه از کل
            # ساده‌ترین راه این است که مدل Drug.total_quantity خودش را آپدیت کند.
            batch.delete() # حذف بچ به طور خودکار از total_quantity کم می‌کند
        messages.success(request, 'بچ دارو با موفقیت حذف شد!')
        return redirect('drugs:drug_batch_list')
    context = {
        'page_title': 'حذف بچ دارو',
        'object': batch
    }
    return render(request, 'confirm_delete.html', context)


# --------------------------------------------------
# توابع مربوط به مدیریت فاکتورهای خرید (PurchaseInvoice Management)
# --------------------------------------------------





# --- لیست فاکتورهای خرید ---
@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_purchaseinvoice', raise_exception=True)
def purchase_invoice_list(request):
    search_query = request.GET.get('query', '')
    
    if search_query:
        invoices_list = PurchaseInvoice.objects.filter(
            Q(invoice_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        ).order_by('-invoice_date', '-created_at')
    else:
        invoices_list = PurchaseInvoice.objects.all().order_by('-invoice_date', '-created_at')

    paginator = Paginator(invoices_list, 10) # 10 فاکتور در هر صفحه
    page = request.GET.get('page')

    try:
        invoices = paginator.page(page)
    except PageNotAnInteger:
        invoices = paginator.page(1)
    except EmptyPage:
        invoices = paginator.page(paginator.num_pages)

    context = {
        'page_title': 'لیست فاکتورهای خرید',
        'page_obj': invoices,
        'paginator': paginator,
        'search_query': search_query,
    }
    return render(request, 'drugs/purchase_invoice_list.html', context)






# --- Purchase Invoice Create View ---
def purchase_invoice_create(request):
    PurchaseInvoiceItemFormset = inlineformset_factory(
        PurchaseInvoice,
        PurchaseInvoiceItem,
        form=PurchaseInvoiceItemForm,
        extra=3, # مثلاً 3 آیتم خالی اولیه
        can_delete=True
    )

    if request.method == 'POST':
        form = PurchaseInvoiceForm(request.POST)
        formset = PurchaseInvoiceItemFormset(request.POST, prefix='items')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    invoice = form.save(commit=False)
                    invoice.created_by = request.user # اگر فیلد created_by دارید
                    invoice.save()
                    
                    # ذخیره آیتم‌های فرم‌ست.
                    # سیگنال‌های post_save در PurchaseInvoiceItem موجودی و total_item_price را مدیریت می‌کنند.
                    instances = formset.save(commit=False)
                    for item in instances:
                        item.invoice = invoice
                        item.save() # این save سیگنال post_save را برای هر آیتم فعال می کند

                    for obj in formset.deleted_objects:
                        obj.delete() # اگر آیتمی در فرم جدید حذف شده باشد (در update مهمتر است)

                    # پس از ذخیره آیتم‌ها و بروزرسانی موجودی در سیگنال‌ها،
                    # total_amount فاکتور را بروزرسانی کنید.
                    invoice.update_total_amount()
                    
                messages.success(request, 'فاکتور خرید با موفقیت ایجاد شد.')
                return redirect('drugs:purchase_invoice_detail', pk=invoice.pk)

            except Exception as e:
                messages.error(request, f'خطا در ایجاد فاکتور خرید: {e}. لطفا اطلاعات را بررسی کنید.')
                print(f"\n--- خطای کلی در تراکنش ایجاد: {e} ---")
                import traceback
                traceback.print_exc()

        else:
            messages.error(request, 'خطا در اعتبارسنجی اطلاعات فاکتور. لطفا اطلاعات را بررسی کنید.')
            print("\n--- خطاهای اعتبارسنجی فرم ---")
            print("خطاهای فرم اصلی (PurchaseInvoiceForm):", form.errors)
            if form.non_field_errors():
                print("خطاهای غیرفیلد فرم اصلی (PurchaseInvoiceForm Non-Field Errors):", form.non_field_errors())
            print("خطاهای فرم‌ست آیتم‌ها (PurchaseInvoiceItemFormset Errors):")
            for i, item_form in enumerate(formset):
                if item_form.errors:
                    print(f" - Item {i+1} Errors: {item_form.errors}")
            if formset.non_form_errors():
                print("خطاهای غیرفیلد فرم‌ست (Formset Non-Form Errors):", formset.non_form_errors())
            print("------------------------------\n")
    else:
        form = PurchaseInvoiceForm()
        formset = PurchaseInvoiceItemFormset(prefix='items')
    
    context = {
        'page_title': 'ثبت فاکتور خرید جدید',
        'form': form,
        'formset': formset
    }
    return render(request, 'drugs/purchase_invoice_form.html', context)


# --- Purchase Invoice Update View ---
def purchase_invoice_update(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, pk=pk)
    
    original_status = invoice.status 

    PurchaseInvoiceItemFormset = inlineformset_factory(
        PurchaseInvoice,
        PurchaseInvoiceItem,
        form=PurchaseInvoiceItemForm,
        extra=1,
        can_delete=True,
    )

    if request.method == 'POST':
        form = PurchaseInvoiceForm(request.POST, instance=invoice)
        formset = PurchaseInvoiceItemFormset(request.POST, instance=invoice, prefix='items')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    new_status = form.cleaned_data['status']
                    
                    # Scenario 1: Invoice was 'final', now it's 'draft' (or any non-final status)
                    if original_status == 'final' and new_status != 'final':
                        # This part assumes you want to reverse stock if status changes from final.
                        # It's crucial to ensure this logic aligns with your business rules.
                        for item in invoice.items.all():
                            try:
                                drug_batch = DrugBatch.objects.get(
                                    drug=item.drug, 
                                    batch_number=item.batch_number 
                                )
                                drug_batch.remove_stock(item.quantity)
                            except DrugBatch.DoesNotExist:
                                messages.warning(request, f"هشدار: بچ داروی '{item.batch_number}' برای آیتم '{item.drug.name}' در زمان معکوس کردن موجودی (تغییر وضعیت) پیدا نشد.")
                                print(f"Warning: DrugBatch not found for old item {item.pk} (batch: {item.batch_number}) on status change from final to draft.")
                            except ValueError as e:
                                messages.warning(request, f"هشدار: خطا در کاهش موجودی بچ {item.batch_number} برای {item.drug.name}: {e}")
                                print(f"Error removing stock during status change: {e}")

                    invoice = form.save() 
                    formset.save() # This will trigger post_save/post_delete for items.
                    
                    # Re-calculate total amount based on the current items after saves/deletes.
                    invoice.update_total_amount() 

                messages.success(request, 'فاکتور خرید با موفقیت ویرایش شد.')
                return redirect('drugs:purchase_invoice_detail', pk=invoice.pk)

            except Exception as e:
                messages.error(request, f'خطا در ویرایش فاکتور خرید: {e}. لطفا اطلاعات را بررسی کنید.')
                print(f"\n--- خطای کلی در تراکنش ویرایش: {e} ---")
                import traceback
                traceback.print_exc() 

        else:
            messages.error(request, 'خطا در اعتبارسنجی اطلاعات فاکتور. لطفا اطلاعات را بررسی کنید.')
            print("\n--- خطاهای اعتبارسنجی فرم ---")
            print("خطاهای فرم اصلی (PurchaseInvoiceForm):", form.errors)
            if form.non_field_errors():
                print("خطاهای غیرفیلد فرم اصلی (PurchaseInvoiceForm Non-Field Errors):", form.non_field_errors())
            print("خطاهای فرم‌ست آیتم‌ها (PurchaseInvoiceItemFormset Errors):")
            for i, item_form in enumerate(formset):
                if item_form.errors:
                    print(f" - Item {i+1} Errors: {item_form.errors}")
            if formset.non_form_errors():
                print("خطاهای غیرفیلد فرم‌ست (Formset Non-Form Errors):", formset.non_form_errors())
            print("------------------------------\n")

    else: # GET request
        form = PurchaseInvoiceForm(instance=invoice)
        formset = PurchaseInvoiceItemFormset(instance=invoice, prefix='items')

    context = {
        'page_title': f'ویرایش فاکتور خرید شماره {invoice.invoice_number}',
        'form': form,
        'formset': formset,
        'invoice': invoice
    }
    return render(request, 'drugs/purchase_invoice_form.html', context)
# --- نمایش جزئیات فاکتور خرید ---
@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_purchaseinvoice', raise_exception=True)
def purchase_invoice_detail(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, pk=pk)
    # ⭐ اصلاح شده: استفاده از related_name='items' ⭐
    invoice_items = invoice.items.all() 
    
    try:
        # اطمینان حاصل کنید که total_amount یک عدد است، سپس آن را به int تبدیل کنید.
        # اگر total_amount ممکن است None باشد، ابتدا آن را مدیریت کنید.
        if invoice.total_amount is not None:
            total_amount_int = int(invoice.total_amount)
            total_amount_in_words = digits.to_word(total_amount_int)
        else:
            total_amount_in_words = "صفر" # یا هر متن دلخواه دیگر برای مبلغ خالی
    except (ValueError, TypeError):
        total_amount_in_words = "خطا در تبدیل مبلغ" # اگر مقدار قابل تبدیل به عدد نباشد

    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'total_amount_in_words': total_amount_in_words, # پاس دادن مبلغ به حروف به تمپلیت
    }
    return render(request, 'drugs/purchase_invoice_detail.html', context)


@login_required
@permission_required('drugs.view_purchaseinvoice', raise_exception=True)
def purchase_invoice_print_view(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, pk=pk)
    invoice_items = invoice.items.all().select_related('drug')

    total_amount_in_words = ""
    try:
        if invoice.total_amount is not None:
            total_amount_as_number = float(invoice.total_amount)
            total_amount_int = int(round(total_amount_as_number))
            total_amount_in_words = digits.to_word(total_amount_int)
        else:
            total_amount_in_words = "صفر"
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Error converting invoice.total_amount ({invoice.total_amount}) to persian words: {e}")
        total_amount_in_words = "خطا در تبدیل مبلغ"

    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'total_amount_in_words': total_amount_in_words,
    }
    # ⭐ تغییر در نام تمپلیت رندر شده ⭐
    return render(request, 'drugs/purchase_invoice_print.html', context)



@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.delete_purchaseinvoice', raise_exception=True)
def purchase_invoice_delete(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, pk=pk)
    
    # قبل از حذف، وضعیت فاکتور را بررسی می‌کنیم
    original_status = invoice.status

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ⭐ منطق معکوس کردن موجودی انبار هنگام حذف فاکتور ⭐
                if original_status == 'final':
                    # اگر فاکتور نهایی بوده، باید تمام DrugBatchهای مرتبط با آن را پیدا کرده 
                    # و موجودی‌شان را کاهش دهیم یا حذف کنیم.
                    # این کار مهم است تا موجودی انبار نادرست نشود.
                    # فرض می‌کنیم DrugBatchها به purchase_invoice اشاره دارند.
                    for drug_batch in DrugBatch.objects.filter(purchase_invoice=invoice):
                        # در اینجا باید موجودی را از بچ کم کنیم، یا اگر این بچ فقط متعلق به این فاکتور بود، حذفش کنیم.
                        # اگر یک بچ ممکن است از فاکتورهای متعدد تامین شود (مثلا با batch_number یکسان)،
                        # باید فقط تعداد مربوط به این فاکتور را از آن کم کنید.
                        # ساده‌ترین حالت: هر DrugBatch منحصر به یک PurchaseInvoice و یک PurchaseInvoiceItem است.
                        drug_batch.delete() # حذف بچ‌های مرتبط با این فاکتور
                    messages.success(request, 'فاکتور خرید نهایی با موفقیت حذف شد و موجودی انبار به‌روزرسانی شد.')
                else:
                    messages.info(request, 'فاکتور خرید (موقت) با موفقیت حذف شد. موجودی انبار تغییری نکرده است.')

                invoice.delete()
                
            return redirect('drugs:purchase_invoice_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف فاکتور خرید: {e}')
            print(f"\n--- خطای کلی در حذف فاکتور: {e} ---")

    context = {
        'page_title': f'حذف فاکتور خرید شماره {invoice.invoice_number}',
        'invoice': invoice
    }
    return render(request, 'drugs/purchase_invoice_confirm_delete.html', context) # یک قالب برای تایید حذف

# --- Ajax View برای جستجوی دارو با Select2 ---
@login_required
def search_drugs_ajax(request):
    from drugs.models import DrugBatch
    from django.db.models import Min
    from django.utils import timezone
    import jdatetime
    
    form = DrugSearchForm(request.GET)
    results = []
    count = 0
    page = int(request.GET.get('page', 1))
    per_page = 10 

    if form.is_valid():
        query = form.cleaned_data.get('q')
        drug_id = form.cleaned_data.get('id')

        drugs = Drug.objects.all()

        if drug_id: 
            drugs = drugs.filter(pk=drug_id)
        elif query:
            # جستجو بر اساس drug_code, name, form, generic_name
            drugs = drugs.filter(
                Q(name__icontains=query) | 
                Q(drug_code__icontains=query) | 
                Q(form__icontains=query) | 
                Q(generic_name__icontains=query)
            ).distinct() 

        drugs = drugs.order_by('name')

        count = drugs.count()
        paginator = Paginator(drugs, per_page)
        page_obj = paginator.get_page(page)

        today = timezone.now().date()
        three_months_later = today + timezone.timedelta(days=90)

        for drug in page_obj:
            # محاسبه موجودی کل
            total_stock = sum(batch.quantity for batch in drug.batches.all())
            
            # بررسی تاریخ انقضای نزدیک‌ترین بچ معتبر
            nearest_batch = drug.batches.filter(quantity__gt=0, expiry_date__gte=today).order_by('expiry_date').first()
            
            # وضعیت‌ها
            is_expired = any(batch.quantity > 0 and batch.expiry_date and batch.expiry_date < today 
                           for batch in drug.batches.all())
            is_near_expiry = any(batch.quantity > 0 and batch.expiry_date and 
                                today <= batch.expiry_date <= three_months_later 
                                for batch in drug.batches.all())
            is_low_stock = total_stock > 0 and total_stock < drug.min_stock_alert
            
            # ساخت نمایش متنی
            text_display = f"{drug.name}"
            if hasattr(drug, 'form') and drug.form:
                text_display += f" ({drug.form})" 
            if hasattr(drug, 'generic_name') and drug.generic_name:
                text_display += f" - ژنریک: {drug.generic_name}"
            if hasattr(drug, 'drug_code') and drug.drug_code:
                text_display += f" - کد: {drug.drug_code}"
            else:
                text_display += " - کد: ندارد"

            # ساخت badge برای نمایش در select2
            stock_badge = ""
            if total_stock == 0:
                stock_badge = "<span class='badge badge-danger mr-1'>ناموجود</span>"
            elif is_expired:
                stock_badge = "<span class='badge badge-dark mr-1'>منقضی</span>"
            elif is_low_stock:
                stock_badge = f"<span class='badge badge-warning mr-1'>موجودی کم: {total_stock}</span>"
            elif is_near_expiry:
                stock_badge = f"<span class='badge badge-info mr-1'>موجودی: {total_stock} (نزدیک انقضا)</span>"
            else:
                stock_badge = f"<span class='badge badge-success mr-1'>موجودی: {total_stock}</span>"
            
            # اضافه کردن اطلاعات تاریخ انقضای نزدیک‌ترین بچ
            expiry_info = ""
            if nearest_batch:
                jalali_expiry = jdatetime.date.fromgregorian(date=nearest_batch.expiry_date).strftime('%Y/%m/%d')
                days_until_expiry = (nearest_batch.expiry_date - today).days
                if days_until_expiry < 30:
                    expiry_info = f"<span class='text-danger small mr-1'> (انقضا: {jalali_expiry})</span>"
                elif days_until_expiry < 90:
                    expiry_info = f"<span class='text-warning small mr-1'> (انقضا: {jalali_expiry})</span>"
                else:
                    expiry_info = f"<span class='text-muted small mr-1'> (انقضا: {jalali_expiry})</span>"

            results.append({
                'id': drug.pk,
                'text': text_display,
                'stock': total_stock,
                'is_expired': is_expired,
                'is_near_expiry': is_near_expiry,
                'is_low_stock': is_low_stock,
                'nearest_expiry': nearest_batch.get_jalali_expiry_date() if nearest_batch else None,
                'html': text_display + stock_badge + expiry_info
            })
    
    return JsonResponse({
        'results': results,
        'count': count,
        'pagination': {
            'more': page_obj.has_next()
        }
    })





@login_required
@permission_required('drugs.add_drugrequest')
def generate_drug_request_view(request):
    if request.method == 'POST':
        form = DrugRequestAnalysisForm(request.POST)
        if form.is_valid():
            # ... منطق تحلیل شما که قبلاً کار می‌کرد ...
            # ... این بخش شامل تولید initial_data و generation_notes است
            # نمونه‌ای از نحوه تولید initial_data (بسته به منطق شما)
            # این بخش از کد باید در پروژه شما کامل باشد.
            all_drugs_with_stock = Drug.objects.annotate(
                current_stock=models.Sum('batches__quantity', default=Value(0), output_field=IntegerField())
            )
            initial_data = []
            generation_notes = "پیش‌نویس تولید شده بر اساس تحلیل موجودی و مصرف."
            # مثال فرضی: اگر دارویی موجودی صفر دارد، آن را به لیست اضافه کن
            for drug in all_drugs_with_stock:
                if drug.current_stock == 0:
                    initial_data.append({
                        'drug': drug.pk, # باید PK دارو باشد
                        'requested_quantity': 10 # یک مقدار پیش‌فرض
                    })
            # ... (بقیه منطق تحلیل)
            
            # ذخیره داده‌ها در سشن برای استفاده در ویوی ایجاد
            request.session['generated_items'] = initial_data 
            request.session['generation_notes'] = generation_notes

            messages.success(request, f"آیتم‌های پیشنهادی با موفقیت ایجاد شدند. لطفاً فرم را تکمیل کنید.")
            # مطمئن شوید که به ویوی drug_request_create_from_suggestion ریدایرکت می‌کنید.
            return redirect('drugs:drug_request_create_from_suggestion')
    else:
        form = DrugRequestAnalysisForm()

    return render(request, 'drugs/generate_drug_request.html', {
        'form': form,
        'page_title': 'تحلیل و ایجاد درخواست هوشمند دارو'
    })

# --------------------------------------------------
# ویوی تکمیل و ثبت پیش‌نویس درخواست دارو (از تحلیل)
# --------------------------------------------------
@login_required
@permission_required('drugs.add_drugrequest')
def drug_request_create_from_suggestion(request):
    initial_items = request.session.get('generated_items', [])
    generation_notes = request.session.get('generation_notes', '')

    DrugRequestItemFormset = inlineformset_factory(
        DrugRequest, DrugRequestItem, form=DrugRequestItemForm, extra=1, can_delete=True, min_num=1, validate_min=True,
    )

    if request.method == 'POST':
        form = DrugRequestForm(request.POST)  # بدون request
        formset = DrugRequestItemFormset(request.POST, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                drug_request = form.save(commit=False)
                drug_request.requested_by = request.user  # کاربر لاگین‌شده
                drug_request.save()
                formset.instance = drug_request
                formset.save()

                request.session.pop('generated_items', None)
                request.session.pop('generation_notes', None)

                messages.success(request, "درخواست دارو با موفقیت ایجاد شد.")
                return redirect('drugs:drug_request_detail', pk=drug_request.pk)
        else:
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
            print("Formset non_form_errors:", formset.non_form_errors)
            # 🚨🚨🚨 تا اینجا 🚨🚨🚨
            messages.error(request, "خطا در فرم. لطفاً موارد را بررسی کنید.")
            
    else:
        form = DrugRequestForm(initial={'description': generation_notes})
        formset = DrugRequestItemFormset(prefix='items', initial=initial_items, queryset=DrugRequestItem.objects.none())

    return render(request, 'drugs/drug_request_form.html', {
        'form': form,
        'formset': formset,
        'page_title': 'تکمیل و ثبت پیش‌نویس درخواست دارو'
    })


@login_required
@permission_required('drugs.add_drugrequest')
def drug_request_create(request):
    initial_items = request.session.pop('generated_items', [])
    initial_desc = request.session.pop('generation_notes', '')

    DrugRequestItemFormset = inlineformset_factory(
        DrugRequest, DrugRequestItem, form=DrugRequestItemForm, extra=0, can_delete=True, min_num=0, validate_min=True,
    )

    if request.method == 'POST':
        form = DrugRequestForm(request.POST)
        formset = DrugRequestItemFormset(request.POST, prefix='items')

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                drug_request = form.save(commit=False)
                drug_request.requested_by = request.user
                drug_request.save()

                formset.instance = drug_request
                formset.save()

                DrugRequestWorkflowLog.objects.create(
                    drug_request=drug_request, actor=request.user, action="ایجاد درخواست",
                    new_status=drug_request.status, notes="درخواست توسط کاربر ایجاد شد."
                )

                messages.success(request, "درخواست دارو با موفقیت ایجاد شد.")
                return redirect('drugs:drug_request_detail', pk=drug_request.pk)
        else:
            messages.error(request, "خطا در فرم. لطفاً موارد را بررسی کنید.")
    else:
        form = DrugRequestForm(initial={'description': initial_desc})
        formset = DrugRequestItemFormset(prefix='items', initial=initial_items)

    return render(request, 'drugs/drug_request_form.html', {
        'form': form, 'formset': formset, 'page_title': 'ثبت درخواست داروی جدید'
    })


# --------------------------------------------------
# ویوی ویرایش درخواست دارو
# --------------------------------------------------
@login_required
@permission_required('drugs.change_drugrequest', raise_exception=True)
def drug_request_update(request, pk):
    drug_request = get_object_or_404(DrugRequest, pk=pk)

    if request.method == 'POST':
        form = DrugRequestForm(request.POST, instance=drug_request)
        formset = DrugRequestItemFormset(request.POST, instance=drug_request, prefix='items')

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                messages.success(request, 'تغییرات با موفقیت ذخیره شد.')
                return redirect('drugs:drug_request_detail', pk=drug_request.pk)
    else:
        form = DrugRequestForm(instance=drug_request)
        formset = DrugRequestItemFormset(instance=drug_request, prefix='items')

    return render(request, 'drugs/drug_request_update.html', {
        'form': form,
        'formset': formset,
        'drug_request': drug_request
    })
# --------------------------------------------------
# ویوی جدید برای تبدیل درخواست به فاکتور خرید
# --------------------------------------------------
@login_required
@permission_required('drugs.add_purchaseinvoice') # دسترسی برای افزودن فاکتور
def create_invoice_from_request(request, pk):
    drug_request = get_object_or_404(DrugRequest, pk=pk, status__in=['approved', 'pending'])
    
    # فرم‌ست برای آیتم‌های فاکتور
    InvoiceItemFormSet = inlineformset_factory(
        PurchaseInvoice, PurchaseInvoiceItem, form=PurchaseInvoiceItemForm, extra=0, can_delete=False
    )

    if request.method == 'POST':
        invoice_form = PurchaseInvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST, prefix='items')

        if invoice_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = invoice_form.save(commit=False)
                invoice.created_by = request.user
                invoice.notes = f"بر اساس درخواست {drug_request.request_code} | {invoice_form.cleaned_data.get('notes', '')}"
                invoice.status = 'draft' # فاکتور به صورت پیش‌نویس ایجاد می‌شود
                invoice.save()

                formset.instance = invoice
                formset.save() # این کار سیگنال‌ها را برای افزایش موجودی فعال نمی‌کند مگر اینکه وضعیت نهایی باشد

                invoice.update_total_amount()

                drug_request.status = 'completed'
                drug_request.save()
                
                DrugRequestWorkflowLog.objects.create(
                    drug_request=drug_request, actor=request.user, action="تبدیل به فاکتور",
                    new_status='completed', notes=f"فاکتور خرید {invoice.invoice_number} ایجاد شد."
                )
                
                messages.success(request, f"فاکتور خرید {invoice.invoice_number} با موفقیت از درخواست ایجاد شد.")
                return redirect('drugs:purchase_invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, "خطا در اطلاعات فاکتور. لطفاً فرم را بررسی کنید.")
    else:
        invoice_form = PurchaseInvoiceForm()
        initial_data = [{'drug': item.drug, 'quantity': item.requested_quantity} for item in drug_request.items.all()]
        formset = InvoiceItemFormSet(prefix='items', initial=initial_data, queryset=PurchaseInvoiceItem.objects.none())

    context = {
        'page_title': f"ایجاد فاکتور از درخواست {drug_request.request_code}",
        'form': invoice_form,
        'formset': formset,
        'object': drug_request
    }
    # می‌توانید از یک تمپلیت اختصاصی یا همان `purchase_invoice_form` استفاده کنید
    return render(request, 'drugs/purchase_invoice_form.html', context)



# ویوی لیست درخواست‌های دارو
# --------------------------------------------------
@login_required
@permission_required('drugs.view_drugrequest', raise_exception=True)
def drug_request_list(request):
    """
    نمایش لیست درخواست‌های دارو با فیلترهای مختلف.
    """
    view_filter = request.GET.get('filter', 'my_requests')
    
    base_queryset = DrugRequest.objects.select_related('requested_by', 'assigned_approver').all()

    if view_filter == 'assigned_to_me':
        queryset = base_queryset.filter(assigned_approver=request.user)
        page_title = 'درخواست‌های ارجاع شده به من'
    elif view_filter == 'all' and request.user.is_superuser:
        queryset = base_queryset
        page_title = 'تمام درخواست‌های دارو'
    else: # 'my_requests'
        queryset = base_queryset.filter(requested_by=request.user)
        page_title = 'درخواست‌های ایجاد شده توسط من'

    context = {
        'page_title': page_title,
        'requests': queryset.order_by('-request_date'),
        'current_filter': view_filter,
    }
    return render(request, 'drugs/drug_request_list.html', context)

# --------------------------------------------------
# ویوی جزئیات درخواست دارو
# --------------------------------------------------
@login_required
@permission_required('drugs.view_drugrequest', raise_exception=True)
def drug_request_detail(request, pk):
    """
    نمایش جزئیات یک درخواست دارو به همراه آیتم‌ها و لاگ گردش کار.
    """
    drug_request = get_object_or_404(
        DrugRequest.objects.prefetch_related('items__drug', 'workflow_logs__actor'),
        pk=pk
    )

    # کنترل دسترسی: کاربر باید درخواست‌کننده، مسئول تایید، یا سوپریوزر باشد
    if not (request.user == drug_request.requested_by or request.user == drug_request.assigned_approver or request.user.is_superuser):
        messages.error(request, "شما اجازه مشاهده این درخواست را ندارید.")
        return redirect('drugs:drug_request_list')

    context = {
        'page_title': f'جزئیات درخواست {drug_request.request_code}',
        'drug_request': drug_request, # نام را به drug_request تغییر دادم تا در تمپلیت خواناتر باشد
    }
    return render(request, 'drugs/drug_request_detail.html', context)


# --------------------------------------------------
# ویوی حذف درخواست دارو
# --------------------------------------------------
@login_required
@permission_required('drugs.delete_drugrequest', raise_exception=True)
@require_POST # برای امنیت بیشتر، حذف فقط با متد POST انجام شود
def drug_request_delete(request, pk):
    """
    حذف یک درخواست دارو.
    """
    drug_request = get_object_or_404(DrugRequest, pk=pk)

    # فقط ایجاد کننده یا سوپریوزر می‌تواند حذف کند
    if not (request.user == drug_request.requested_by or request.user.is_superuser):
        messages.error(request, "شما اجازه حذف این درخواست را ندارید.")
        return redirect('drugs:drug_request_detail', pk=pk)

    # جلوگیری از حذف درخواست‌های در حال پردازش
    if drug_request.status != 'pending':
        messages.error(request, "امکان حذف درخواستی که از وضعیت 'در حال بررسی' خارج شده، وجود ندارد.")
        return redirect('drugs:drug_request_detail', pk=pk)
        
    try:
        drug_request.delete()
        messages.success(request, f"درخواست {drug_request.request_code} با موفقیت حذف شد.")
        return redirect('drugs:drug_request_list')
    except Exception as e:
        messages.error(request, f"خطا در هنگام حذف درخواست: {e}")
        return redirect('drugs:drug_request_detail', pk=pk)





# --------------------------------------------------
# توابع مربوط به مدیریت تامین‌کنندگان (Supplier Management)
# --------------------------------------------------

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_supplier', raise_exception=True)
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by('name')
    query = request.GET.get('query')
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(phone__icontains=query) | # ⭐ 'phone_number' changed to 'phone' ⭐
            Q(email__icontains=query)
        )

    paginator = Paginator(suppliers, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = pagulator.page(paginator.num_pages)
        
    context = {
        'page_title': 'لیست تامین‌کنندگان',
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, 'drugs/supplier_list.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_supplier', raise_exception=True)
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    context = {
        'page_title': f"جزئیات تامین‌کننده: {supplier.name}",
        'supplier': supplier,
    }
    return render(request, 'drugs/supplier_detail.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.add_supplier', raise_exception=True)
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تأمین‌کننده با موفقیت اضافه شد.')
            return redirect('drugs:supplier_list') # به لیست تامین‌کنندگان ریدایرکت می‌کنیم
    else:
        form = SupplierForm()
    context = {
        'page_title': "افزودن تأمین‌کننده جدید",
        'form': form
    }
    return render(request, 'drugs/supplier_form.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.change_supplier', raise_exception=True)
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'اطلاعات تأمین‌کننده با موفقیت به روز شد.')
            return redirect('drugs:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    context = {
        'page_title': f"ویرایش تأمین‌کننده: {supplier.name}",
        'form': form,
        'supplier': supplier, # برای نمایش نام تامین‌کننده در عنوان صفحه
    }
    return render(request, 'drugs/supplier_form.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.delete_supplier', raise_exception=True)
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'تأمین‌کننده با موفقیت حذف شد.')
        return redirect('drugs:supplier_list')
    context = {
        'page_title': f"حذف تأمین‌کننده: {supplier.name}",
        'object': supplier, # معمولاً object رو برای فرم تایید حذف میفرستن
    }
    return render(request, 'drugs/supplier_confirm_delete.html', context)


# --------------------------------------------------
# API برای جستجوی دارو (برای فرم‌های ویزیت)
# --------------------------------------------------
class DrugSearchAPIView(generics.ListAPIView):
    queryset = Drug.objects.all()
    serializer_class = DrugSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'generic_name', 'drug_code'] # فیلدهایی که برای فیلتر استفاده می‌شوند

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | 
                Q(generic_name__icontains=query) | 
                Q(drug_code__icontains=query)
            )
        return queryset.annotate(current_stock_val=Sum('batches__quantity', filter=Q(batches__expiry_date__gte=datetime.date.today())))


class DrugSelect2View(AutoResponseView):
    queryset = Drug.objects.all().order_by('name')
    def get_results(self, context, field, request, page, app_label, model_name, field_name):
        # این تابع به صورت پیش‌فرض نتایج را برمی‌گرداند.
        # می‌توانید اینجا منطق جستجو را سفارشی کنید
        qs = self.get_queryset()
        term = self.q # term جستجوی Select2 است
        if term:
            qs = qs.filter(Q(name__icontains=term) | Q(generic_name__icontains=term))
        return [
            {'id': obj.pk, 'text': str(obj)} for obj in qs[page * 10:(page + 1) * 10]
        ]

class UserSelect2View(AutoResponseView):
    queryset = User.objects.all().order_by('first_name', 'last_name')
    def get_results(self, context, field, request, page, app_label, model_name, field_name):
        qs = self.get_queryset()
        term = self.q
        if term:
            qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(username__icontains=term))
        return [
            {'id': obj.pk, 'text': obj.get_full_name() or obj.username} for obj in qs[page * 10:(page + 1) * 10]
        ]
def upload_temporary_inventory(request):
    """
    View برای آپلود فایل اکسل و ایجاد موجودی موقت (کاذب) برای داروها.
    """
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                workbook = openpyxl.load_workbook(filename=BytesIO(excel_file.read()))
                sheet = workbook.active
                
                rows_created = 0
                errors = []
                
                form_choices_dict = dict(DRUG_FORM_CHOICES)
                
                with transaction.atomic():
                    for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                        if not row or not row[0]:
                            continue
                            
                        drug_name = str(row[0]).strip()
                        if not drug_name:
                            errors.append(f"ردیف {row_num}: نام دارو خالی است. این ردیف نادیده گرفته شد.")
                            continue

                        drug_form_persian = str(row[1]).strip() if len(row) > 1 else 'قرص'
                        
                        drug = None
                        
                        try:
                            # 1. جستجو برای داروی موجود
                            drug = Drug.objects.get(name__iexact=drug_name)
                        except Drug.DoesNotExist:
                            # 2. اگر دارو نبود، یک داروی جدید ایجاد کن (با استفاده از فرم)
                            form_key = 'tablet'
                            for key, value in form_choices_dict.items():
                                if value == drug_form_persian:
                                    form_key = key
                                    break
                            
                            # ایجاد یک دیکشنری از داده‌ها
                            new_drug_data = {
                                'name': drug_name,
                                'generic_name': drug_name,
                                'form': form_key,
                                'min_stock_alert': 20,  # ⭐ افزودن مقدار پیش‌فرض
                                'reorder_point': 20,    # ⭐ افزودن مقدار پیش‌فرض
                            }
                           
                            drug_form_instance = DrugForm(new_drug_data)
                            if drug_form_instance.is_valid():
                                drug = drug_form_instance.save()
                                messages.info(request, f"داروی جدید '{drug_name}' در سیستم ایجاد شد.")
                            else:
                                # اگر فرم نامعتبر بود، خطا را ثبت کن و ادامه بده
                                for field, errs in drug_form_instance.errors.items():
                                    for err in errs:
                                        errors.append(f"ردیف {row_num}: خطای فرم برای داروی '{drug_name}' - فیلد '{field}': {err}")
                                continue

                        # ⭐ بررسی نهایی: اطمینان از وجود شیء و id
                        if not drug or not drug.id:
                            errors.append(f"ردیف {row_num}: خطای غیرمنتظره در ذخیره‌سازی داروی '{drug_name}' رخ داد.")
                            continue

                        # 3. ایجاد موجودی موقت برای دارو
                        default_expiry_date = date.today() + relativedelta(months=+6)
                        
                        DrugBatch.objects.create(
                            drug=drug,
                            batch_number=f"TEMP-{drug.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{row_num}",
                            quantity=200,
                            expiry_date=default_expiry_date, 
                            purchase_price=Decimal('0.00'),
                            is_temporary=True
                        )
                        rows_created += 1
                    
                if errors:
                    for error in errors:
                        messages.warning(request, error)
                
                if rows_created > 0:
                    messages.success(request, f"{rows_created} موجودی موقت از طریق فایل اکسل با موفقیت ایجاد شد.")
                else:
                    messages.info(request, "هیچ موجودی موقتی از فایل ایجاد نشد. لطفاً ساختار فایل را بررسی کنید.")
                
            except Exception as e:
                messages.error(request, f"خطا در پردازش فایل: {e}")
            
            return redirect('drugs:drug_list')
    else:
        form = ExcelUploadForm()
        
    context = {
        'form': form,
        'page_title': "آپلود موجودی موقت با اکسل",
    }
    return render(request, 'drugs/upload_temporary_inventory.html', context)


@login_required
def delete_temporary_inventory(request):
    """
    View برای حذف تمام موجودی‌های موقت پس از انبارگردانی.
    """
    if request.method == 'POST':
        with transaction.atomic():
            temporary_batches_count = DrugBatch.objects.filter(is_temporary=True).count()
            if temporary_batches_count > 0:
                DrugBatch.objects.filter(is_temporary=True).delete()
                messages.success(request, f"{temporary_batches_count} موجودی موقت با موفقیت حذف شد.")
            else:
                messages.info(request, "هیچ موجودی موقتی برای حذف وجود ندارد.")
        return redirect('drugs:drug_list')
        
    context = {
        'page_title': "حذف موجودی موقت",
    }
    return render(request, 'drugs/delete_temporary_inventory_confirm.html', context)  
def search_suppliers_ajax(request):
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    per_page = 10 

    suppliers = Supplier.objects.all()

    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query)
        ).distinct() 

    suppliers = suppliers.order_by('name')

    count = suppliers.count()
    paginator = Paginator(suppliers, per_page)
    page_obj = paginator.get_page(page)
    
    # استفاده از سریالایزر برای تبدیل QuerySet به داده‌های JSON
    serializer = SupplierSerializer(page_obj, many=True)
    results = serializer.data
    
    return JsonResponse({
        'results': results,
        'count': count,
        'pagination': {
            'more': page_obj.has_next()
        }
    })
# ... import های دیگر
import re # ماژول regular expressions را برای استخراج کد اضافه کنید
from django.db.models import Q

# ... 
# کلاس‌های دیگر
# ...

class DrugAutocompleteAPIView(generics.ListAPIView):
    serializer_class = DrugSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        print(f"\n[DEBUG] API received query: '{query}'") # --- دیباگ ۱

        if not query:
            return Drug.objects.none()

        # تلاش برای استخراج GTIN از بارکد GS1
        gtin_match = re.search(r'(?:01)(\d{14})', query)
        
        if gtin_match:
            extracted_gtin = gtin_match.group(1)
            print(f"[DEBUG] GS1 GTIN extracted: '{extracted_gtin}'") # --- دیباگ ۲
            
            barcode_query = Q(barcodes__gtin=extracted_gtin)
            results = Drug.objects.filter(barcode_query).prefetch_related('barcodes').distinct()
            
            print(f"[DEBUG] Found {results.count()} drugs for this GTIN.") # --- دیباگ ۳
            return results

        # اگر GTIN پیدا نشد، به منطق جستجوی قبلی برمی‌گردیم
        print("[DEBUG] No GS1 GTIN found. Falling back to general search.") # --- دیباگ ۴
        
        if query.isdigit():
            return Drug.objects.filter(pk=query).prefetch_related('barcodes')

        name_query = Q(name__icontains=query)
        barcode_query = Q(barcodes__gtin__icontains=query)
        combined_query = name_query | barcode_query
        
        results = Drug.objects.filter(combined_query).prefetch_related('barcodes').distinct()
        print(f"[DEBUG] General search found {results.count()} results.") # --- دیباگ ۵
        return results