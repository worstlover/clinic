# D:\final\core\urls.py
from . import views
from django.urls import path
from django.contrib.auth.views import LogoutView # این خط رو دیگه لازم ندارید اگه CustomLogoutView رو از final/urls.py ایمپورت کردید
from .views import (
    # CustomLoginView, dashboard, # <--- اینها حذف میشن
    user_profile, # این باقی میمونه چون در core.views.py هست و در final/urls.py تعریف نشده.
    patient_list, patient_create, patient_detail, patient_update, patient_delete,
    company_list, company_create, company_detail, company_update, company_delete,upload_personnel_file,process_personnel_import
)

app_name = 'core' # <--- این باقی میمونه چون برای URLهای patient و company هنوز از این استفاده میکنیم

urlpatterns = [
    # Authentication & Profile
    #path('login/', CustomLoginView.as_view(), name='login'), # <--- حذف شد
    #path('logout/', LogoutView.as_view(next_page='core:login'), name='logout'), # <--- حذف شد
    path('profile/', user_profile, name='user_profile'),
    path('upload-personnel/', views.upload_personnel_file, name='upload_personnel_file'),
    path('process-personnel-import/', views.process_personnel_import, name='process_personnel_import'),

    # Dashboard
    # path('dashboard/', dashboard, name='dashboard'), # <--- حذف شد
    # path('', dashboard, name='home'), # <--- حذف شد

    # Company Management (اینها باقی میمونند و تحت namespace 'core' خواهند بود)
    path('companies/', company_list, name='company_list'),
    path('companies/add/', company_create, name='company_create'),
    path('companies/<int:pk>/', company_detail, name='company_detail'),
    path('companies/<int:pk>/edit/', company_update, name='company_update'),
    path('companies/<int:pk>/delete/', company_delete, name='company_delete'),

    # Patient Management (اینها باقی میمونند و تحت namespace 'core' خواهند بود)
    path('patients/', patient_list, name='patient_list'),
    path('patients/add/', patient_create, name='patient_create'),
    path('patients/<int:pk>/', patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', patient_update, name='patient_update'),
    path('patients/<int:pk>/delete/', patient_delete, name='patient_delete'),
    
]