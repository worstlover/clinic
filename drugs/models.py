# D:\final\drugs\models.py
from django.db import models
from django.contrib.auth.models import User
import jdatetime
import datetime
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Max
from datetime import date # اضافه کردن
from persiantools import jdatetime
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from persiantools.jdatetime import JalaliDate
from decimal import Decimal
import uuid
from django.utils.crypto import get_random_string
DRUG_FORM_CHOICES = [
    ('tablet', 'قرص'),
    ('capsule', 'کپسول'),
    ('syrup', 'شربت'),
    ('injection', 'آمپول/تزریقی'),
    ('cream', 'کرم/پماد'),
    ('gel', 'ژل'),
    ('solution', 'محلول'),
    ('suspension', 'سوسپانسیون'),
    ('drops', 'قطره'),
    ('suppository', 'شیاف'),
    ('aerosol', 'اسپری/افشانه'),
    ('powder', 'پودر'),
    ('vial', 'ویال'),
    ('other', 'سایر'),
]

DRUG_UNIT_CHOICES = [
    ('packet', 'بسته'),
    ('box', 'جعبه'),
    ('bottle', 'بطری'),
    ('blister', 'ورق'), # مثلا برای قرص
    ('ampoule','عدد'),
    ('vial', 'عدد (ویال)'),
    ('tube', 'تیوب'), # برای کرم
    ('can', 'قوطی'),
    ('other', 'سایر'),
]


INVOICE_STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('cancelled', 'لغو شده'),
        ('final', 'نهایی شده'), # اطمینان حاصل کنید که 'final' در Choices شما وجود دارد
        ('draft', 'پیش‌نویس'), # اطمینان حاصل کنید که 'draft' در Choices شما وجود دارد
    ]

# ⛔️ این تعریف DrugRequestWorkflowLog باید حذف شود یا با تعریف کاملتر جایگزین شود ⛔️
# class DrugRequestWorkflowLog(models.Model):
#     drug_request = models.ForeignKey('DrugRequest', on_delete=models.CASCADE, related_name='workflow_logs', verbose_name="درخواست دارو")
#     action = models.CharField(max_length=100, verbose_name="عملیات انجام شده") # مثال: "تایید پزشک", "رد سوپروایزر", "ایجاد"
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="کاربر")
#     timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
#     notes = models.TextField(blank=True, null=True, verbose_name="توضیحات/دلیل")

#     class Meta:
#         verbose_name = "لاگ گردش کار درخواست دارو"
#         verbose_name_plural = "لاگ‌های گردش کار درخواست دارو"
#         ordering = ['-timestamp'] # نمایش جدیدترین لاگ‌ها در ابتدا

#     def __str__(self):
#         return f"{self.action} برای درخواست {self.drug_request.pk} توسط {self.user.username if self.user else 'سیستم'} در {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class Drug(models.Model):
    name = models.CharField(max_length=255,unique=True, verbose_name="نام دارو")
    drug_code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="کد دارو")
    generic_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="نام ژنریک")
    form = models.CharField(max_length=50, choices=DRUG_FORM_CHOICES, default='tablet', verbose_name="شکل دارویی")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    min_stock_alert = models.IntegerField(default=10, verbose_name="حداقل موجودی هشدار")
    reorder_point = models.IntegerField(default=20, verbose_name="نقطه سفارش مجدد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ آخرین بروزرسانی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    unit = models.CharField(max_length=50, choices=DRUG_UNIT_CHOICES, verbose_name="واحد بسته‌بندی",default='عدد')
    class Meta:
        verbose_name = "دارو"
        verbose_name_plural = "داروها"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_quantity(self):
        # Calculates the total quantity of this drug across all batches
        # Ensure 'batches' related_name is correct for DrugBatch model
        return self.batches.aggregate(total=Sum('quantity'))['total'] or 0
    def is_low_stock(self):
        """
        بررسی می‌کند که آیا موجودی دارو کمتر یا مساوی با حداقل موجودی هشدار است.
        """
        return self.total_quantity <= self.min_stock_alert
    @property
    def is_low_stock(self):
        return self.total_quantity <= self.min_stock_alert

    # ⭐ جدید: متد برای بررسی داروهای در شرف انقضا
    @property
    def has_expiring_batches(self):
        # Check if any batches are expiring within 90 days from now
        future_date = timezone.now() + datetime.timedelta(days=90)
        return self.batches.filter(expiry_date__lte=future_date, quantity__gt=0).exists()

# 2. مدل تامین‌کننده (Supplier)
class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="نام تامین‌کننده")
    contact_person = models.CharField(max_length=255, blank=True, null=True, verbose_name="فرد تماس")
    phone = models.CharField(max_length=15, blank=True, null=True, verbose_name="شماره تماس") # نام فیلد 'phone' است
    email = models.EmailField(blank=True, null=True, verbose_name="ایمیل")
    address = models.TextField(blank=True, null=True, verbose_name="آدرس")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات") # اضافه شد

    # اگر نیاز به این فیلدها در این مدل هست، اضافه کنید
    # is_active = models.BooleanField(default=True, verbose_name="فعال")
    # created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    # updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "تامین‌کننده"
        verbose_name_plural = "تامین‌کنندگان"
        ordering = ['name']

    def __str__(self):
        return self.name
