# D:\final\visits\views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q , Sum, Count # برای استفاده از Count و Q object
from datetime import date ,timezone
from django.db.models.functions import TruncMonth # برای گروه‌بندی بر اساس ماه
import jdatetime # برای کار با تاریخ شمسی
from django.utils import timezone 
# ایمپورت مدل‌ها و فرم‌ها
from .models import Visit, ReasonForVisit, TreatmentResult, VISIT_STATUS_CHOICES, VisitItem
from .forms import VisitForm, VisitItemFormSet, VisitReferralForm
from core.models import Patient, Company # Patient و Company از core ایمپورت می‌شوند
from drugs.models import Drug, DrugBatch # Drug و DrugBatch از drugs ایمپورت می‌شوند
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from fcm_django.models import FCMDevice
# ایمپورت فیلترها (فرض بر این است که این فایل در جای صحیح قرار دارد)
from core.filters import VisitFilter # مسیر صحیح را تأیید کنید
from django.views.decorators.http import require_POST
# ایمپورت‌های مربوط به API Views
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
# *** توجه: این دو سریالایزر باید در اپ core (یا هر اپ دیگری که تعریف کرده‌اید) موجود باشند ***
from core.serializers import PatientSerializer, DrugSerializer 
from rest_framework.decorators import api_view
from rest_framework.response import Response # برای patient_detail_api
from django.shortcuts import get_object_or_404
# ایمپورت‌های مربوط به نوتیفیکیشن
from fcm_django.models import FCMDevice
from clinic_messages.models import Notification # فرض می‌کنیم این مدل وجود دارد و مسیرش صحیح است
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from core.models import Patient# مدل Visit را هم import کنید
from core.serializers import PatientSearchSerializer
# دریافت مدل User
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import ReasonForVisit

# --- توابع کمکی برای نوتیفیکیشن ---
def send_visit_referral_notification(visit_instance, recipient_user, sender_user):
    """
    تابع کمکی برای ارسال نوتیفیکیشن ارجاع ویزیت.
    نوتیفیکیشن را در دیتابیس ذخیره کرده و به صورت پوش (FCM) ارسال می‌کند.
    """
    message_title = "ویزیت جدید به شما ارجاع شد!"
    message_body = (
        f"ویزیت بیمار {visit_instance.patient.get_full_name()} "
        f"(تاریخ: {jdatetime.datetime.fromgregorian(datetime=visit_instance.visit_date).strftime('%Y/%m/%d - %H:%M')}) "
        "به شما ارجاع داده شد. لطفاً آن را بررسی کنید."
    )
    
    try:
        link_to_visit = reverse('visits:visit_detail', args=[visit_instance.pk])
    except Exception:
        link_to_visit = f"/visits/{visit_instance.pk}/" # یک لینک جایگزین اگر reverse کار نکرد

    # 1. ذخیره نوتیفیکیشن در دیتابیس (مدل Notification)
    try:
        Notification.objects.create(
            recipient=recipient_user,
            sender=sender_user,
            message=message_body,
            link=link_to_visit,
            notification_type='referral',
            is_read=False
        )
        print(f"DEBUG: Database Notification created for {recipient_user.username}.")
    except Exception as e:
        print(f"ERROR: Error creating database notification for {recipient_user.username}: {e}")

    # 2. ارسال نوتیفیکیشن پوش با FCM
    devices = FCMDevice.objects.filter(user=recipient_user, active=True)
    if devices.exists():
        try:
            devices.send_message(
                title=message_title, 
                body=message_body,
                data={
                    "visit_id": str(visit_instance.pk),
                    "type": "referral",
                    "link": link_to_visit 
                } 
            )
            print(f"DEBUG: FCM Notification sent to {recipient_user.username} for visit {visit_instance.pk}.")
        except Exception as e:
            print(f"ERROR: Error sending FCM notification to {recipient_user.username}: {e}")
    else:
        print(f"DEBUG: No active FCM devices found for user {recipient_user.username} to send notification for visit {visit_instance.pk}.")


