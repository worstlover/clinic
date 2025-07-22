# D:\final\core\views.py

from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum
from django.contrib import messages
import sys
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import jdatetime
import datetime
from .models import Patient, Company # مطمئن شوید Company هم ایمپورت شده
from .forms import PatientForm # CompanyForm هم باید ایمپورت شود
from django.http import JsonResponse
from django.db import transaction
from django.forms import inlineformset_factory
from django.db.models import Max
from django.core.paginator import Paginator
from django.db.models import Sum, F
from rest_framework import generics, status
from rest_framework.views import APIView # اضافه شده
from rest_framework.response import Response # اضافه شده
from rest_framework.permissions import IsAuthenticated, AllowAny # AllowAny اضافه شده
# از serializers موجود شما استفاده میکنیم و PatientAuthSerializer رو ایمپورت میکنیم
from .serializers import PatientSerializer, PatientAuthSerializer # DrugSerializer اگر لازم بود
from openpyxl import load_workbook
from django_filters.rest_framework import DjangoFilterBackend 
from clinic_messages.models import Message, MessageRecipient 
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from drugs.models import Drug
from django.contrib.messages.views import SuccessMessageMixin
from core.filters import PatientFilter


# --- ویوهای موجود شما (بدون تغییر) ---
class CustomLoginView(SuccessMessageMixin, LoginView):
    template_name = 'core/login.html'
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard') 
    success_message = "با موفقیت وارد شدید!"

    def form_invalid(self, form):
        messages.error(self.request, "نام کاربری یا رمز عبور اشتباه است.")
        return super().form_invalid(form)

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "با موفقیت خارج شدید!")
        return super().dispatch(request, *args, **kwargs)

@login_required(login_url=reverse_lazy('login'))
def dashboard(request):
    page_title = "داشبورد"
    context = {
        'page_title': page_title,
    }
    return render(request, 'core/dashboard.html', context)

@login_required(login_url='login')
@permission_required('core.view_patient', raise_exception=True)
def patient_list(request):
    """
    نمایش لیست بیماران با قابلیت جستجو، فیلتر پیشرفته و صفحه‌بندی.
    """
    base_queryset = Patient.objects.select_related('company', 'registered_by').all().order_by('-pk')
    patient_filter = PatientFilter(request.GET, queryset=base_queryset)
    advanced_filters_applied = any(
        value for key, value in request.GET.items() if key not in ['q', 'page'] and value
    )
    paginator = Paginator(patient_filter.qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_title': 'لیست بیماران',
        'patients': page_obj,
        'page_obj': page_obj,
        'filter': patient_filter,
        'search_query': request.GET.get('q', ''),
        'advanced_filters_applied': advanced_filters_applied,
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'core/patient_list.html', context)
    
@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.registered_by = request.user
            patient.save()
            messages.success(request, 'بیمار با موفقیت ثبت شد.')
            return redirect('core:patient_list')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید.')
    else:
        form = PatientForm()
    
    context = {
        'form': form,
        'page_title': 'ثبت بیمار جدید'
    }
    return render(request, 'core/patient_form.html', context)

@login_required
def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            patient = form.save()
            messages.success(request, 'اطلاعات بیمار با موفقیت به‌روزرسانی شد.')
            return redirect('core:patient_list')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید.')
    else:
        form = PatientForm(instance=patient)
        
    context = {
        'form': form,
        'page_title': f'ویرایش بیمار: {patient.full_name}'
    }
    return render(request, 'core/patient_form.html', context)

@login_required(login_url=reverse_lazy('login'))
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    # مطمئن شوید مدل Visit وجود دارد و به Patient مرتبط است
    # visits = patient.visits.all().order_by('-visit_date') 
    # فعلاً به خاطر عدم وجود مدل Visit در اینجا، این خط رو کامنت میکنیم.
    visits = [] # placeholder
    context = {
        'page_title': f'جزئیات بیمار: {patient.full_name}',
        'patient': patient,
        'visits': visits
    }
    return render(request, 'core/patient_detail.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('core.delete_patient', raise_exception=True)
def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        messages.success(request, 'بیمار با موفقیت حذف شد!')
        return redirect('patient_list')
    context = {
        'page_title': 'حذف بیمار',
        'object': patient
    }
    return render(request, 'core/confirm_delete.html', context)

@login_required(login_url=reverse_lazy('login'))
def company_list(request):
    companies = Company.objects.all().order_by('name')
    context = {
        'page_title': 'لیست شرکت‌ها',
        'companies': companies
    }
    return render(request, 'core/company_list.html', context)

@login_required(login_url=reverse_lazy('login'))
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'شرکت با موفقیت اضافه شد!')
            return redirect('company_list')
        else:
            messages.error(request, 'خطا در ثبت شرکت. لطفا اطلاعات وارد شده را بررسی کنید.')
    else:
        form = CompanyForm()
    context = {
        'page_title': 'افزودن شرکت جدید',
        'form': form
    }
    return render(request, 'core/company_form.html', context)

