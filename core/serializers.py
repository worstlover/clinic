# core/serializers.py (نسخه نهایی و صحیح)

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Patient # ایمپورت صحیح از اپ core
from drugs.models import Drug
from clinic_messages.models import Notification

# --- سریالایزر جدید برای ارتباط با React ---
from rest_framework import serializers
from .models import Patient, Company # مطمئن شوید Company هم ایمپورت شده است
from datetime import date # برای محاسبه سن در صورت نیاز
from django.contrib.auth import get_user_model # 👈 این خط رو اضافه کن

from rest_framework import serializers
from .models import Patient# مدل Visit را هم import کنید
from visits.models import Visit , ReasonForVisit
# visits/serializers.py
from rest_framework import serializers

from jalali_date import datetime2jalali

class PatientSearchSerializer(serializers.ModelSerializer):
    """
    این سریالایزر به صورت اختصاصی برای API جستجوی بیمار (Select2) طراحی شده.
    خروجی آن شامل فیلدهای id و text است که برای Select2 الزامی است.
    """
    # فیلد text از پراپرتی full_name_and_identifiers در مدل Patient خوانده می‌شود
    text = serializers.CharField(source='full_name_and_identifiers', read_only=True)

    class Meta:
        model = Patient
        # فقط فیلدهای مورد نیاز برای نمایش در لیست جستجو را برمی‌گردانیم
        fields = ['id', 'text', 'national_code', 'phone_number']


