# از یک ایمیج پایه پایتون 3.11 (نسخه سبک) استفاده کن
FROM python:3.11-slim-buster

# دایرکتوری کاری را در کانتینر تنظیم کن
WORKDIR /app

# فایل requirements.txt را کپی کرده و وابستگی‌ها را نصب کن
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# بقیه کد برنامه را کپی کن
COPY . /app/

# متغیرهای محیطی برای جنگو (اختیاری اما توصیه شده)
ENV PYTHONUNBUFFERED 1
# نام پروژه جنگو خودت را به جای your_project_name قرار بده (مثلا final.settings)
ENV DJANGO_SETTINGS_MODULE final.settings

# پورتی که برنامه جنگو شما روی آن اجرا می‌شود را مشخص کن
EXPOSE 8000

# دستوری که برای اجرای برنامه جنگو شما استفاده می‌شود (از Gunicorn استفاده می‌کنیم)
# مطمئن شو که gunicorn در requirements.txt شما هست.
# نام پروژه جنگو خودت را به جای your_project_name قرار بده (مثلا final.wsgi)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "final.wsgi:application"]