@login_required(login_url=reverse_lazy('login'))
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)
    context = {
        'page_title': f'جزئیات شرکت: {company.name}',
        'company': company
    }
    return render(request, 'core/company_detail.html', context)

@login_required(login_url=reverse_lazy('login'))
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'اطلاعات شرکت با موفقیت ویرایش شد!')
            return redirect('company_list')
        else:
            messages.error(request, 'خطا در ویرایش شرکت. لطفا اطلاعات وارد شده را بررسی کنید.')
    else:
        form = CompanyForm(instance=company)
    context = {
        'page_title': f'ویرایش شرکت: {company.name}',
        'form': form
    }
    return render(request, 'core/company_form.html', context)

@login_required(login_url=reverse_lazy('login'))
@permission_required('core.delete_company', raise_exception=True)
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        company.delete()
        messages.success(request, 'شرکت با موفقیت حذف شد!')
        return redirect('company_list')
    context = {
        'page_title': 'حذف شرکت',
        'object': company
    }
    return render(request, 'core/confirm_delete.html', context)

@login_required
def user_profile(request):
    return render(request, 'core/user_profile.html', {'user': request.user})


# --- API Views for React (جدید) ---

class RegisterPatientAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # 👈👈👈 context={'request': request} رو به سریالایزر پاس بده
        serializer = PatientAuthSerializer(data=request.data, context={'request': request}) 
        if serializer.is_valid():
            try:
                patient = serializer.save() 
                return Response({
                    "message": "درخواست ثبت نام با موفقیت ارسال شد و در انتظار تایید مدیر سیستم است.", # 👈 پیام رو دقیق تر کن
                    "patient_id": patient.id,
                    "user": PatientAuthSerializer(patient, context={'request': request}).data # ارسال داده‌های بیمار ثبت نام شده
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Error during patient registration: {e}") 
                return Response({"detail": "خطای سرور هنگام ثبت نام: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        print(f"Serializer errors: {serializer.errors}") 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginPatientAPIView(APIView):
    permission_classes = [AllowAny] # برای لاگین، AllowAny مناسب است

    def post(self, request):
        personnel_number = request.data.get('personnelNumber') 
        national_code_input = request.data.get('nationalCode') 

        if not personnel_number or not national_code_input:
            return Response({"detail": "کد پرسنلی و کد ملی (رمز عبور) الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient = Patient.objects.get(personnel_number=personnel_number)
            
            # --- 👈👈👈 این بخش جدید و حیاتی برای بررسی وضعیت تایید است ---
            if not patient.is_approved:
                return Response({
                    "detail": "حساب کاربری شما هنوز توسط مدیر تایید نشده است. لطفا منتظر بمانید."
                }, status=status.HTTP_403_FORBIDDEN) # 403 Forbidden برای دسترسی ممنوع
            # --- پایان بخش جدید ---

            # --- هشدار امنیتی مهم ---
            # مقایسه مستقیم national_code_input با patient.national_code کاملاً ناامن است.
            # رمز عبور (national_code) باید در دیتابیس هش شده ذخیره شود و هنگام ورود، ورودی کاربر هم هش شده و مقایسه شود.
            # برای مثال، اگر از Django's default User model استفاده می‌کنید، از patient.check_password(national_code_input) استفاده می‌کنید.
            # اگر national_code را هش نکرده‌اید، این سیستم به شدت آسیب‌پذیر است.
            # TODO: در آینده، برای امنیت بیشتر، شماره ملی (که نقش رمز عبور دارد) باید هش شود.
            if patient.national_code == national_code_input: # فرض بر این است که national_code هش نشده است.
                serializer = PatientAuthSerializer(patient)
                
                # --- افزودن توکن به پاسخ (مثال با Simple JWT) ---
                # اگر از Simple JWT استفاده می‌کنید و patient یک User model باشد:
                # refresh = RefreshToken.for_user(patient) 
                # token_data = {
                #     'refresh': str(refresh),
                #     'access': str(refresh.access_token),
                # }
                # return Response({"message": "ورود موفقیت آمیز", "user": serializer.data, "tokens": token_data}, status=status.HTTP_200_OK)

                # در غیر این صورت، پاسخ ساده فعلی:
                return Response({"message": "ورود موفقیت آمیز", "user": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "کد ملی (رمز عبور) اشتباه است."}, status=status.HTTP_401_UNAUTHORIZED)
        except Patient.DoesNotExist:
            return Response({"detail": "کاربری با این کد پرسنلی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error during patient login: {e}") 
            return Response({"detail": "خطای سرور هنگام ورود: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# View برای مدیریت EmergencyAlert ها (در آینده)
class EmergencyAlertAPIView(APIView):
    permission_classes = [IsAuthenticated] # فقط کاربران لاگین شده میتوانند هشدار ارسال کنند

    def post(self, request):
        # از کاربر لاگین شده (که فرض میکنیم یک Patient است) به عنوان فرستنده استفاده میکنیم
        # TODO: این بخش نیاز به تعریف مدل EmergencyAlert و Serializer مربوطه دارد
        # فرض میکنیم request.user به یک Patient متصل است یا میتوانیم از personnel_number ارسالی استفاده کنیم

        # اطلاعاتی که از فرانت اند می آید:
        # {
        #   "user_personnel_id": "P1001",
        #   "location": { "lat": 35.xxx, "lng": 51.xxx, "address": "..." },
        #   "timestamp": "YYYY-MM-DD HH:MM:SS",
        #   "type": "حادثه اضطراری"
        # }
        
        user_personnel_id = request.data.get('user_personnel_id')
        location_data = request.data.get('location')
        timestamp = request.data.get('timestamp')
        incident_type = request.data.get('type')

        if not user_personnel_id or not location_data:
            return Response({"detail": "اطلاعات کاربر و موقعیت مکانی الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient = Patient.objects.get(personnel_number=user_personnel_id)
            # TODO: اینجا باید یک شیء EmergencyAlert ایجاد و ذخیره شود
            # EmergencyAlert.objects.create(
            #     patient=patient,
            #     latitude=location_data.get('lat'),
            #     longitude=location_data.get('lng'),
            #     address_description=location_data.get('address'),
            #     incident_type=incident_type,
            #     timestamp=timestamp # اگر timestamp را به عنوان string میفرستیم، باید parse شود
            # )
            
            print(f"Emergency Alert Received for {patient.full_name}: Type={incident_type}, Location={location_data}, Time={timestamp}")
            return Response({"message": "گزارش حادثه با موفقیت دریافت شد."}, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({"detail": "بیمار با کد پرسنلی ارسال شده یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --------------------------------------------------
# پروفایل کاربر (User Profile) - این ویو HTML برمی‌گرداند، نه JSON
# --------------------------------------------------
@login_required
def user_profile(request):
    return render(request, 'core/user_profile.html', {'user': request.user})


# لیست Patient ها برای API (اگر نیاز باشد)
# این همان generics.ListAPIView است که در کامنت قبلی داشتید
class PatientListAPIView(generics.ListAPIView):
    queryset = Patient.objects.all().order_by('last_name', 'first_name')
    serializer_class = PatientSerializer # از PatientSerializer موجود شما استفاده میکند
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientFilter # اگر فیلتر برای API نیاز دارید
    permission_classes = [IsAuthenticated] # فقط کاربران احراز هویت شده می‌توانند این لیست را ببینند
 
def upload_personnel_file(request):
    """
    نمایش صفحه آپلود فایل اکسل مشخصات پرسنل.
    """
    return render(request, 'core/upload_personnel.html')

def process_personnel_import(request):
    """
    پردازش فایل اکسل مشخصات پرسنل:
    - اگر کد ملی وجود داشته باشد، شماره پرسنلی را به‌روزرسانی می‌کند.
    - اگر کد ملی وجود نداشته باشد، بیمار جدیدی را ثبت می‌کند.
    """
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, 'لطفاً یک فایل اکسل انتخاب کنید.')
            return redirect('core:upload_personnel_file')

        excel_file = request.FILES['excel_file']

        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'فایل انتخاب شده باید از نوع اکسل (xlsx یا xls) باشد.')
            return redirect('core:upload_personnel_file')

        try:
            workbook = load_workbook(excel_file)
            sheet = workbook.active
            # اصلاح: خواندن و پاک کردن فاصله‌های خالی از سربرگ‌ها
            header = [str(cell.value).strip() if cell.value is not None else '' for cell in sheet[1]] 

            # تعریف نگاشت سربرگ‌های اکسل به فیلدهای مدل
            column_mapping = {
                'نام': 'first_name',
                'نام خانوادگی': 'last_name',
                'کد ملی': 'national_code',
                'شماره پرسنلی': 'personnel_number',
            }

            # پیدا کردن ایندکس ستون‌ها بر اساس سربرگ
            col_indices = {}
            for excel_header, model_field in column_mapping.items():
                try:
                    # حالا 'header' خودش فاقد فاصله‌های اضافی است
                    col_indices[model_field] = header.index(excel_header)
                except ValueError:
                    messages.warning(request, f'سربرگ "{excel_header}" در فایل اکسل یافت نشد. این ستون نادیده گرفته خواهد شد.')
                    col_indices[model_field] = -1

            if col_indices.get('national_code', -1) == -1:
                messages.error(request, 'ستون "کد ملی" در فایل اکسل ضروری است و یافت نشد.')
                return redirect('core:upload_personnel_file')
            
            # (ادامه کد شما...)
            updated_count = 0
            created_count = 0
            skipped_count = 0

            with transaction.atomic():
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
                    row_data = [cell.value for cell in row]

                    national_code = None
                    if col_indices['national_code'] != -1:
                        national_code = str(row_data[col_indices['national_code']]).strip() if row_data[col_indices['national_code']] else None

                    if not national_code:
                        messages.warning(request, f'ردیف {row_idx}: کد ملی خالی است. این ردیف نادیده گرفته شد.')
                        skipped_count += 1
                        continue

                    personnel_number = None
                    if col_indices['personnel_number'] != -1:
                        personnel_number = str(row_data[col_indices['personnel_number']]).strip() if row_data[col_indices['personnel_number']] else None

                    first_name = None
                    if col_indices['first_name'] != -1:
                        first_name = str(row_data[col_indices['first_name']]).strip() if row_data[col_indices['first_name']] else ''

                    last_name = None
                    if col_indices['last_name'] != -1:
                        last_name = str(row_data[col_indices['last_name']]).strip() if row_data[col_indices['last_name']] else ''

                    try:
                        patient, created = Patient.objects.get_or_create(
                            national_code=national_code,
                            defaults={
                                'first_name': first_name,
                                'last_name': last_name,
                                'personnel_number': personnel_number,
                            }
                        )
                        if created:
                            created_count += 1
                            messages.success(request, f'ردیف {row_idx}: بیمار جدید با کد ملی {national_code} و شماره پرسنلی {personnel_number} ثبت شد.')
                        else:
                            if patient.personnel_number != personnel_number:
                                patient.personnel_number = personnel_number
                                # همچنین نام و نام خانوادگی را در صورت وجود در اکسل و عدم خالی بودن به روز رسانی کنید
                                patient.first_name = first_name if first_name else patient.first_name
                                patient.last_name = last_name if last_name else patient.last_name
                                patient.save()
                                updated_count += 1
                                messages.info(request, f'ردیف {row_idx}: شماره پرسنلی برای کد ملی {national_code} به {personnel_number} به‌روزرسانی شد.')
                            else:
                                messages.info(request, f'ردیف {row_idx}: بیمار با کد ملی {national_code} از قبل موجود بود و نیازی به به‌روزرسانی شماره پرسنلی نبود.')


                    except Exception as e:
                        messages.error(request, f'ردیف {row_idx}: خطایی در پردازش رخ داد: {e}')
                        skipped_count += 1

            messages.success(request, f'فرآیند آپلود پرسنل با موفقیت به پایان رسید. تعداد ثبت شده: {created_count}، تعداد به‌روزرسانی شده: {updated_count}، تعداد نادیده گرفته شده: {skipped_count}.')

        except Exception as e:
            messages.error(request, f'خطا در خواندن فایل اکسل: {e}')
            return redirect('core:upload_personnel_file')

    return redirect('core:upload_personnel_file')