# --- سریالایزر کامل بیمار (برای نمایش جزئیات پس از انتخاب) ---
class PatientSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Patient جهت استفاده در API
    """
    full_name_and_identifiers = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    visit_count = serializers.SerializerMethodField()
    last_visit_date = serializers.SerializerMethodField()
    last_visit_reason = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = (
            'id',
            'first_name',
            'last_name',
            'national_code',
            'personnel_number',
            'medical_history',
            'allergies',
            'phone_number', # phone_number را برای نمایش در جزئیات اضافه می‌کنیم
            'full_name_and_identifiers',
            'age',
            'visit_count',
            'last_visit_date',
            'last_visit_reason'
        )

    def get_full_name_and_identifiers(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_age(self, obj):
        if obj.date_of_birth: # از date_of_birth به جای birth_date استفاده شد
            today = date.today()
            age = today.year - obj.date_of_birth.year - ((today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day))
            return age
        return '---'

    def get_visit_count(self, obj):
        return Visit.objects.filter(patient=obj).count()

    def get_last_visit_date(self, obj):
        last_visit = Visit.objects.filter(patient=obj).order_by('-visit_date').first()
        if last_visit and last_visit.visit_date:
            return datetime2jalali(last_visit.visit_date).strftime('%Y/%m/%d')
        return '---'

    def get_last_visit_reason(self, obj):
        last_visit = Visit.objects.filter(patient=obj).order_by('-visit_date').first()
        if last_visit and last_visit.reason_for_visit:
            return last_visit.reason_for_visit.name
        return '---'


class PatientAuthSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True, required=False)
    age = serializers.IntegerField(read_only=True)

    # 👈👈👈 این خط رو اضافه کنید تا فرمت YYYY-MM-DD به درستی هندل شود
    date_of_birth = serializers.DateField(format="%Y-%m-%d", required=False, allow_null=True) 

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'national_code', 'personnel_number',
            'phone_number', 'is_foreign_national', 'passport_number',
            'date_of_birth', 
            'gender', 'blood_type', 'insurance_type', 'company',
            'company_name', 'address', 'allergies', 'medical_history', 'occupation',
            'last_periodic_examination_date', 'is_monitored', 'profile_picture', 'age',
            'is_approved' # 👈 اضافه کردن فیلد is_approved
        ]
        read_only_fields = ['id', 'company_name', 'age', 'registered_at', 'registered_by', 'is_approved'] # 👈 is_approved هم read_only است برای ورودی

        extra_kwargs = {
            'national_code': {'write_only': True, 'required': True}, 
            'personnel_number': {'required': True, 'allow_null': False, 'allow_blank': False}, 
            'company': {'required': False, 'allow_null': True}, 
            'passport_number': {'required': False, 'allow_null': True, 'allow_blank': True},
            'phone_number': {'required': False, 'allow_null': True, 'allow_blank': True},
            # 'date_of_birth': {'required': False, 'allow_null': True}, # 👈 این خط رو حذف کنید یا کامنت کنید چون در بالا صریحاً تعریفش کردیم
            'blood_type': {'required': False, 'allow_null': True, 'allow_blank': True},
            'insurance_type': {'required': False, 'allow_null': True, 'allow_blank': True},
            'address': {'required': False, 'allow_null': True, 'allow_blank': True},
            'allergies': {'required': False, 'allow_blank': True},
            'medical_history': {'required': False, 'allow_blank': True},
            'occupation': {'required': False, 'allow_null': True, 'allow_blank': True},
            'last_periodic_examination_date': {'required': False, 'allow_null': True},
        }

    # اعتبارسنجی یکتایی و شرطی
    def validate(self, data):
        is_foreign = data.get('is_foreign_national', False)
        national_code = data.get('national_code')
        passport_number = data.get('passport_number')
        personnel_number = data.get('personnel_number')

        # 1. اعتبارسنجی حضور کد ملی/پاسپورت
        if not is_foreign and not national_code:
            raise serializers.ValidationError({"national_code": "کد ملی برای اتباع ایرانی الزامی است."})
        
        if is_foreign and not passport_number:
            raise serializers.ValidationError({"passport_number": "شماره پاسپورت برای اتباع خارجی الزامی است."})
        
        # 2. اعتبارسنجی یکتایی و وضعیت تایید
        instance_id = self.instance.id if self.instance else None

        # کوئری برای یافتن بیماران موجود با کد ملی، پاسپورت یا کد پرسنلی
        existing_patient_query = Patient.objects.none()
        if not is_foreign and national_code:
            existing_patient_query = existing_patient_query | Patient.objects.filter(national_code=national_code)
        
        if is_foreign and passport_number:
            existing_patient_query = existing_patient_query | Patient.objects.filter(passport_number=passport_number)
        
        if personnel_number:
            existing_patient_query = existing_patient_query | Patient.objects.filter(personnel_number=personnel_number)
        
        # فیلتر کردن موارد فعلی در صورت update
        if instance_id:
            existing_patient_query = existing_patient_query.exclude(id=instance_id)

        # 👈👈👈 منطق جدید: بررسی بیماران موجود که هنوز تایید نشده‌اند یا تایید شده‌اند
        if existing_patient_query.exists():
            # اگر بیمار موجود است و هنوز تایید نشده
            if existing_patient_query.filter(is_approved=False).exists(): # 👈 اینجا exclude(id=instance_id) رو حذف کردم چون قبلا انجام شده
                raise serializers.ValidationError({
                    "detail": "ثبت نام شما قبلاً انجام شده و در انتظار تایید مدیر سیستم است."
                })
            # اگر بیمار موجود است و تایید شده
            elif existing_patient_query.filter(is_approved=True).exists(): # 👈 اینجا exclude(id=instance_id) رو حذف کردم
                 raise serializers.ValidationError({
                    "detail": "شما قبلاً ثبت نام کرده‌اید. لطفاً وارد شوید."
                })
        
        return data

    # متد create برای ذخیره Patient
    def create(self, validated_data):
        # 👈👈👈 تنظیم is_approved به False به صورت پیش‌فرض در زمان ایجاد
        validated_data['is_approved'] = False 

        company_instance = validated_data.pop('company', None) # اگر company به صورت PrimaryKeyRelatedField تعریف شده باشد، این خودش یک instance است
        
        registered_by = self.context.get('request').user if 'request' in self.context else None
        if registered_by and not registered_by.is_authenticated:
            registered_by = None

        patient = Patient.objects.create(company=company_instance, registered_by=registered_by, **validated_data)
        return patient

    # متد update برای به‌روزرسانی Patient (اگر نیاز دارید)
    def update(self, instance, validated_data):
        company_instance = validated_data.pop('company', None)
        if company_instance is not None:
            instance.company = company_instance
        elif company_instance is None:
              instance.company = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance




class DrugSerializer(serializers.ModelSerializer):
    # این 'text' ضروری است تا Select2 آن را نمایش دهد
    text = serializers.SerializerMethodField()

    class Meta:
        model = Drug
        # مطمئن شوید 'id' و 'name' و 'generic_name' و 'drug_code' در اینجا باشند
        fields = ['id', 'name', 'generic_name', 'drug_code', 'text']

    def get_text(self, obj):
        # این تابع فرمت نمایشی دارو را در Select2 مشخص می‌کند
        if obj.generic_name:
            return f"{obj.name} ({obj.generic_name}) - کد: {obj.drug_code or 'نامشخص'}"
        return f"{obj.name} - کد: {obj.drug_code or 'نامشخص'}"
class UserSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل کاربر.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

class NotificationSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل نوتیفیکیشن.
    """
    class Meta:
        model = Notification
        fields = '__all__'