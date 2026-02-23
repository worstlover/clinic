from rest_framework import serializers
from drugs.models import Supplier , Drug, DrugBarcode
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
class SupplierSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField() # Optional, since ModelSerializer includes pk by default, but useful for clarity
    text = serializers.CharField(source='name') # Map 'name' to 'text' for Select2

    class Meta:
        model = Supplier
        fields = ('id', 'text')

# drugs/serializers.py

# اول این رو تعریف کن
class DrugBarcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrugBarcode
        fields = ('id', 'gtin')

# حالا ازش اینجا استفاده کن


class DrugSerializer(serializers.ModelSerializer):
    total_stock = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    near_expiry = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField() # ✅ این اضافه شد
    text = serializers.SerializerMethodField()

    class Meta:
        model = Drug
        fields = ['id', 'name', 'text', 'form', 'total_stock', 'is_expired', 'near_expiry', 'is_low_stock']

    def get_text(self, obj):
        return f"{obj.name} ({obj.form})"

    def get_total_stock(self, obj):
        # محاسبه پایتونی روی دیتای لود شده
        return sum(batch.quantity for batch in obj.batches.all())

    def get_is_expired(self, obj):
        today = timezone.now().date()
        for batch in obj.batches.all():
            # اگر حتی یک بچ تاریخ گذشته و دارای موجودی باشد، هشدار می‌دهد
            if batch.quantity > 0 and batch.expiry_date and batch.expiry_date < today:
                return True
        return False

    def get_near_expiry(self, obj):
        today = timezone.now().date()
        future_limit = today + timedelta(days=90)
        for batch in obj.batches.all():
            if batch.quantity > 0 and batch.expiry_date:
                if today <= batch.expiry_date <= future_limit:
                    return True
        return False

    def get_is_low_stock(self, obj):
        # ✅ منطق کمبود موجودی: مثلا اگر زیر ۱۰ تا بود (می‌تونی عدد رو عوض کنی)
        total = self.get_total_stock(obj)
        return total < 10 and total > 0