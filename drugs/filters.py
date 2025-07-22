# D:\final\drugs\filters.py

import django_filters
from django import forms
from django.db.models import Q, Sum, F
from django.utils import timezone
import datetime

from .models import Drug, DrugBatch

class DrugFilter(django_filters.FilterSet):
    # فیلتر بر اساس نام یا نام ژنریک
    name = django_filters.CharFilter(
        method='filter_by_name_or_generic',
        label='نام دارو / ژنریک',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'جستجو بر اساس نام'})
    )

    # فیلتر برای drug_code (فقط عدد)
    drug_code = django_filters.CharFilter( # با CharFilter شروع می‌کنیم
        method='filter_by_drug_code',
        label='کد دارو',
        widget=forms.NumberInput(attrs={'placeholder': 'جستجو بر اساس کد عددی'}) # استفاده از NumberInput
    )

    # فیلتر بر اساس شکل دارویی
    form = django_filters.ChoiceFilter(
        choices=lambda: [(drug_form, drug_form) for drug_form in Drug.objects.values_list('form', flat=True).distinct().exclude(form__isnull=True).exclude(form__exact='')],
        empty_label="همه اشکال دارویی",
        label='شکل دارویی',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # فیلتر برای داروهای با موجودی کم
    is_low_stock = django_filters.BooleanFilter(
        method='filter_is_low_stock',
        label='موجودی کم',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # فیلتر برای داروهای با انقضای نزدیک (90 روز آینده)
    # این فیلتر حالا واقعاً فیلتر می‌کنه
    has_expiring_batches = django_filters.BooleanFilter(
        method='filter_has_expiring_batches',
        label='انقضای نزدیک (90 روز)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Drug
        # نیازی به فیلدهای اینجا نیست چون بالا تعریف کردیم
        fields = []

    def filter_by_name_or_generic(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(name__icontains=value) |
                Q(generic_name__icontains=value)
            )
        return queryset

    # متد جدید برای فیلتر کد دارو (فقط عددی)
    def filter_by_drug_code(self, queryset, name, value):
        if value:
            # مطمئن میشیم که value قابل تبدیل به عدد هست
            if value.isdigit():
                return queryset.filter(drug_code=value)
        return queryset

    def filter_is_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(total_stock__lte=F('min_stock_alert')) # تغییر به total_stock <= min_stock_alert
        return queryset

    # متد اصلاح شده برای فیلتر انقضای نزدیک
    def filter_has_expiring_batches(self, queryset, name, value):
        if value:
            today = timezone.now().date()
            three_months_from_now = today + datetime.timedelta(days=90)
            return queryset.filter(
                # مطمئن میشیم بچ فعال و دارای موجودی باشه
                batches__expiry_date__gte=today,
                batches__expiry_date__lte=three_months_from_now,
                batches__quantity__gt=0,
                batches__is_active=True # اگر is_active در DrugBatch دارید
            ).distinct() # distinct برای جلوگیری از تکرار داروها
        return queryset