from django.urls import path
from . import views

from .views import DrugSearchAPIView, DrugSelect2View, UserSelect2View
app_name = 'drugs' # این فضای نام 'drugs:' را که در redirect ها و reverse_lazy ها استفاده کردید، تعریف می کند.

urlpatterns = [
    # Drug Management URLs
    path('drugs/', views.drug_list, name='drug_list'),
    path('drugs/create/', views.drug_create, name='drug_create'),
    path('drugs/<int:pk>/', views.drug_detail, name='drug_detail'),
    path('drugs/<int:pk>/update/', views.drug_update, name='drug_update'),
    path('drugs/<int:pk>/delete/', views.drug_delete, name='drug_delete'),

    # Drug Batch Management URLs
    path('batches/', views.drug_batch_list, name='drug_batch_list'),
    path('batches/create/', views.drug_batch_create, name='drug_batch_create'),
    path('batches/<int:pk>/', views.drug_batch_detail, name='drug_batch_detail'),
    path('batches/<int:pk>/update/', views.drug_batch_update, name='drug_batch_update'),
    path('batches/<int:pk>/delete/', views.drug_batch_delete, name='drug_batch_delete'),

      # Purchase Invoice URLs
    path('purchase-invoices/', views.purchase_invoice_list, name='purchase_invoice_list'),
    path('purchase-invoices/<int:pk>/print/', views.purchase_invoice_print_view, name='purchase_invoice_print'),
    path('purchase-invoices/create/', views.purchase_invoice_create, name='purchase_invoice_create'),
    path('purchase-invoices/<int:pk>/', views.purchase_invoice_detail, name='purchase_invoice_detail'),
    path('purchase-invoices/<int:pk>/update/', views.purchase_invoice_update, name='purchase_invoice_update'),
    path('purchase-invoices/<int:pk>/delete/', views.purchase_invoice_delete, name='purchase_invoice_delete'),
    path('search-drugs-ajax/', views.search_drugs_ajax, name='search_drugs_ajax'),
    # Drug Request Management URLs
    
    # --- Drug Request URLs ---
    path('requests/', views.drug_request_list, name='drug_request_list'),
    
    # URL برای صفحه تحلیل هوشمند
    path('requests/generate/', views.generate_drug_request_view, name='drug_request_generate'),
    
    # 👇 مسیر جدیدی که باید اضافه کنید 👇
    # این URL برای صفحه‌ای است که پیش‌نویس تولید شده را نمایش می‌دهد و کاربر آن را نهایی می‌کند.
    path('requests/create-from-suggestion/', views.drug_request_create_from_suggestion, name='drug_request_create_from_suggestion'),
    
    # URL برای ایجاد یک درخواست کاملاً جدید و دستی
    path('requests/create/', views.drug_request_create, name='drug_request_create'),
    
    path('requests/<int:pk>/', views.drug_request_detail, name='drug_request_detail'),
    path('requests/<int:pk>/update/', views.drug_request_update, name='drug_request_update'),
    path('requests/<int:pk>/delete/', views.drug_request_delete, name='drug_request_delete'),
    
    # URL جدید برای تبدیل درخواست به فاکتور
    path('requests/<int:pk>/create-invoice/', views.create_invoice_from_request, name='create_invoice_from_request'),
    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/update/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # API URLs
    path('api/drugs/search/', DrugSearchAPIView.as_view(), name='api_drug_search'),
    
    path('select2/users/', UserSelect2View.as_view(), name='select2_users'),
    path('batches/upload/temporary/', views.upload_temporary_inventory, name='upload_temporary_inventory'),
    path('batches/delete/temporary/', views.delete_temporary_inventory, name='delete_temporary_inventory'),
]