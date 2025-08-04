# از یک ایمیج پایه پایتون 3.11 سبک استفاده کن
# این ایمیج برای jalali-date مناسب است
FROM python:3.11-slim-buster

# دایرکتوری کاری را در کانتینر تنظیم کن
WORKDIR /app

# فایل requirements.txt را کپی کرده و وابستگی‌ها را نصب کن
# این کار به کش داکر کمک می‌کند تا بیلد سریع‌تر شود
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# بقیه کدهای پروژه را کپی کن
COPY . .

# متغیرهای محیطی برای جنگو
# مطمئن شو که 'final' نام پوشه اصلی پروژه شماست که settings.py داخل آن قرار دارد
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE final.settings

# پورتی که برنامه روی آن اجرا می‌شود را مشخص کن
EXPOSE 8000

# دستوری که برای اجرای پروژه استفاده می‌شود
# مطمئن شو که gunicorn در requirements.txt شما هست و 'final' نام پروژه اصلی شماست
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "final.wsgi:application"]


