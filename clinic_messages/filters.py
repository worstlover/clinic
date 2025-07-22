# D:\final\clinic_messages\filters.py

import django_filters
from django_filters import DateFilter, CharFilter, ChoiceFilter
from django.db.models import Q
from django.contrib.auth import get_user_model

import jdatetime 

from .models import Message, MessageRecipient

User = get_user_model()

class MessageFilter(django_filters.FilterSet):
    # فیلتر برای موضوع پیام (Case-insensitive contains)
    subject__icontains = CharFilter(field_name='message__subject', lookup_expr='icontains', label='موضوع')
    # فیلتر برای متن پیام (Case-insensitive contains)
    body__icontains = CharFilter(field_name='message__body', lookup_expr='icontains', label='متن پیام')
    # فیلتر برای نام کاربری فرستنده (Case-insensitive contains)
    sender__username__icontains = CharFilter(field_name='message__sender__username', lookup_expr='icontains', label='فرستنده')
    
    # فیلتر برای وضعیت خوانده شدن
    is_read = ChoiceFilter(
        choices=[('read', 'خوانده شده'), ('unread', 'نخوانده')],
        method='filter_by_read_status',
        label='وضعیت خوانده شدن',
        empty_label="همه پیام‌ها"
    )

    # فیلترهای تاریخ شمسی برای created_at (تاریخ ایجاد پیام)
    start_date_fa = DateFilter(field_name='message__created_at', method='filter_by_start_date_fa', label='از تاریخ')
    end_date_fa = DateFilter(field_name='message__created_at', method='filter_by_end_date_fa', label='تا تاریخ')


    class Meta:
        model = MessageRecipient
        fields = [] 


    def filter_by_read_status(self, queryset, name, value):
        if value == 'read':
            return queryset.filter(read_at__isnull=False)
        elif value == 'unread':
            return queryset.filter(read_at__isnull=True)
        return queryset

    def filter_by_start_date_fa(self, queryset, name, value):
        if value:
            return queryset.filter(message__created_at__date__gte=value)
        return queryset

    def filter_by_end_date_fa(self, queryset, name, value):
        if value:
            return queryset.filter(message__created_at__date__lte=value)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if 'query' in self.data and self.data['query']:
            query = self.data['query']
            return queryset.filter(
                Q(message__subject__icontains=query) |
                Q(message__body__icontains=query) |
                Q(message__sender__username__icontains=query)
            )
        return queryset