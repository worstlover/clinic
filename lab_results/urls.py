# lab_results/urls.py
from django.urls import path
from . import views

app_name = 'lab_results' # <--- Add this line

urlpatterns = [
    path('upload/', views.upload_excel_file, name='upload_excel_file'),
    path('process_import/', views.process_import, name='process_import'),
    path('patient/<int:patient_id>/results/', views.view_patient_lab_results, name='patient_lab_results'),
    path('examination/<int:exam_id>/print/', views.generate_opinion_form, name='generate_opinion_form'),
    path('print/bulk/', views.bulk_print_page, name='bulk_print_page'),
]