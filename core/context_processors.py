# D:\final\core\context_processors.py

from django.apps import apps
from django.db.models import Count

def unread_messages_count(request):
    if request.user.is_authenticated:
        # به جای import مستقیم، از get_model استفاده کنید
        MessageRecipient = apps.get_model('clinic_messages', 'MessageRecipient')
        count = MessageRecipient.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_messages_count': count}
    return {'unread_messages_count': 0}