class PatientSearchAPIView(generics.ListAPIView):
    """
    API View برای جستجوی بیماران جهت استفاده در Select2.
    """
    # 🔽🔽🔽 تغییر اصلی اینجاست 🔽🔽🔽
    serializer_class = PatientSearchSerializer # از سریالایزر اختصاصی جستجو استفاده می‌کنیم
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Patient.objects.all()
        search_query = self.request.query_params.get('q', '')

        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(national_code__icontains=search_query) |
                Q(personnel_number__icontains=search_query)
            ).distinct()
        
        return queryset[:10]

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Patient, Visit
import jdatetime # برای تبدیل تاریخ به شمسی

def patient_detail_api(request):
    patient_id = request.GET.get('patient_id')
    current_visit_id = request.GET.get('current_visit_id')
    
    if not patient_id:
        return JsonResponse({"error": "شناسه بیمار الزامی است"}, status=400)
    
    try:
        patient = Patient.objects.get(pk=patient_id)
        
        # پیدا کردن ویزیت قبلی (غیر از ویزیت فعلی)
        visits_query = patient.visits.all()
        if current_visit_id:
            visits_query = visits_query.exclude(pk=current_visit_id)
        
        last_visit = visits_query.order_by('-visit_date').first()
        
        shamsi_date = "---"
        last_reason = "ویزیت اول (فاقد سابقه قبلی)"
        
        if last_visit:
            if last_visit.visit_date:
                shamsi_date = jdatetime.datetime.fromgregorian(datetime=last_visit.visit_date).strftime('%Y/%m/%d')
            if last_visit.reason_for_visit:
                # اگر مدل reason_for_visit داری .name بزن، اگر فیلد متنیه مستقیم خودش رو بفرست
                last_reason = str(last_visit.reason_for_visit)

        data = {
            "age": patient.age,  # اضافه شدن سن از متد مدل Patient
            "visit_count": patient.visits.count(),
            "last_visit_date": shamsi_date,
            "last_visit_reason": last_reason,
            "allergies": patient.allergies or "موردی ندارد",
            "medical_history": patient.medical_history or "فاقد سابقه قبلی",
            "occupation": patient.occupation or "ثبت نشده",
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

class DrugSearchAPIView(generics.ListAPIView):
    serializer_class = DrugSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', None)
        # این خط حیاتی است برای نسخه دوم سریالایزر که دادم
        queryset = Drug.objects.prefetch_related('batches').all()
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(generic_name__icontains=query) |
                Q(drug_code__icontains=query) # اضافه کردن جستجو با کد دارو
            ).distinct()
        return queryset



# --- VIEW FUNCTIONS ---

@login_required
@permission_required('visits.add_visit', raise_exception=True)
def visit_create(request, patient_id=None):
    """
    ایجاد ویزیت جدید و تجویز دارو.
    """
    initial_data = {}
    patient = None  # مقدار اولیه برای patient
    if patient_id:
        try:
            patient = Patient.objects.get(pk=patient_id)
            # پر کردن فیلد بیمار در فرم به صورت خودکار با استفاده از شیء patient
            initial_data['patient'] = patient
            messages.info(request, f"ایجاد ویزیت جدید برای بیمار: {patient.full_name}")
        except Patient.DoesNotExist:
            messages.error(request, "بیمار مورد نظر یافت نشد.")
            return redirect('core:patient_list')

    if request.method == 'POST':
        form = VisitForm(request.POST, initial=initial_data)
        formset = VisitItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                visit = form.save(commit=False)
                visit.doctor = request.user
                visit.assigned_to = request.user
                visit.status = 'pending'
                visit.save()

                formset.instance = visit
                formset.save()

                messages.success(request, 'ویزیت جدید با موفقیت ثبت شد.')
                return redirect('visits:visit_detail', pk=visit.pk)
        else:
            messages.error(request, 'خطا در ثبت ویزیت. لطفاً خطاهای فرم را برطرف کنید.')
            print("Visit Form Errors:", form.errors)
            print("VisitItem Formset Errors:", formset.errors)
    else:
        form = VisitForm(initial=initial_data)
        formset = VisitItemFormSet()

    context = {
        'form': form,
        'formset': formset,
        'page_title': 'ثبت ویزیت جدید',
        'is_update': False,
        'patient': patient,  # ارسال آبجکت patient به context برای نمایش در قالب HTML
    }
    return render(request, 'visits/visit_form.html', context)


