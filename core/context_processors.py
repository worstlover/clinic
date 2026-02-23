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
def user_groups_processor(request):
    """
    متغیرهای مربوط به گروه‌های کاربری را برای استفاده در تمام تمپلیت‌ها به کانتکست اضافه می‌کند.
    """
    context = {}
    
    # فقط در صورتی که کاربر لاگین کرده باشد، گروه‌ها را بررسی کن
    if request.user.is_authenticated:
        # با یک کوئری، لیست نام تمام گروه‌های کاربر را می‌گیریم تا بهینه‌تر باشد
        user_groups = set(request.user.groups.values_list('name', flat=True))
        
        # بررسی نقش‌های فردی
        context['is_doctor'] = 'Doctor' in user_groups
        context['is_supervisor'] = 'Supervisor' in user_groups
        context['is_nurse'] = 'Nurse' in user_groups
        context['is_supplier'] = 'Supplier' in user_groups
        context['is_accountant'] = 'Accountant' in user_groups
        context['is_personnel'] = 'Personnel' in user_groups

        # ساخت متغیرهای ترکیبی برای شرط‌های پیچیده‌تر
        context['is_medical_staff'] = any([context['is_doctor'], context['is_supervisor'], context['is_nurse']])
        context['is_management'] = any([context['is_doctor'], context['is_supervisor']])
        
    return context

# core/context_processors.py

def theme_picker(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # لیست دستگاه‌های موبایل
    is_mobile = any(device in user_agent for device in ['iphone', 'android', 'mobile', 'webos'])
    
    # تعیین نام فایل (مطمئن شو این فایل‌ها در پوشه templates هستند)
    template_name = 'base_mobile.html' if is_mobile else 'base.html'
    
    return {
        'main_base': template_name
    }