# 3. مدل بچ دارو (DrugBatch)


class DrugBatch(models.Model):
    drug = models.ForeignKey('Drug', on_delete=models.CASCADE, related_name='batches', verbose_name="دارو")
    batch_number = models.CharField(max_length=100, unique=True, verbose_name="شماره بچ")
    quantity = models.PositiveIntegerField(default=0, verbose_name="موجودی") 
    manufacturing_date = models.DateField(blank=True, null=True, verbose_name="تاریخ تولید")
    expiry_date = models.DateField(verbose_name="تاریخ انقضا")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت خرید")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="قیمت فروش")
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="تامین‌کننده")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    # اگر نیاز دارید هر بچ بداند از کدام فاکتور خرید آمده است:
    # purchase_invoice = models.ForeignKey('PurchaseInvoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='drug_batches', verbose_name="فاکتور خرید") 
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    is_temporary = models.BooleanField(
        default=False,
        verbose_name="موجودی موقت (کاذب)",
        help_text="در صورت انتخاب، این موجودی پس از انبارگردانی حذف خواهد شد."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "بچ دارو"
        verbose_name_plural = "بچ‌های دارو"
        ordering = ['-expiry_date']
        # unique_together = ('drug', 'batch_number') # ⚠️ این خط باید حذف شود چون batch_number خودش unique است.


    def __str__(self):
        return f"{self.drug.name} ({self.batch_number}) - Exp: {self.expiry_date}"

    @property
    def is_expired(self):
        return self.expiry_date and self.expiry_date < date.today() # Import 'date' from datetime

    def add_stock(self, quantity_to_add):
        self.quantity += quantity_to_add
        self.save(update_fields=['quantity']) # فقط فیلد quantity را آپدیت کن

    def remove_stock(self, quantity_to_remove):
        print(f"DEBUG: remove_stock called on batch PK {self.pk}, batch_number: {self.batch_number} for drug: {self.drug.name}")
        print(f"DEBUG: Attempting to remove {quantity_to_remove} from current quantity {self.quantity}")
        if self.quantity < quantity_to_remove:
            print(f"DEBUG ERROR: Not enough stock in batch {self.batch_number} to remove {quantity_to_remove}. Current: {self.quantity}")
            raise ValueError(f"Not enough stock in batch {self.batch_number} to remove {quantity_to_remove}. Current: {self.quantity}")
        self.quantity -= quantity_to_remove
        self.save(update_fields=['quantity'])
        print(f"DEBUG: Successfully removed {quantity_to_remove}. New quantity for batch {self.batch_number}: {self.quantity}")

    @classmethod
    def remove_from_batches(cls, drug, quantity_to_remove):
        print(f"DEBUG: remove_from_batches called for drug: {drug.name} (PK: {drug.pk}) with total quantity to remove: {quantity_to_remove}")
        batches = cls.objects.filter(drug=drug, quantity__gt=0).order_by('expiry_date')
        remaining_to_remove = quantity_to_remove

        for batch in batches:
            if remaining_to_remove <= 0:
                print("DEBUG: remaining_to_remove is 0 or less. Breaking loop.")
                break
            
            if batch.quantity >= remaining_to_remove:
                print(f"DEBUG: Batch {batch.batch_number} (PK: {batch.pk}) has {batch.quantity}. Removing {remaining_to_remove}.")
                batch.quantity -= remaining_to_remove
                batch.save()
                remaining_to_remove = 0
                print(f"DEBUG: Batch {batch.batch_number} new quantity: {batch.quantity}. remaining_to_remove is now 0.")
            else:
                qty_removed_from_this_batch = batch.quantity
                print(f"DEBUG: Batch {batch.batch_number} (PK: {batch.pk}) has {batch.quantity}. Removing all of it ({qty_removed_from_this_batch}).")
                remaining_to_remove -= batch.quantity
                batch.quantity = 0
                batch.save()
                print(f"DEBUG: Batch {batch.batch_number} new quantity: {batch.quantity}. Remaining to remove: {remaining_to_remove}.")
        
        if remaining_to_remove > 0:
            print(f"DEBUG ERROR: Not enough total stock for {drug.name}. Remaining unfulfilled: {remaining_to_remove}")
            raise ValueError(f"Not enough stock for {drug.name}. Remaining to remove: {remaining_to_remove}")
    def get_jalali_expiry_date(self):
        """تاریخ انقضای میلادی را به شمسی تبدیل می‌کند."""
        if self.expiry_date:
            return JalaliDate.to_jalali(self.expiry_date).strftime('%Y/%m/%d')
        return "نامشخص"      

# --- PurchaseInvoice Model ---
class PurchaseInvoice(models.Model):
    invoice_number = models.CharField(max_length=100, unique=True, verbose_name="شماره فاکتور")
    invoice_date = models.DateField(verbose_name="تاریخ فاکتور") 
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="تامین‌کننده")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="مبلغ کل")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ایجاد کننده")
    status = models.CharField(max_length=10, choices=[ # فرض می کنیم INVOICE_STATUS_CHOICES تعریف شده است
        ('draft', 'پیش‌نویس'),
        ('final', 'نهایی شده'),
        ('paid', 'پرداخت شده'),
        ('pending', 'در انتظار پرداخت'),
        ('cancelled', 'لغو شده'),
    ], default='draft', verbose_name="وضعیت فاکتور")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت در سیستم") 
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ آخرین بروزرسانی") 

    class Meta:
        verbose_name = "فاکتور خرید"
        verbose_name_plural = "فاکتورهای خرید"
        ordering = ['-invoice_date', '-created_at']

    def __str__(self):
        return f"فاکتور {self.invoice_number} از {self.supplier.name if self.supplier else 'ناشناس'}"
    
    def get_jalali_invoice_date(self):
        if self.invoice_date:
            return JalaliDate(self.invoice_date).strftime('%Y/%m/%d')
        return "-"

    def calculate_total_amount(self):
        """مبلغ کل فاکتور را بر اساس آیتم‌ها محاسبه می‌کند."""
        total = Decimal('0')
        for item in self.items.all():
            total += item.quantity * item.unit_price
        return total
    
    def update_total_amount(self):
        """مبلغ کل فاکتور را بر اساس آیتم‌های موجود بروزرسانی و ذخیره می‌کند."""
        new_total = self.calculate_total_amount()
        if self.total_amount != new_total:
            self.total_amount = new_total
            self.save(update_fields=['total_amount'])