@login_required
@permission_required('visits.change_visit', raise_exception=True)
def visit_update(request, pk):
    """
    ویرایش ویزیت و آیتم‌های تجویز شده.
    """
    visit = get_object_or_404(Visit, pk=pk)
    
    # کنترل دسترسی ویرایش: فقط کاربر مسئول فعلی یا سوپریوزر
    if not (request.user == visit.assigned_to or request.user.is_superuser):
        messages.error(request, "شما اجازه ویرایش این ویزیت را ندارید. ویزیت به کاربر دیگری ارجاع شده است.")
        return redirect('visits:visit_detail', pk=visit.pk)

    if visit.status == 'completed':
        messages.warning(request, "امکان ویرایش ویزیت تکمیل شده وجود ندارد.")
        return redirect('visits:visit_detail', pk=visit.pk)

    if request.method == 'POST':
        form = VisitForm(request.POST, instance=visit)
        formset = VisitItemFormSet(request.POST, instance=visit, prefix='items')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                messages.success(request, 'تغییرات ویزیت با موفقیت ذخیره شد.')
                return redirect('visits:visit_detail', pk=visit.pk)
        else:
            messages.error(request, 'خطا در ویرایش ویزیت. لطفاً خطاهای فرم را برطرف کنید.')
            print("Visit Form Errors:", form.errors)
            print("VisitItem Formset Errors:", formset.errors)
    else:
        form = VisitForm(instance=visit)
        formset = VisitItemFormSet(instance=visit, prefix='items')

    return render(request, 'visits/visit_update.html', {
        'page_title': f'ویرایش ویزیت: {visit.patient.full_name}',
        'form': form,
        'formset': formset,
        'visit': visit,
        'is_update': True,
    })

@login_required
@permission_required('visits.view_visit', raise_exception=True)
def visit_list(request):
    """
    نمایش لیست ویزیت‌ها با قابلیت فیلتر و جستجو.
    """
    base_queryset = Visit.objects.select_related(
        'patient',
        'doctor',          # 'visits_as_doctor' در مدل، اینجا فقط 'doctor' کافی است
        'assigned_to',     # 'assigned_visits' در مدل، اینجا فقط 'assigned_to' کافی است
        'reason_for_visit', # علت مراجعه
        'treatment_result' # نتیجه درمان
    ).prefetch_related('items').all() 
    
    view_filter = request.GET.get('view', 'pending')

    if view_filter == 'referred_to_me':
        queryset = base_queryset.filter(status='referred', assigned_to=request.user)
        title = "ویزیت‌های ارجاع شده به من"
    elif view_filter == 'completed':
        queryset = base_queryset.filter(status='completed')
        title = "ویزیت‌های تکمیل شده"
    else: # 'pending' (شامل ویزیت‌هایی که assigned_to خود کاربر هستند و وضعیت pending دارند)
        queryset = base_queryset.filter(status='pending', assigned_to=request.user)
        title = "ویزیت‌های در حال بررسی من"

    search_query = request.GET.get('q')
    if search_query:
        queryset = queryset.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__national_code__icontains=search_query) |
            Q(patient__personnel_number__icontains=search_query)
        ).distinct()

    paginator = Paginator(queryset.order_by('-visit_date'), 15) # مرتب سازی بر اساس visit_date که شامل ساعت هم هست
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'visits/visit_list.html', {
        'page_title': title,
        'page_obj': page_obj,
        'search_query': search_query,
        'view_filter': view_filter,
    })

@login_required
@permission_required('visits.view_visit', raise_exception=True)
def visit_detail(request, pk):
    """
    نمایش جزئیات یک ویزیت خاص.
    """
    visit = get_object_or_404(
        Visit.objects.select_related(
            'patient',
            'doctor',           # 'visits_as_doctor' در مدل، اینجا فقط 'doctor' کافی است
            'assigned_to',      # 'assigned_visits' در مدل، اینجا فقط 'assigned_to' کافی است
            'reason_for_visit', # علت مراجعه
            'treatment_result'  # نتیجه درمان
        ).prefetch_related('items__drug'), # برای داروهای تجویز شده و دسترسی به Drug
        pk=pk
    )
    
    # فرم ارجاع فقط با کاربرانی که خود کاربر فعلی نیستند پر می‌شود
    referral_form = VisitReferralForm(user=request.user)
    
    return render(request, 'visits/visit_detail.html', {
        'page_title': f'جزئیات ویزیت: {visit.patient.full_name}',
        'visit': visit,
        'referral_form': referral_form,
    })

