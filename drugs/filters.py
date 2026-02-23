import django_filters
from django import forms
from .models import Drug
from django.db.models import Q, F, Count
from django.utils import timezone
import datetime

class DrugFilter(django_filters.FilterSet):
    # فیلتر نام یا نام ژنریک
    name = django_filters.CharFilter(
        method='filter_by_name_or_generic',
        label='نام دارو / ژنریک',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجو نام...'})
    )

    # فیلتر کد دارو
    drug_code = django_filters.CharFilter(
        method='filter_by_drug_code',
        label='کد دارو',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'کد عددی...'})
    )

    # فیلتر شکل دارویی (بهینه‌سازی شده برای پرفورمنس)
    form = django_filters.ChoiceFilter(
        choices=lambda: [(f, f) for f in Drug.objects.values_list('form', flat=True).distinct() if f],
        empty_label="همه اشکال",
        label='شکل دارو',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # فیلتر موجودی کم
    is_low_stock = django_filters.BooleanFilter(
        method='filter_is_low_stock',
        label='موجودی کم',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # فیلتر انقضای نزدیک
    has_expiring_batches = django_filters.BooleanFilter(
        method='filter_has_expiring_batches',
        label='انقضای نزدیک',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # ⭐ فیلتر جدید: داروهای بدون بارکد
    no_barcode = django_filters.BooleanFilter(
        method='filter_no_barcode',
        label='بدون بارکد',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Drug
        fields = []

    def filter_by_name_or_generic(self, queryset, name, value):
        if value:
            return queryset.filter(Q(name__icontains=value) | Q(generic_name__icontains=value))
        return queryset

    def filter_by_drug_code(self, queryset, name, value):
        if value and value.isdigit():
            return queryset.filter(drug_code=value)
        return queryset

    def filter_is_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(total_stock__lte=F('min_stock_alert'))
        return queryset

    def filter_has_expiring_batches(self, queryset, name, value):
        if value:
            today = timezone.now().date()
            future = today + datetime.timedelta(days=90)
            return queryset.filter(
                batches__expiry_date__gte=today,
                batches__expiry_date__lte=future,
                batches__quantity__gt=0
            ).distinct()
        return queryset

    def filter_no_barcode(self, queryset, name, value):
        if value:
            # داروهایی که هیچ رکوردی در DrugBarcode ندارند
            return queryset.annotate(num_barcodes=Count('barcodes')).filter(num_barcodes=0)
        return queryset