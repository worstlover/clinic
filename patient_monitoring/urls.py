from django.urls import path
from . import views

app_name = 'patient_monitoring'
urlpatterns = [
    path('report/<int:patient_id>/', views.patient_report_view, name='patient_report'),
]