@login_required
@permission_required('visits.delete_visit', raise_exception=True)
@require_POST # اطمینان از اینکه فقط درخواست POST می‌تواند حذف کند
def visit_delete(request, pk):
    """
    حذف یک ویزیت.
    """
    visit = get_object_or_404(Visit, pk=pk)
    # کنترل دسترسی حذف: فقط کاربر ثبت کننده یا سوپریوزر (و نه اگر تکمیل شده باشد)
    if not (request.user == visit.doctor or request.user.is_superuser):
        messages.error(request, "شما اجازه حذف این ویزیت را ندارید.")
        return redirect('visits:visit_detail', pk=visit.pk)

    if visit.status == 'completed':
        messages.error(request, 'امکان حذف ویزیت تکمیل شده وجود ندارد.')
        return redirect('visits:visit_detail', pk=visit.pk)
    
    try:
        visit.delete()
        messages.success(request, 'ویزیت با موفقیت حذف شد.')
    except Exception as e:
        messages.error(request, f"خطا در حذف ویزیت: {e}")
    
    return redirect('visits:visit_list') # همیشه به لیست ویزیت‌ها ریدایرکت شود


@login_required
@permission_required('visits.refer_visit', raise_exception=True)
@require_POST # اطمینان از اینکه فقط درخواست POST می‌تواند ارجاع دهد
def refer_visit(request, pk):
    """
    ارجاع یک ویزیت به کاربر دیگر.
    """
    visit = get_object_or_404(Visit, pk=pk)
    
    # کنترل دسترسی ارجاع: فقط کاربر مسئول فعلی یا سوپریوزر
    if not (request.user == visit.assigned_to or request.user.is_superuser):
        messages.error(request, "شما اجازه ارجاع این ویزیت را ندارید.")
        return redirect('visits:visit_detail', pk=visit.pk)
        
    if visit.status == 'completed':
        messages.error(request, "ویزیت تکمیل شده قابل ارجاع نیست.")
        return redirect('visits:visit_detail', pk=visit.pk)

    # ⭐ ذخیره کاربر مسئول قبلی قبل از تغییر برای منطق نوتیفیکیشن ⭐
    old_assigned_to = visit.assigned_to

    # 'user=request.user' را به فرم پاس می‌دهیم تا بتواند کاربر فعلی را از لیست ارجاع حذف کند
    form = VisitReferralForm(request.POST, instance=visit, user=request.user) # instance=visit را نگه داریم
    
    if form.is_valid():
        new_assigned_to = form.cleaned_data['assigned_to'] # کاربر جدید انتخاب شده در فرم
        
        # ⭐ بروزرسانی assigned_to و status ⭐
        visit.assigned_to = new_assigned_to
        visit.status = 'referred' # وضعیت را به ارجاع شده تغییر می‌دهیم
        visit.save() # ویزیت را ذخیره می‌کنیم

        # ⭐ منطق ارسال نوتیفیکیشن: فقط در صورتی که کاربر جدیدی تعیین شده باشد و با کاربر قبلی متفاوت باشد ⭐
        # و کاربر جدید None نباشد (چون به None ارجاع داده شده نوتیفیکیشن نمی‌فرستیم)
        if new_assigned_to and new_assigned_to != old_assigned_to:
            messages.success(request, f"ویزیت با موفقیت به {new_assigned_to.get_full_name()} ارجاع داده شد.")
            send_visit_referral_notification(visit, new_assigned_to, request.user) 
        elif not new_assigned_to: # اگر به هیچکس ارجاع داده نشده (یعنی assigned_to شده None)
            messages.info(request, f"ویزیت از حالت ارجاع خارج و به حالت بررسی بازگشت (بدون کاربر مسئول).")
        else: # اگر به همان کاربر قبلی ارجاع داده شده (یعنی کاربر مسئول تغییر نکرده)
            messages.info(request, f"ویزیت به همان کاربر قبلی ارجاع داده شده است.")

        return redirect('visits:visit_detail', pk=visit.pk)
    else:
        messages.error(request, "خطا در ارجاع ویزیت. لطفاً انتخاب را بررسی کنید.")
        # برای نمایش ارورها در مودال، باید فرم ویزیت و خطاها را دوباره به تمپلیت پاس دهید و مودال را با جاوااسکریپت باز کنید.
        # فعلاً فقط پیام کلی را نمایش می‌دهیم.
        print("Referral Form Errors:", form.errors) 
        # اگر می‌خواهید خطاهای فرم را نمایش دهید، باید مودال را به درستی هندل کنید.
        # می‌توانید به جای redirect، دوباره visit_detail را با form_referral_error به context رندر کنید.
    return redirect('visits:visit_detail', pk=visit.pk)
