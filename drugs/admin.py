# D:\final\drugs\admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (Drug, DrugBatch, PurchaseInvoice, PurchaseInvoiceItem, DrugRequest, DrugRequestItem, Supplier)
from django import forms
from django.db import models
from jalali_date.admin import ModelAdminJalaliMixin
import jdatetime # اضافه کردن برای استفاده از تاریخ شمسی

from django.contrib import admin
from .models import Drug

@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('name', 'drug_code', 'package_type', 'package_size', 'min_stock_alert')
    search_fields = ('name', 'drug_code', 'package_type', 'package_size', 'min_stock_alert')



@admin.register(DrugBatch)
class DrugBatchAdmin(ModelAdminJalaliMixin, admin.ModelAdmin): # اضافه کردن ModelAdminJalaliMixin
    list_display = ('drug', 'batch_number', 'quantity', 'get_jalali_expiry_date', 'get_supplier_name', 'purchase_price', 'selling_price', 'is_expired') # 'is_low_stock' حذف شد
    list_filter = ('expiry_date', 'drug', 'supplier')
    search_fields = ('drug__name', 'batch_number', 'supplier__name')
    ordering = ('-expiry_date',)

    # فیلدها برای فرم اضافه/ویرایش
    fieldsets = (
        (None, {
            'fields': ('drug', 'batch_number', 'quantity', 'production_date', 'expiry_date', 'supplier', 'purchase_price', 'selling_price', 'notes') # 'notes' و 'production_date' اضافه شد
        }),
    )

    # متد برای نمایش تاریخ انقضا شمسی
    @admin.display(description='تاریخ انقضا (شمسی)')
    def get_jalali_expiry_date(self, obj):
        if obj.expiry_date:
            return jdatetime.date.fromgregorian(date=obj.expiry_date).strftime('%Y/%m/%d')
        return "-"
    get_jalali_expiry_date.admin_order_field = 'expiry_date'

    # متد برای نمایش نام تامین کننده
    @admin.display(description='تامین‌کننده')
    def get_supplier_name(self, obj):
        return obj.supplier.name if obj.supplier else "-"
    get_supplier_name.admin_order_field = 'supplier__name'

# Inline برای آیتم‌های فاکتور خرید
class PurchaseInvoiceItemInline(admin.TabularInline):
    model = PurchaseInvoiceItem
    extra = 1
    fields = ('drug', 'quantity', 'unit_price') # 'expiry_date' حذف شد
    autocomplete_fields = ['drug'] # 'drug_batch' به 'drug' تغییر یافت

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(ModelAdminJalaliMixin, admin.ModelAdmin): # اضافه کردن ModelAdminJalaliMixin
    list_display = ('invoice_number', 'get_jalali_invoice_date', 'supplier', 'total_amount')
    list_filter = ('invoice_date', 'supplier')
    search_fields = ('invoice_number', 'supplier__name')
    ordering = ('-invoice_date',)
    inlines = [PurchaseInvoiceItemInline]

    fieldsets = (
        (None, {
            'fields': ('invoice_number', 'supplier', 'invoice_date', 'total_amount', 'notes') # 'total_amount' و 'notes' اضافه شد
        }),
    )

    @admin.display(description='تاریخ فاکتور (شمسی)')
    def get_jalali_invoice_date(self, obj):
        if obj.invoice_date:
            return jdatetime.date.fromgregorian(date=obj.invoice_date).strftime('%Y/%m/%d')
        return "-"
    get_jalali_invoice_date.admin_order_field = 'invoice_date'


class DrugRequestItemInline(admin.TabularInline):
    model = DrugRequestItem
    extra = 1
    fields = ('drug', 'requested_quantity')
    autocomplete_fields = ['drug'] # Enable autocomplete for drug field

class DrugRequestItemInline(admin.TabularInline):
    model = DrugRequestItem
    extra = 1
    fields = ('drug', 'requested_quantity', 'notes') # notes را اضافه کردم
    autocomplete_fields = ['drug']

# <<<<< کلاس ادمین اصلاح شده برای DrugRequest >>>>>
@admin.register(DrugRequest)
class DrugRequestAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('request_code', 'get_jalali_request_date', 'requested_by', 'assigned_approver', 'status')
    list_filter = ('status', 'request_date', 'requested_by', 'assigned_approver')
    search_fields = ('request_code', 'description', 'requested_by__username', 'assigned_approver__username')
    date_hierarchy = 'request_date'
    ordering = ('-request_date',)
    inlines = [DrugRequestItemInline]

    readonly_fields = ('request_code', 'requested_by', 'request_date')

    fieldsets = (
        ("اطلاعات اصلی (غیرقابل ویرایش)", {
            'fields': ('request_code', 'requested_by', 'request_date')
        }),
        ("گردش کار و وضعیت", {
            'fields': ('status', 'assigned_approver', 'description')
        }),
    )

    @admin.display(description='تاریخ درخواست (شمسی)')
    def get_jalali_request_date(self, obj):
        if obj.request_date:
            return jdatetime.datetime.fromgregorian(datetime=obj.request_date).strftime('%Y/%m/%d %H:%M')
        return "-"
    get_jalali_request_date.admin_order_field = 'request_date'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email') # 'phone_number' به 'phone' تغییر یافت
    search_fields = ('name', 'contact_person', 'phone', 'email')
    ordering = ('name',)