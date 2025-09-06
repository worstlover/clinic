# core/management/commands/clean_phones.py

from django.core.management.base import BaseCommand
from core.models import Patient  # نام مدل خود را به جای 'Patient' بنویسید

class Command(BaseCommand):
    help = 'Cleans up phone number formatting by removing .0 and ensures it starts with 09.'

    def handle(self, *args, **options):
        self.stdout.write("Starting phone number cleanup...")

        records = Patient.objects.all() # نام مدل خود را به جای 'Patient' بنویسید
        updated_count = 0

        for record in records:
            current_number = record.phone_number  # نام فیلد خود را به جای 'phone_number' بنویسید
            new_number = None

            if isinstance(current_number, (float, int)):
                # اگر شماره به صورت عدد (مثلا 9123456789.0) ذخیره شده، تبدیل به رشته کن
                new_number = str(int(current_number))
            elif isinstance(current_number, str):
                # اگر شماره به صورت رشته‌ای است، .0 را از آخر آن حذف کن
                if current_number.endswith('.0'):
                    new_number = current_number[:-2]
                else:
                    new_number = current_number

            # حالا مطمئن شو که شماره با '09' شروع می‌شود
            if new_number and new_number.startswith('9'):
                new_number = '0' + new_number
            
            # در نهایت، اگر تغییری رخ داده بود، آن را ذخیره کن
            if new_number and new_number != str(current_number):
                record.phone_number = new_number
                record.save()
                updated_count += 1
                self.stdout.write(f"Updated record ID {record.pk}: {current_number} -> {new_number}")

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} phone numbers.'))