# در فایل views.py
def api_reason_search(request):
    query = request.GET.get('q', '')
    # تغییر title__icontains به name__icontains
    reasons = ReasonForVisit.objects.filter(name__icontains=query, is_active=True)[:10]
    
    results = [
        {'id': reason.id, 'text': reason.name} # اینجا هم name رو بفرست
        for reason in reasons
    ]
    return JsonResponse(results, safe=False)

@login_required
@permission_required('visits.change_visit', raise_exception=True)
@require_POST
def complete_visit(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    
    if visit.status == 'completed':
        messages.warning(request, "این ویزیت قبلاً تکمیل شده است.")
        return redirect('visits:visit_detail', pk=visit.pk)
    
    # 1. وضعیت ویزیت را به 'completed' تغییر دهید
    # 2. زمان تکمیل و کاربر تکمیل کننده را ثبت کنید
    # 3. موجودی دارو را کسر کنید
    
    try:
        with transaction.atomic():
            # ⭐ مهم: تغییر وضعیت به 'completed' و ذخیره آن
            # این ذخیره (save) کردن، سیگنال pre_save (handle_stock_on_visit_completion در signals.py) را تریگر می‌کند.
            # بنابراین، منطق کسر موجودی نباید مستقیماً اینجا تکرار شود.
            visit.status = 'completed'
            visit.completed_at = timezone.now()
            visit.completed_by = request.user
            visit.save() # این save سیگنال handle_stock_on_visit_completion را فعال می‌کند.

            # توجه: حلقه کسر موجودی که قبلاً در اینجا بود، طبق بررسی‌های اخیر شما حذف شده است.
            # این باعث می‌شود کسر موجودی فقط از طریق سیگنال انجام شود و از کسر دو برابر جلوگیری کند.
            # for item in visit.items.all():
            #     DrugBatch.remove_from_batches(item.drug, item.quantity) # این خط باید حذف شده باشد

            print(f"DEBUG: Visit (PK: {visit.pk}) status set to 'completed' and saved.")
            print(f"DEBUG: Visit (PK: {visit.pk}) completion successful.")
            messages.success(request, 'ویزیت با موفقیت تکمیل و موجودی دارو کسر شد.')
            return redirect('visits:visit_detail', pk=visit.pk)
    except Exception as e:
        messages.error(request, f"خطا در تکمیل ویزیت: {e}")
        print(f"ERROR: Error completing visit {visit.pk}: {e}")
        # اگر خطایی در سیگنال (مثلاً موجودی کافی نیست) رخ دهد، اینجا دریافت و گزارش می‌شود.
        return redirect('visits:visit_detail', pk=visit.pk)


# Ajax view for patient search (Select2)
@login_required
def patient_search_ajax(request):
    """
    جستجوی بیماران برای Select2 در فرم ویزیت.
    """
    term = request.GET.get('term', '')
    if term:
        patients = Patient.objects.filter(
            Q(first_name__icontains=term) |
            Q(last_name__icontains=term) |
            Q(national_code__icontains=term) |
            Q(personnel_number__icontains=term)
        )[:10]
        results = []
        for p in patients:
            results.append({
                'id': p.pk,
                # 'full_name_and_identifiers' باید به عنوان یک property در مدل Patient تعریف شده باشد
                'text': p.full_name_and_identifiers 
            })
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})

