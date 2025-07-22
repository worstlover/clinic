# visits/urls.py (نسخه نهایی و صحیح - با اضافه شدن گزارش شرکت)

from django.urls import path
from . import views

app_name = 'visits'

urlpatterns = [
    # URLs اصلی مدیریت ویزیت
    path('', views.visit_list, name='visit_list'),
    path('create/', views.visit_create, name='visit_create'),
    path('<int:pk>/', views.visit_detail, name='visit_detail'),
    path('<int:pk>/update/', views.visit_update, name='visit_update'),
    path('<int:pk>/delete/', views.visit_delete, name='visit_delete'),
    path('create/<int:patient_id>/', views.visit_create, name='visit_create_for_patient'),
    # *** جدید: URLs برای اکشن‌های مربوط به ویزیت ***
    path('<int:pk>/refer/', views.refer_visit, name='refer_visit'),
    path('<int:pk>/complete/', views.complete_visit, name='complete_visit'),

    # URLs مربوط به API ها که در فرم ویزیت استفاده می‌شوند
    path('api/patient-search/', views.PatientSearchAPIView.as_view(), name='patient_search_api'),
    path('api/drug-search/', views.DrugSearchAPIView.as_view(), name='api_drug_search'),
    path('api/patient-detail/', views.patient_detail_api, name='patient_detail_api'),
    # *** جدید: URL برای گزارش شرکت‌ها و ویزیت‌ها ***
    path('reports/company-visits/', views.company_visit_report_view, name='company_visit_report'), #
]