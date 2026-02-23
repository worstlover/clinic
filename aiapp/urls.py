# aiapp/urls.py
from django.urls import path
from . import views

app_name = 'aiapp'

urlpatterns = [
    # تغییر از 'aiapp/upload/' به 'upload/'
    path('upload/', views.upload_visit_scan, name='upload'), 
    
    path('confirm/', views.final_confirm, name='final_confirm'),
]