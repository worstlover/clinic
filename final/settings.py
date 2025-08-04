# D:\final\final\settings.py
import os
from pathlib import Path

#locale.setlocale(locale.LC_ALL, "fa_IR.UTF-8")
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# WARNING: keep the secret key used in production secret!
# این کلید در محیط پروداکشن باید تغییر کند و بهتر است از متغیرهای محیطی خوانده شود.
SECRET_KEY = 'django-insecure-#3p4$3qq@*o=+_*(!57s-jcbz4^oh4f=uuw5ell)3)7%-=m%pr'

# SECURITY WARNING: don't run in debug turned on in production!
# برای محیط توسعه True باشد. برای محیط پروداکشن حتماً False شود.
DEBUG = False

# در محیط پروداکشن باید دامنه‌ها یا IP سرور شما باشد.
# مثال: ['127.0.0.1', 'localhost', '.yourdomain.com', 'your_server_ip']
ALLOWED_HOSTS = ['https://clinic-1-luqt.onrender.com/','www.onrender.com']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages', # این مربوط به فریم‌ورک پیام‌رسانی داخلی جنگو است
    'django.contrib.staticfiles',
    'widget_tweaks',
    'ckeditor',
    'ckeditor_uploader',
    # اپلیکیشن‌های سفارشی شما
    'core',
    'clinic_messages',   # <<< فقط یک بار باید اینجا باشد
    
    # اگر از Django REST Framework و Django Filters استفاده می‌کنید
    'rest_framework',
    'django_filters',
    'crispy_forms',           # این خط را اضافه کنید
    'crispy_bootstrap5',
    'visits',
    'drugs',
    'django.contrib.humanize',
    'mammoth',
    'corsheaders',
    'fcm_django',
    'django_select2',
    'lab_results',
    'reports'
    
]
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5" # برای مشخص کردن پکیج قالب‌های مجاز
CRISPY_TEMPLATE_PACK = "bootstrap5"   
JALALI_SETTINGS = {
    # JavaScript static files for the admin Jalali date widget
    "ADMIN_JS_STATIC_FILES": [
        "admin/jquery.ui.datepicker.jalali/scripts/jquery-1.10.2.min.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.core.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc.js",
        "admin/jquery.ui.datepicker.jalali/scripts/calendar.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc-fa.js",
        "admin/main.js",
    ],
    # CSS static files for the admin Jalali date widget
    "ADMIN_CSS_STATIC_FILES": {
        "all": [
            "admin/jquery.ui.datepicker.jalali/themes/base/jquery-ui.min.css",
            "admin/css/main.css",
        ]
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    # این خط رو حتما بالای CommonMiddleware قرار بدید
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # آدرس فرانت‌اند React شما
    # "http://127.0.0.1:3000", # اگر فرانت‌اند با 127.0.0.1 ران میشه، این رو هم اضافه کنید
    # "http://your-frontend-domain.com", # اگر اپ شما در آینده روی دامنه‌ای مستقر شد
]
CORS_ALLOW_ALL_ORIGINS = True 
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    # هر هدر کاستوم دیگری که در فرانت‌اند می‌فرستید
]
ROOT_URLCONF = 'final.urls' # مطمئن شوید نام پروژه شما 'final' است.

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # اطمینان حاصل کنید که این مسیر به پوشه templates اصلی پروژه شما اشاره می‌کند
        'APP_DIRS': True, # این به جنگو می‌گوید که به دنبال پوشه 'templates' در هر اپلیکیشن نصب شده بگردد
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.unread_messages_count', # اضافه شده برای شمارنده پیام‌های خوانده نشده
            ],
        },
    },
]

WSGI_APPLICATION = 'final.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

# برای فارسی‌سازی رابط کاربری و تاریخ‌ها (اگر لازم باشد)
LANGUAGE_CODE = 'fa-ir'


# برای منطقه زمانی ایران
TIME_ZONE = 'Asia/Tehran'

USE_I18N = True # فعال کردن بین‌المللی سازی

USE_TZ = True # فعال کردن زمان‌های حساس به منطقه زمانی


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = f'{BASE_DIR}/staticfiles'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'), # BASE_DIR به روت پروژه شما اشاره می کند
]
# STATIC_ROOT is used in production to collect all static files into one place.
# STATIC_ROOT = BASE_DIR / 'staticfiles'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Media files (user-uploaded files like patient photos, document uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# This is the local path where uploaded files will be stored.
# Path using pathlib.Path
MEDIA_ROOT = BASE_DIR / 'media'
CKEDITOR_UPLOAD_PATH = 'uploads/ckeditor/' 
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
        'extraPlugins': 'codesnippet', # اگر پلاگین‌های خاصی نیاز دارید
        # 'removePlugins': 'exportpdf', # اگر خطای exportpdf را نمی‌خواهید، این را اضافه کنید
    },
}
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = 'login' # برای تغییر مسیر ورود