# Ajax view for drug search (Select2)
@login_required
def drug_search_ajax(request):
    """
    جستجوی داروها برای Select2 در فرم آیتم ویزیت.
    """
    term = request.GET.get('term', '')
    if term:
        drugs = Drug.objects.filter(
            Q(name__icontains=term) |
            Q(generic_name__icontains=term) |
            Q(drug_code__icontains=term)
        )[:10]
        results = []
        for d in drugs:
            results.append({
                'id': d.pk,
                # 'form_display' و 'total_quantity' باید به عنوان property در مدل Drug تعریف شده باشند
                'text': f"{d.name} ({d.form_display}) - موجودی: {d.total_quantity}" 
            })
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})

@login_required
def api_unread_referred_visits_count(request):
    """
    این API تعداد ویزیت‌های ارجاع داده شده به کاربر فعلی را که هنوز "خوانده نشده‌اند" برمی‌گرداند.
    """
    # فیلتر کردن ویزیت‌هایی که:
    # 1. به کاربر فعلی (request.user) ارجاع داده شده‌اند (assigned_to).
    # 2. هنوز خوانده نشده‌اند (is_read=False).
    # 3. یک فیلتر وضعیت (status) برای ویزیت‌های ارجاعی. این مقدار باید دقیقاً با چیزی که در دیتابیس ذخیره کرده‌اید، مطابقت داشته باشد.
    #    مثلاً اگر در مدل Visit، گزینه‌ای مانند 'referred' یا 'pending_referral' دارید.
    #    من 'referred' را به عنوان مثال قرار داده‌ام.
    unread_count = Visit.objects.filter(
        assigned_to=request.user,  # فیلد صحیح برای ارجاع
        is_read=False,             # فیلد خوانده شده
        status='referred',         # ✅ اطمینان حاصل کنید که این مقدار (مانند 'referred') دقیقاً با وضعیت
                                   #    ویزیت‌های ارجاعی در دیتابیس شما مطابقت دارد.
                                   #    اگر وضعیت خاصی برای ویزیت‌های ارجاعی ندارید، این خط را حذف کنید.
    ).count()

    return JsonResponse({'count': unread_count})

@csrf_exempt # برای سادگی در توسعه، در پروداکشن از CSRF token استفاده کنید
@login_required # اطمینان از اینکه فقط کاربران لاگین شده توکن ارسال می‌کنند
def register_fcm_device(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')

            if not token:
                return JsonResponse({"status": "error", "message": "No FCM token provided."}, status=400)

            # هر بار که توکن جدیدی دریافت می‌شود، آن را با کاربر فعلی مرتبط می‌کند.
            # اگر دستگاهی با همین توکن برای کاربر دیگری وجود دارد، به کاربر فعلی اختصاص داده می‌شود.
            # این کار `fcm_django` را در مدیریت دستگاه‌های هر کاربر یاری می‌دهد.
            device, created = FCMDevice.objects.get_or_create(
                user=request.user, # توکن را به کاربر لاگین شده متصل می‌کند
                registration_id=token,
                defaults={'active': True} # اگر جدید است، فعال باشد
            )
            # اگر دستگاه از قبل وجود داشته، مطمئن می‌شویم که فعال است
            if not created and not device.active:
                device.active = True
                device.save()
            
            print(f"DEBUG: FCM Device {'created' if created else 'updated'} for user {request.user.username} with token {token}")
            return JsonResponse({"status": "success", "message": "FCM device registered successfully."})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON."}, status=400)
        except Exception as e:
            print(f"ERROR: Failed to register FCM device: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Only POST requests are allowed."}, status=405)
