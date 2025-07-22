# D:\final\clinic_messages\admin.py (اگر وجود ندارد، آن را بسازید)

from django.contrib import admin
from .models import Message, MessageRecipient, MessageAttachment, Notification

# مدل‌های Message و MessageRecipient و MessageAttachment را قبلاً باید ثبت کرده باشید
# مثال:
# @admin.register(Message)
# class MessageAdmin(admin.ModelAdmin):
#     list_display = ('subject', 'sender', 'created_at')
#     search_fields = ('subject', 'body', 'sender__username')
#     list_filter = ('created_at',)

# @admin.register(MessageRecipient)
# class MessageRecipientAdmin(admin.ModelAdmin):
#     list_display = ('message', 'recipient', 'is_read', 'read_at')
#     list_filter = ('is_read', 'read_at', 'recipient')
#     search_fields = ('message__subject', 'recipient__username')

# --- ثبت مدل Notification ---
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('message_preview', 'recipient', 'sender', 'is_read', 'notification_type', 'created_at', 'link')
    list_filter = ('is_read', 'notification_type', 'created_at', 'recipient', 'sender')
    search_fields = ('message', 'recipient__username', 'sender__username')
    ordering = ('-created_at',)

    def message_preview(self, obj):
        return obj.message[:75] + '...' if len(obj.message) > 75 else obj.message
    message_preview.short_description = "متن اعلان"