# messages/forms.py
from ckeditor.widgets import CKEditorWidget
from django import forms
from .models import Message, MessageAttachment, MessageRecipient # اطمینان حاصل کنید که MessageRecipient ایمپورت شده است
from django.contrib.auth.models import User
from visits.models import Visit
from drugs.models import DrugRequest
import jdatetime
import datetime
from django.forms import ModelForm, inlineformset_factory
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from django.contrib.auth import get_user_model
import django_filters
from django.db.models import Q 
from ckeditor.fields import RichTextField # برای مدل‌ها
from ckeditor_uploader.fields import RichTextUploadingFormField


class MessageForm(forms.ModelForm):
    body = RichTextUploadingFormField(label="متن پیام")
   

    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'select2'}),
        label="گیرندگان",
        required=True
    )

    class Meta:
        model = Message
        fields = ['recipients', 'subject', 'body', 'parent_message'] # فیلدهای related_visit و related_drug_request حذف شدند

    def __init__(self, *args, **kwargs):
        # استخراج آرگومان 'request' قبل از فراخوانی متد والد
        self.request = kwargs.pop('request', None) # این خط کلیدی است

        super().__init__(*args, **kwargs) # این خط در traceback به عنوان خط 42 نشان داده شده است

        # در اینجا می‌توانید از self.request برای فیلتر کردن querysetها استفاده کنید
        # به عنوان مثال، اگر می‌خواهید کاربر فعلی را از لیست گیرندگان حذف کنید:
        if self.request and self.request.user.is_authenticated:
            self.fields['recipients'].queryset = User.objects.exclude(id=self.request.user.id)
        else:
            self.fields['recipients'].queryset = User.objects.all()

        # تنظیمات CKEditor
        # اگر CKEditorWidget را به صورت پیش‌فرض در Meta تعریف نکرده‌اید:
        self.fields['body'].widget = CKEditorWidget()
        self.fields['body'].label = "متن پیام"
        self.fields['subject'].label = "موضوع"

        # اگر فیلد parent_message مخفی است:
        if 'parent_message' in self.fields:
            self.fields['parent_message'].widget = forms.HiddenInput()


class MessageAttachmentForm(forms.ModelForm):
    class Meta:
        model = MessageAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control-file'})
        }

MessageAttachmentFormSet = inlineformset_factory(
    Message,
    MessageAttachment,
    form=MessageAttachmentForm,
    fields=['file'],
    extra=1, # می‌توانید تعداد فیلدهای خالی اولیه را کنترل کنید
    can_delete=True
)

# فرم جدید برای MessageRecipient (برای مدیریت گیرندگان)
class MessageRecipientForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'select2'}),
        label="گیرنده",
        required=True
    )

    class Meta:
        model = MessageRecipient
        fields = ['recipient']

# فرم‌ست برای مدیریت گیرندگان
MessageRecipientFormSet = inlineformset_factory(
    Message,
    MessageRecipient,
    form=MessageRecipientForm,
    extra=1, # تعداد فرم‌های خالی اولیه
    can_delete=True,
    min_num=1, # حداقل یک گیرنده
    max_num=10, # حداکثر تعداد گیرنده
)


# فرم‌ست برای مدیریت پیوست‌ها (کد قبلی شما درست بود)

MessageAttachmentFormSet = inlineformset_factory(
    Message,
    MessageAttachment,
    form=MessageAttachmentForm,
    extra=1, # تعداد فرم‌های خالی اولیه
    can_delete=True,
    min_num=0, # حداقل تعداد فرم
    max_num=5, # حداکثر تعداد پیوست
)