@login_required
@permission_required('visits.view_visit_report', raise_exception=True)
def company_visit_report_view(request):
    """
    نمایش گزارشات مربوط به ویزیت شرکت‌ها شامل فیلترها و نمودارها.
    """
    # 1. اعمال فیلترها از طریق درخواست کاربر
    # VisitFilter به طور خودکار request.GET را برای فیلتر کردن queryset استفاده می‌کند.
    # بهینه‌سازی کوئری با select_related برای دسترسی به نام شرکت
    base_queryset_for_report = Visit.objects.select_related('patient__company', 'reason_for_visit', 'treatment_result').all()
    visit_filter = VisitFilter(request.GET, queryset=base_queryset_for_report)
    
    # queryset فیلتر شده بر اساس ورودی‌های کاربر
    filtered_visits = visit_filter.qs

    # 2. پردازش داده‌ها برای جدول خلاصه شرکت‌ها
    # این کوئری تعداد کل ویزیت‌ها و تعداد بیماران منحصربه‌فرد ویزیت‌شده برای هر شرکت را محاسبه می‌کند.
    # شرکت‌هایی که نام ندارند، به عنوان 'نامشخص' در نظر گرفته می‌شوند.
    company_report_data = filtered_visits.values('patient__company__name').annotate(
        total_visits=Count('id'),
        unique_patients_visited=Count('patient', distinct=True)
    ).order_by('-total_visits')

    # برای نمایش 'نامشخص' به جای None برای شرکت‌های بدون نام
    # (می‌توانید این را در تمپلیت نیز هندل کنید، اما اینجا داده را آماده می‌کنیم)
    processed_company_report_data = []
    for item in company_report_data:
        company_name = item['patient__company__name'] if item['patient__company__name'] else 'نامشخص'
        processed_company_report_data.append({
            'company_name': company_name,
            'total_visits': item['total_visits'],
            'unique_patients_visited': item['unique_patients_visited']
        })

    # 3. پردازش داده‌ها برای نمودارها
    
    # نمودار توزیع علت مراجعه (Pie Chart یا Bar Chart)
    # با استفاده از select_related قبلی، به نام علت مراجعه دسترسی داریم
    reason_for_visit_distribution = filtered_visits.values('reason_for_visit__name').annotate(
        count=Count('id')
    ).order_by('reason_for_visit__name')

    reason_labels = [item['reason_for_visit__name'] if item['reason_for_visit__name'] else 'نامشخص' for item in reason_for_visit_distribution]
    reason_counts = [item['count'] for item in reason_for_visit_distribution]
    
    # نمودار توزیع نتیجه درمان (Pie Chart یا Bar Chart)
    # با استفاده از select_related قبلی، به نام نتیجه درمان دسترسی داریم
    treatment_result_distribution = filtered_visits.values('treatment_result__name').annotate(
        count=Count('id')
    ).order_by('treatment_result__name')

    treatment_labels = [item['treatment_result__name'] if item['treatment_result__name'] else 'نامشخص' for item in treatment_result_distribution]
    treatment_counts = [item['count'] for item in treatment_result_distribution]

    # نمودار روند ویزیت‌ها در طول زمان (Line Chart)
    # گروه‌بندی بر اساس ماه برای نمایش روند ماهانه
    monthly_visit_trend = filtered_visits.annotate(
        month=TruncMonth('visit_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    # تبدیل تاریخ‌های میلادی به شمسی برای نمایش در نمودار
    monthly_trend_labels = []
    monthly_trend_counts = []
    for item in monthly_visit_trend:
        # تبدیل تاریخ میلادی (datetime) به شمسی با jdatetime
        # اطمینان حاصل کنید که item['month'] یک datetime object است
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=item['month'])
            monthly_trend_labels.append(jd.strftime('%Y/%m')) # به عنوان مثال: 1403/04
        except Exception as e:
            print(f"Error converting date to Jalali: {e} for {item['month']}")
            monthly_trend_labels.append(item['month'].strftime('%Y-%m')) # فال‌بک به میلادی
        monthly_trend_counts.append(item['count'])

    context = {
        'filter': visit_filter, # ارسال فیلتر به تمپلیت برای نمایش فرم فیلتر
        'company_report_data': processed_company_report_data, # استفاده از داده‌های پردازش شده
        
        # داده‌ها برای نمودار توزیع علت مراجعه
        'reason_chart_labels': reason_labels,
        'reason_chart_data': reason_counts,

        # داده‌ها برای نمودار توزیع نتیجه درمان
        'treatment_chart_labels': treatment_labels,
        'treatment_chart_data': treatment_counts,

        # داده‌ها برای نمودار روند ماهانه ویزیت‌ها
        'monthly_trend_labels': monthly_trend_labels,
        'monthly_trend_data': monthly_trend_counts,
    }
    
    return render(request, 'visits/reports/company_visits_report.html', context)
# مطمئن شوید این serializer را import می‌کنید

