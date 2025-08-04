# از پایتون 3.10 استفاده می‌کنیم چون jalali-date با بالاتر کار نمی‌کنه
FROM python:3.10-slim

# ست کردن دایرکتوری کاری
WORKDIR /app

# کپی فایل‌های پروژه به داخل کانتینر
COPY . .

# نصب پکیج‌ها
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# پورت پیش‌فرض
EXPOSE 8000

# اجرای پروژه (در صورت نیاز تغییر بده)
CMD ["gunicorn", "yourproject.wsgi:application", "--bind", "0.0.0.0:8000"]
