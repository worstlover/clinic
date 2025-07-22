# D:\final\clinic_messages\urls.py

from django.urls import path
from .import views
from .views import UserSearchAPIView, export_message_to_word, ConvertDocxToHtmlAPIView
app_name = 'clinic_messages'

urlpatterns = [
    path('api/users/search/', UserSearchAPIView.as_view(), name='user_search_api'),
    path('inbox/', views.message_inbox, name='message_inbox'),
    path('sent/', views.SentMessageListView.as_view(), name='message_sent'),
    path('create/', views.message_create, name='message_create'),
    path('<int:pk>/', views.message_detail, name='message_detail'),
    path('<int:pk>/reply/', views.message_reply, name='message_reply'),
    # path('<int:pk>/delete/', views.message_delete, name='message_delete'), # اگر این ویو را دارید
    path('<int:pk>/export/word/', export_message_to_word, name='message_export_word'),
    # API Endpoints
    path('convert-docx-to-html/', ConvertDocxToHtmlAPIView.as_view(), name='convert_docx_to_html'),
    path('convert-docx-to-html/', views.ConvertDocxToHtmlAPIView.as_view(), name='convert_docx_to_html'),
    path('api/messages/', views.UserMessageListAPIView.as_view(), name='api_message_list'),
    path('api/unread_count/', views.UnreadMessagesCountAPIView.as_view(), name='api_unread_count'),
    # نام کلاس API View را اصلاح می‌کنیم
    path('api/<int:pk>/read/', views.MessageMarkAsReadAPIView.as_view(), name='api_mark_message_as_read'),
    path('api/users/search/', views.UserSearchAPIView.as_view(), name='api_user_search'),
    path('ckeditor_upload/', views.ckeditor_upload_file, name='ckeditor_upload_file'),
    path('export_composed_message_to_word/', views.export_composed_message_to_word, name='export_composed_message_to_word'),
]