# --- PurchaseInvoiceItem Model ---
class PurchaseInvoiceItem(models.Model):
    invoice = models.ForeignKey('PurchaseInvoice', on_delete=models.CASCADE, related_name='items', verbose_name="فاکتور")
    drug = models.ForeignKey('Drug', on_delete=models.CASCADE, verbose_name="دارو")
    quantity = models.PositiveIntegerField(verbose_name="تعداد")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت واحد")
    expiry_date = models.DateField(verbose_name="تاریخ انقضا")
    
    batch_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره بچ تولید شده") 
    
    # فیلد total_item_price را به مدل اضافه کنید اگر قبلا حذف کرده‌اید.
    # این به ما کمک می‌کند تا مبلغ جزء را در دیتابیس ذخیره کنیم و محاسبات را تکرار نکنیم.
    total_item_price = models.DecimalField(max_digits=20, decimal_places=0, default=Decimal('0'), verbose_name="مبلغ جزء")


    class Meta:
        verbose_name = "آیتم فاکتور خرید"
        verbose_name_plural = "آیتم‌های فاکتور خرید"
        # ⚠️ اگر می‌خواهید هر فاکتور خرید، آیتمی با drug و batch_number یکسان را تکرار نکند:
        unique_together = ('invoice', 'drug', 'batch_number') # یا ('invoice', 'drug', 'expiry_date', 'batch_number')


    def save(self, *args, **kwargs):
        # 1. محاسبه total_item_price (حتی اگر در فرانت‌اند هم محاسبه شود، اینجا تأیید می‌شود)
        if self.quantity is not None and self.unit_price is not None:
            self.total_item_price = self.quantity * self.unit_price
        else:
            self.total_item_price = Decimal('0')

        # 2. تولید batch_number (فقط در زمان ایجاد اگر خالی بود)
        # این منطق باید قبل از super().save() باشد تا batch_number در شیء موجود باشد.
        if self._state.adding and not self.batch_number:
            drug_name_prefix = self.drug.name[:3].upper() if self.drug and self.drug.name else "UNK"
            drug_form_prefix = self.drug.form[:3].upper() if self.drug and self.drug.form else "NFO" 
            
            if self.expiry_date:
                expiry_part = self.expiry_date.strftime('%Y%m') 
            else:
                expiry_part = "UNKEXP"

            base_batch_prefix_for_counter = f"{drug_name_prefix}-{drug_form_prefix}-{expiry_part}"

            last_batch_number_for_this_drug_prefix = DrugBatch.objects.filter(
                drug=self.drug, 
                batch_number__startswith=base_batch_prefix_for_counter
            ).aggregate(Max('batch_number'))['batch_number__max']

            new_counter = 1
            if last_batch_number_for_this_drug_prefix:
                try:
                    parts = last_batch_number_for_this_drug_prefix.split('-')
                    if len(parts) == 4 and parts[0] == drug_name_prefix and \
                       parts[1] == drug_form_prefix and parts[2] == expiry_part:
                        current_counter_str = parts[3]
                        if current_counter_str.isdigit():
                            new_counter = int(current_counter_str) + 1
                except (ValueError, IndexError):
                    pass
            
            self.batch_number = f"{base_batch_prefix_for_counter}-{new_counter}"
        
        super().save(*args, **kwargs) # آیتم فاکتور را ذخیره می‌کند. سیگنال پس از این اجرا می‌شود.

    def __str__(self):
        return f"{self.drug.name} ({self.quantity}) - {self.invoice.invoice_number}"

