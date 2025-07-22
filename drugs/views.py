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
# مدل‌ها و فرم‌های اپ drugs
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

@login_required(login_url=reverse_lazy('login'))
def drug_list(request):
    today = timezone.now().date()
    three_months_from_now = today + datetime.timedelta(days=90)

    base_queryset = Drug.objects.all().annotate(
        total_stock=Sum('batches__quantity', default=0),
        # اضافه کردن تعداد بچ‌های منقضی شده
        expired_batches_count=Count(
            Case(
                When(batches__expiry_date__lt=today, then=Value(1)),
                output_field=BooleanField(),
            ),
            distinct=True # برای شمارش بچ‌های مختلف، نه فقط ردیف‌های تکراری
        ),
        # اضافه کردن تعداد بچ‌های در شرف انقضا (فعال و دارای موجودی)
        expiring_soon_batches_count=Count(
            Case(
                When(
                    batches__expiry_date__gte=today,
                    batches__expiry_date__lte=three_months_from_now,
                    batches__quantity__gt=0,
                    then=Value(1)
                ),
                output_field=BooleanField(),
            ),
            distinct=True
        )
    )

    drug_filter = DrugFilter(request.GET, queryset=base_queryset)
    filtered_drugs = drug_filter.qs.order_by('name')

    paginator = Paginator(filtered_drugs, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'page_title': 'لیست داروها',
        'page_obj': page_obj,
        'filter': drug_filter,
    }
    return render(request, 'drugs/drug_list.html', context)



@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.add_drug', raise_exception=True)
def drug_create(request):
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'دارو با موفقیت اضافه شد!')
            return redirect('drugs:drug_list')
        else:
            messages.error(request, 'خطا در افزودن دارو. لطفا اطلاعات را بررسی کنید.')
    else:
        form = DrugForm()
    context = {
        'page_title': 'افزودن داروی جدید',
        'form': form
    }
    return render(request, 'drugs/drug_form.html', context)


@login_required(login_url=reverse_lazy('login'))
@permission_required('drugs.view_drug', raise_exception=True)
def drug_detail(request, pk):
    drug = get_object_or_404(Drug, pk=pk)
    batches = drug.drugbatch_set.all().order_by('-expiry_date', '-created_at')
    
    # Calculate drug requests related to this drug
    # Here we might want to show items of drug requests where this drug is requested
    # For simplicity, we are just counting for now
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
            # فرض بر این است که این فیلدها در مدل Drug شما وجود دارند
            drugs = drugs.filter(
                Q(name__icontains=query) | 
                Q(drug_code__icontains=query) | # drug_code استفاده شد
                Q(form__icontains=query) | # form استفاده شد
                Q(generic_name__icontains=query) # generic_name استفاده شد
            ).distinct() 

        drugs = drugs.order_by('name')

        count = drugs.count()
        paginator = Paginator(drugs, per_page)
        page_obj = paginator.get_page(page)

        for drug in page_obj:
            text_display = f"{drug.name}"
            # اضافه کردن فرم دارویی (اگر وجود دارد)
            if hasattr(drug, 'form') and drug.form: # چک کردن وجود فیلد form
                text_display += f" ({drug.form})" 
            # اضافه کردن نام ژنریک (اگر وجود دارد)
            if hasattr(drug, 'generic_name') and drug.generic_name: # چک کردن وجود فیلد generic_name
                text_display += f" - ژنریک: {drug.generic_name}"
            # اضافه کردن کد دارو (اگر وجود دارد)
            if hasattr(drug, 'drug_code') and drug.drug_code: # چک کردن وجود فیلد drug_code
                text_display += f" - کد: {drug.drug_code}"
            else:
                text_display += " - کد: ندارد" # اگر کد دارو خالی بود

            results.append({
                'id': drug.pk,
                'text': text_display
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
        DrugRequest, DrugRequestItem, form=DrugRequestItemForm, extra=1, can_delete=True, min_num=1, validate_min=True,
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

    # برای ایجاد فرم‌ست آیتم‌ها
    DrugRequestItemFormset = inlineformset_factory(
        DrugRequest, DrugRequestItem, form=DrugRequestItemForm, extra=1, can_delete=True, min_num=1, validate_min=True,
    )

    if request.method == 'POST':
        form = DrugRequestForm(request.POST, instance=drug_request)
        formset = DrugRequestItemFormset(request.POST, instance=drug_request, prefix='items')

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # چون requested_by غیرفعال است، در POST وجود ندارد و form.save() آن را تغییر نمی‌دهد
                # و مقدار اولیه شیء حفظ می‌شود. پس مشکلی نیست.
                form.save()
                formset.save()
                
                # منطق لاگ‌گیری برای تغییرات...
                # می‌توانید لاگ تغییر وضعیت یا سایر تغییرات مهم را اینجا اضافه کنید.
                
                messages.success(request, 'درخواست دارو با موفقیت به‌روزرسانی شد.')
                # ✅ 'return' اضافه شد
                return redirect('drugs:drug_request_detail', pk=drug_request.pk)
        else:
            messages.error(request, "خطا در فرم. لطفاً موارد را بررسی کنید.")
    else:
        # در متد GET، request را به فرم می‌دهیم تا فیلد کاربر را غیرفعال کند
        form = DrugRequestForm(instance=drug_request, request=request)
        formset = DrugRequestItemFormset(instance=drug_request, prefix='items')

    context = {
        'form': form, 'formset': formset, 'drug_request': drug_request,
        'page_title': f'ویرایش درخواست: {drug_request.request_code}'
    }
    return render(request, 'drugs/drug_request_update.html', context)

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
        DrugRequest.objects.prefetch_related('items__drug', 'workflow_logs__user'),
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
        return queryset.annotate(current_stock_val=Sum('drugbatch__quantity', filter=Q(drugbatch__expiry_date__gte=datetime.date.today())))


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

