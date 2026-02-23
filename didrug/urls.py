# didrug/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.process_drug_info, name='didrug_index'),
    path('process/', views.process_drug_info, name='process_data'),
]