# --- Signals ---
@receiver(post_save, sender=PurchaseInvoiceItem)
def handle_purchase_item_save(sender, instance, created, **kwargs):
    # این سیگنال در یک transaction نیست، اما متدهای add_stock و remove_stock خودشان save می‌کنند.
    # برای اطمینان از اتمیک بودن کامل، می‌توانید از transaction.atomic() در ویو استفاده کنید.

    # در اینجا، اگر MANUFACTURING_DATE از طریق PurchaseInvoiceItem وارد نمی‌شود،
    # می‌توانید آن را None یا یک مقدار پیش‌فرض دیگر در نظر بگیرید.
    manufacturing_date_for_batch = None 

    if created:
        # آیتم جدیدی ایجاد شده است
        # تلاش برای یافتن یک بچ موجود با همان batch_number که از PurchaseInvoiceItem آمده است
        # یا ایجاد یک بچ جدید
        drug_batch, batch_created = DrugBatch.objects.get_or_create(
            drug=instance.drug,
            batch_number=instance.batch_number,
            defaults={
                'quantity': 0, # با 0 شروع می‌کنیم و سپس اضافه می‌کنیم
                'expiry_date': instance.expiry_date,
                'manufacturing_date': manufacturing_date_for_batch,
                'purchase_price': instance.unit_price,
                'supplier': instance.invoice.supplier,
                # 'purchase_invoice': instance.invoice, # اگر فیلد purchase_invoice را به DrugBatch اضافه کردید
            }
        )
        # موجودی را به هر حال اضافه می‌کنیم (چه بچ جدید باشد چه موجود)
        drug_batch.add_stock(instance.quantity)
    else:
        # آیتم موجود در حال ویرایش است
        # باید موجودی قدیمی را کم و موجودی جدید را اضافه کنیم (اگر batch_number تغییر نکرده)
        # یا اگر batch_number تغییر کرده، از بچ قبلی کم و به بچ جدید اضافه کنیم.
        
        # مقدار اصلی قبل از تغییرات (قبل از save)
        try:
            original_item = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            print(f"Warning: Original PurchaseInvoiceItem with PK {instance.pk} not found during update signal.")
            return # اگر شیء اصلی به دلایلی پیدا نشد، کاری نکنید
        
        original_quantity = original_item.quantity
        original_batch_number = original_item.batch_number
        original_drug = original_item.drug # اگر دارو هم تغییر کند (بسیار نادر)

        # اگر batch_number یا drug تغییر کرده است:
        if original_batch_number != instance.batch_number or original_drug != instance.drug:
            # از بچ قدیمی کم کن
            if original_quantity > 0:
                try:
                    old_batch = DrugBatch.objects.get(
                        drug=original_drug, 
                        batch_number=original_batch_number
                    )
                    old_batch.remove_stock(original_quantity)
                except DrugBatch.DoesNotExist:
                    print(f"Warning: Old batch {original_batch_number} for {original_drug} not found when changing batch/drug.")
                except ValueError as e:
                    print(f"Error removing stock from old batch during batch/drug change: {e}")
            
            # بچ جدید را ایجاد یا به آن اضافه کن
            if instance.quantity > 0:
                drug_batch, batch_created = DrugBatch.objects.get_or_create(
                    drug=instance.drug,
                    batch_number=instance.batch_number,
                    defaults={
                        'quantity': 0,
                        'expiry_date': instance.expiry_date,
                        'manufacturing_date': manufacturing_date_for_batch,
                        'purchase_price': instance.unit_price,
                        'supplier': instance.invoice.supplier,
                        # 'purchase_invoice': instance.invoice, # اگر فیلد purchase_invoice را به DrugBatch اضافه کردید
                    }
                )
                drug_batch.add_stock(instance.quantity)
        else: # اگر batch_number و drug تغییری نکرده‌اند، فقط quantity را تنظیم کن
            quantity_difference = instance.quantity - original_quantity
            if quantity_difference != 0:
                try:
                    drug_batch = DrugBatch.objects.get(
                        drug=instance.drug,
                        batch_number=instance.batch_number
                    )
                    if quantity_difference > 0:
                        drug_batch.add_stock(quantity_difference)
                    else:
                        drug_batch.remove_stock(abs(quantity_difference))
                except DrugBatch.DoesNotExist:
                    print(f"Warning: DrugBatch {instance.batch_number} for {instance.drug} not found during quantity update.")
                except ValueError as e:
                    print(f"Error updating stock for batch {instance.batch_number}: {e}")
    
    # ⭐ همیشه مبلغ کل فاکتور اصلی را بروزرسانی کنید ⭐
    # این کار در هر save آیتم فاکتور انجام می‌شود.
    instance.invoice.update_total_amount()


