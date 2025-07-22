from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ایمپورت کردن ویوهای لاگین، لاگ اوت و داشبورد مستقیماً از core.views
# فرض بر این است که CustomLoginView و CustomLogoutView و dashboard در core.views تعریف شده‌اند.
from core.views import CustomLoginView, CustomLogoutView, dashboard, RegisterPatientAPIView, LoginPatientAPIView,PatientListAPIView, EmergencyAlertAPIView 

urlpatterns = [
    path('admin/', admin.site.urls),

    # URL های اصلی مربوط به احراز هویت و داشبورد
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('', dashboard, name='home'), # ریدایرکت روت به داشبورد
    path('ckeditor/', include('ckeditor_uploader.urls')),
    # شامل کردن URL های اپلیکیشن های مختلف با namespace های مربوطه
    # هر اپلیکیشن باید app_name خودش را در فایل urls.py خود تعریف کرده باشد.

    # URL های اپلیکیشن Visits
    # مطمئن شوید که visits/urls.py دارای app_name = 'visits' است.
    path('visits/', include('visits.urls')),

    # URL های اپلیکیشن Drugs
    # مطمئن شوید که drugs/urls.py دارای app_name = 'drugs' است.
    path('drugs/', include('drugs.urls')),

    # URL های اپلیکیشن Messages
    # مطمئن شوید که clinic_messages/urls.py دارای app_name = 'clinic_messages' است.
    path('messages/', include('clinic_messages.urls')),

    # URL های اپلیکیشن Patients
    # بر اساس خطای 404 قبلی، به نظر می رسد patients یک اپلیکیشن جداگانه است.
    # مطمئن شوید که patients/urls.py دارای app_name = 'patients' است.
    path('core/', include('core.urls')),

     # --- API URL های جدید برای اپ React ---
    # اینها باید با آدرس های مورد انتظار React در api.js مطابقت داشته باشند
    path('api/auth/register/', RegisterPatientAPIView.as_view(), name='api-react-register'), # <--- تغییر اینجا
    path('api/auth/login/', LoginPatientAPIView.as_view(), name='api-react-login'),     # <--- تغییر اینجا
    path('api/react/alert/', EmergencyAlertAPIView.as_view(), name='api-react-alert'),
    path('api/react/patients/', PatientListAPIView.as_view(), name='api-react-patient-list'),
    path('reports/', include('reports.urls', namespace='reports')), 
    path('select2/', include('django_select2.urls')),
    
    path('lab_results/', include('lab_results.urls', namespace='lab_results'))
]

# مدیریت فایل های MEDIA و STATIC در حالت DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)