# core/management/commands/import_patients.py

import pandas as pd
import re
from openpyxl import Workbook
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from core.models import Patient, Company # مطمئن شوید نام مدل‌های شما همین‌هاست

# تابع پاک‌سازی شماره تلفن
def clean_phone_number(phone_number):
    if pd.isna(phone_number):
        return None
    
    if isinstance(phone_number, (float, int)):
        phone_number = str(int(phone_number))
    
    cleaned_number = re.sub(r'\D', '', str(phone_number))

    if cleaned_number.startswith('98'):
        cleaned_number = cleaned_number[2:]

    if cleaned_number.startswith('9') and len(cleaned_number) == 10:
        cleaned_number = '0' + cleaned_number
        
    return cleaned_number

# تابع پاک‌سازی نام کامل برای جستجو
def clean_full_name(full_name):
    if pd.isna(full_name) or not isinstance(full_name, str):
        return None, None
    
    parts = full_name.strip().split()
    first_name = parts[0]
    last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
    
    return first_name, last_name

class Command(BaseCommand):
    help = 'Imports patients from an Excel file, handling name variations and logging skipped records.'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='The path to the Excel file to import')
        parser.add_argument('--log-file', type=str, default='skipped_patients_log.xlsx', help='The path to the log file for skipped records.')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        log_file = options['log_file']

        self.stdout.write(f"Starting patient import from {excel_file}...")

        try:
            df = pd.read_excel(excel_file)
        except FileNotFoundError:
            raise CommandError(f'File "{excel_file}" does not exist.')
        except Exception as e:
            raise CommandError(f'Error reading Excel file: {e}')
        
        required_columns = ['شماره موبایل', 'نام کامل', 'شرکت']
        if not all(col in df.columns for col in required_columns):
            raise CommandError('Excel file must contain the following columns: "شماره موبایل", "نام کامل", "شرکت"')
        
        # آماده‌سازی فایل لاگ
        log_wb = Workbook()
        log_ws = log_wb.active
        log_ws.title = "Skipped Patients"
        log_ws.append(list(df.columns) + ['Reason'])

        imported_count = 0
        updated_count = 0
        skipped_count = 0

        for index, row in df.iterrows():
            raw_phone_number = row['شماره موبایل']
            raw_full_name = row['نام کامل']
            company_name = row['شرکت']

            phone_number = clean_phone_number(raw_phone_number)
            
            patient_found = None
            
            # مرحله ۱: جستجو بر اساس شماره موبایل
            if phone_number:
                try:
                    patient_found = Patient.objects.get(phone_number=phone_number)
                except Patient.DoesNotExist:
                    pass

            # اگر با شماره موبایل پیدا نشد، با نام کامل جستجو کن
            if not patient_found:
                first_name_excel, last_name_excel = clean_full_name(raw_full_name)

                if first_name_excel:
                    try:
                        # جستجو با استفاده از Q-object برای تطابق نام و نام خانوادگی
                        patient_found = Patient.objects.get(
                            Q(first_name=first_name_excel) & Q(last_name=last_name_excel)
                        )
                    except Patient.DoesNotExist:
                        pass
            
            if patient_found:
                if phone_number and patient_found.phone_number != phone_number:
                    patient_found.phone_number = phone_number
                    patient_found.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"Updated patient {patient_found.full_name} with new phone number: {phone_number}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Skipping: Patient {patient_found.full_name} already exists with same phone or no new number."))
                skipped_count += 1
                continue
            
            if not patient_found:
                if not phone_number and not raw_full_name:
                    log_ws.append(list(row) + ['Missing phone number and full name'])
                    skipped_count += 1
                    continue
                
                company, created = Company.objects.get_or_create(name=company_name)
                
                Patient.objects.create(
                    phone_number=phone_number,
                    first_name=first_name_excel,
                    last_name=last_name_excel,
                    company=company
                )
                imported_count += 1
                self.stdout.write(self.style.SUCCESS(f"Successfully imported: {raw_full_name} ({phone_number})"))

        log_wb.save(log_file)
        self.stdout.write(self.style.SUCCESS(f'\nImport complete. {imported_count} imported, {updated_count} updated, {skipped_count} skipped.'))
        self.stdout.write(self.style.SUCCESS(f'Skipped records logged to {log_file}'))