@receiver(post_delete, sender=PurchaseInvoiceItem)
def handle_purchase_item_delete(sender, instance, **kwargs):
    # وقتی یک PurchaseInvoiceItem حذف می‌شود، موجودی آن باید از DrugBatch کم شود.
    if instance.quantity > 0:
        try:
            target_batch = DrugBatch.objects.get(
                drug=instance.drug, 
                batch_number=instance.batch_number
            )
            target_batch.remove_stock(instance.quantity)
        except DrugBatch.DoesNotExist:
            print(f"Warning: Batch {instance.batch_number} for {instance.drug.name} not found on delete. Could not remove stock.")
        except ValueError as e:
            print(f"Error removing stock during delete of {instance.batch_number} for {instance.drug.name}: {e}")
    
    # ⭐ مبلغ کل فاکتور اصلی را پس از حذف آیتم بروزرسانی کنید ⭐
    # بررسی کنید که آیا فاکتور هنوز وجود دارد یا خیر (ممکن است آبشاری حذف شده باشد)
    if PurchaseInvoice.objects.filter(pk=instance.invoice.pk).exists():
        instance.invoice.update_total_amount()
        
        
# 6. مدل درخواست دارو (DrugRequest)
REQUEST_STATUS_CHOICES = [
    ('pending', 'در انتظار بررسی'),
    ('approved', 'تایید شده'),
    ('rejected', 'رد شده'),
    ('completed', 'تکمیل شده'),
    ('canceled', 'لغو شده'),
]