# اصلاح MessageFilterForm برای فیلتر کردن پیام‌های ارسال شده
class MessageFilterForm(forms.Form):
    query = forms.CharField(
        label="جستجو در موضوع/متن",
        required=False,
    )
    recipient = forms.ModelChoiceField( # تغییر user به recipient برای وضوح بیشتر
        queryset=User.objects.all(),
        label="گیرنده",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    start_date_fa = forms.CharField(
        label="تاریخ شروع (شمسی)",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control persian-date-picker'})
    )
    end_date_fa = forms.CharField(
        label="تاریخ پایان (شمسی)",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control persian-date-picker'})
    )
    # is_read_status برای پیام‌های ارسال شده کمتر معنی دارد، مگر اینکه بخواهیم ببینیم آیا حداقل یکی از گیرندگان آن را خوانده است.
    # در این حالت نیاز به یک Q-object پیچیده‌تر داریم. فعلا حذف می کنیم.
    # is_read = forms.ChoiceField(
    #     choices=[('', 'همه'), ('read', 'خوانده شده'), ('unread', 'نخوانده')],
    #     label="وضعیت مطالعه (حداقل یک گیرنده)", # نام را تغییر دادم
    #     required=False,
    #     widget=forms.Select(attrs={'class': 'form-control'})
    # )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        # چیدمان 4 تایی فیلدها
        self.helper.layout = Layout(
            Row(
                Column('query', css_class='form-group col-md-3 mb-0'), # 3 + 3 + 3 + 3 = 12
                Column('recipient', css_class='form-group col-md-3 mb-0'),
                Column('start_date_fa', css_class='form-group col-md-3 mb-0'),
                Column('end_date_fa', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            # اگر فیلد is_read را برگردانید:
            # Row(
            #     Column(Field('is_read', css_class='form-control mb-0'), css_class='form-group col-md-4 mb-0'),
            #     css_class='form-row'
            # ),
            Submit('submit', 'جستجو', css_class='btn btn-primary mt-3')
        )
        
        self.fields['query'].widget.attrs.update({'placeholder': 'جستجو در موضوع/متن'})
        # فیلتر کردن گیرندگان برای نمایش در فیلد `recipient`
        if self.request:
            self.fields['recipient'].queryset = User.objects.filter(is_active=True).exclude(pk=self.request.user.pk)


    @property
    def qs(self):
        # این queryset باید پیام‌هایی باشد که کاربر فعلی فرستاده است
        qs = Message.objects.filter(sender=self.request.user).prefetch_related('recipients_data__recipient').order_by('-created_at')

        if self.is_valid():
            query = self.cleaned_data.get('query')
            recipient = self.cleaned_data.get('recipient')
            start_date_fa = self.cleaned_data.get('start_date_fa')
            end_date_fa = self.cleaned_data.get('end_date_fa')
            # is_read_status = self.cleaned_data.get('is_read') # اگر فعال شد

            if query:
                qs = qs.filter(Q(subject__icontains=query) | Q(body__icontains=query))
            
            if recipient:
                # فیلتر بر اساس گیرنده در MessageRecipient
                qs = qs.filter(recipients_data__recipient=recipient).distinct() # distinct برای جلوگیری از تکرار پیام ها
            
            if start_date_fa:
                jdate = jdatetime.date.fromisoformat(start_date_fa.replace('/', '-'))
                gdate = jdate.togregorian()
                qs = qs.filter(created_at__gte=gdate)
            
            if end_date_fa:
                jdate = jdatetime.date.fromisoformat(end_date_fa.replace('/', '-'))
                gdate = jdate.togregorian()
                qs = qs.filter(created_at__lte=gdate + datetime.timedelta(days=1))

            # if is_read_status:
            #     if is_read_status == 'read':
            #         # پیام‌هایی که حداقل یکی از گیرندگان آن را خوانده است
            #         qs = qs.filter(recipients_data__is_read=True).distinct()
            #     elif is_read_status == 'unread':
            #         # پیام‌هایی که حداقل برای یکی از گیرندگان خوانده نشده است (پیچیده‌تر)
            #         # یا تمام گیرندگان خوانده نشده اند (معمول تر)
            #         # این منطق نیاز به بررسی دقیق دارد، مثلا: پیام هایی که هیچ گیرنده ای آن را نخوانده است:
            #         # qs = qs.exclude(recipients_data__is_read=True)
            #         # یا پیام هایی که حداقل یک گیرنده نخوانده دارد:
            #         # qs = qs.filter(recipients_data__is_read=False).distinct()
            #         pass # فعلاً بدون پیاده‌سازی دقیق برای is_read_status
        return qs