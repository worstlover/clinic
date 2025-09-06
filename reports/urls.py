# D:\final\reports\urls.py

from django.urls import path
from . import views # ویوهای اپلیکیشن reports را ایمپورت می‌کنیم

app_name = 'reports' # <--- !!! بسیار مهم: فضای نام این اپلیکیشن را "reports" قرار می‌دهیم !!!

urlpatterns = [
    # ویوهای گزارش شما
    # نام‌گذاری URLها (name='...') باید با آنچه در قالب‌ها استفاده می‌کنید، مطابقت داشته باشد.
    
    # گزارش بیماران
    path('patients/', views.patient_report_view, name='patient_report'),

    # گزارش عمومی ویزیت‌ها
    path('visits/all/', views.generic_visit_report_view, name='generic_visit_report'),

    # گزارش داروها
    path('drugs/', views.drug_report_view, name='drug_report'),

    # اگر company_visit_report_view را از اپ visits به اینجا منتقل کرده‌اید:
    path('company-visits/', views.company_visit_report_view, name='company_visit_report'),
    path('examinations/all/', views.reports_view, name='all_examinations_report'),
    path('export/excel/', views.export_excel, name='export_excel'),
    
]