class DrugRequest(models.Model):
    request_code = models.CharField(max_length=20, unique=True, editable=True)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[('pending', 'در انتظار'), ('approved', 'تایید شده')])
    assigned_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approver')

    def save(self, *args, **kwargs):
        if not self.request_code:
            self.request_code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def generate_unique_code(self):
        # الگوریتم تولید کد یکتا (مثلاً شامل تاریخ و عدد تصادفی)
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        rand = get_random_string(4, allowed_chars='0123456789')
        return f"DR-{today}-{rand}"

    def __str__(self):
        return self.request_code
# 7. مدل آیتم‌های درخواست دارو (DrugRequestItem)
class DrugRequestItem(models.Model):
    drug_request = models.ForeignKey(DrugRequest, on_delete=models.CASCADE, related_name='items', verbose_name="درخواست دارو")
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, verbose_name="دارو")
    requested_quantity = models.IntegerField(verbose_name="تعداد درخواستی")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات آیتم")
    
    approved_quantity = models.IntegerField(
        verbose_name="تعداد تایید شده",
        null=True,  # می‌تواند خالی باشد تا زمانی که تایید شود
        blank=True, # می‌تواند در فرم خالی ارسال شود
        default=0   # مقدار پیش‌فرض را 0 قرار می‌دهیم
    )
    class Meta:
        verbose_name = "آیتم درخواست دارو"
        verbose_name_plural = "آیتم‌های درخواست دارو"
        unique_together = ('drug_request', 'drug')

    def __str__(self):
        return f"{self.requested_quantity} از {self.drug.name} در درخواست {self.drug_request.id}"

# ✅ تعریف صحیح و کامل مدل DrugRequestWorkflowLog ✅
class DrugRequestWorkflowLog(models.Model):
    drug_request = models.ForeignKey(
        'DrugRequest',
        on_delete=models.CASCADE,
        related_name='workflow_logs',
        verbose_name="درخواست دارو"
    )
    # کاربر مسئول تغییر وضعیت یا انجام فعالیت
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="کاربر"
    )
    # وضعیت قبلی (مثلاً 'pending')
    old_status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS_CHOICES, # استفاده از CHOICES تعریف شده در DrugRequest
        blank=True,
        null=True,
        verbose_name="وضعیت قبلی"
    )
    # وضعیت جدید (مثلاً 'approved', 'rejected', 'completed')
    new_status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS_CHOICES,
        verbose_name="وضعیت جدید"
    )
    # نوع اقدام (مثلاً 'تایید پزشک', 'تایید سوپروایزر', 'رد', 'تکمیل موجودی', 'لغو')
    action = models.CharField(
        max_length=100,
        verbose_name="اقدام انجام شده"
    )
    # توضیحات بیشتر در مورد اقدام
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="توضیحات"
    )
    # زمان ثبت لاگ
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ثبت"
    )

    class Meta:
        verbose_name = "لاگ گردش کار درخواست دارو"
        verbose_name_plural = "لاگ‌های گردش کار درخواست دارو"
        ordering = ['-timestamp']

    def __str__(self):
        return f"لاگ برای درخواست {self.drug_request.id} - {self.action} در {self.timestamp.strftime('%Y/%m/%d %H:%M')}"