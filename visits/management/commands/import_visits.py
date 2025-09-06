# visits/management/commands/import_visits.py

import pandas as pd
import re
from openpyxl import Workbook
from datetime import datetime, time
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.contrib.auth import get_user_model

# فرض بر این است که این مدل‌ها موجود هستند
from core.models import Patient
from visits.models import Visit, ReasonForVisit, TreatmentResult, INCIDENT_TYPE_CHOICES

User = get_user_model()

# تابع پاک‌سازی شماره موبایل
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

# تابع پاک‌سازی نام کامل
def clean_full_name(full_name):
    if pd.isna(full_name) or not isinstance(full_name, str):
        return None, None
    parts = full_name.strip().split()
    first_name = parts[0]
    last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
    return first_name, last_name

# تابع تبدیل ارقام فارسی به انگلیسی
def convert_persian_to_latin_digits(text):
    if not isinstance(text, str):
        return text
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    latin_digits = '0123456789'
    translator = str.maketrans(persian_digits, latin_digits)
    return text.translate(translator)

class Command(BaseCommand):
    help = 'Imports visit data from an Excel file, with an option to delete previous visits.'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='The path to the Excel file to import')
        parser.add_argument('--log-file', type=str, default='skipped_visits_log.xlsx', help='The path to the log file for skipped records.')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        log_file = options['log_file']

        self.stdout.write(self.style.WARNING("--- WARNING: This command can delete all existing visits. ---"))
        confirm = input("Do you want to delete all existing visits before importing? (yes/no): ").lower()
        if confirm in ['yes', 'y', 'بله', 'آره']:
            deleted_count, _ = Visit.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} old visits."))
        else:
            self.stdout.write(self.style.NOTICE("Keeping existing visits. New visits will be added."))

        self.stdout.write(f"\nStarting visit import from {excel_file}...")

        try:
            df = pd.read_excel(excel_file)
        except FileNotFoundError:
            raise CommandError(f'File "{excel_file}" does not exist.')
            
        self.stdout.write("\n--- Debugging Columns ---")
        
        required_cols = ['شماره موبایل', 'تاریخ ویزیت', 'ساعت ویزیت', 'علت مراجعه', 'نوع حادثه', 'نتیجه درمان', 'توضیحات', 'نام کامل']
        self.stdout.write(f"Required columns: {required_cols}")

        found_cols = list(df.columns)
        self.stdout.write(f"Found columns:    {found_cols}")

        missing_cols = [col for col in required_cols if col not in found_cols]
        if missing_cols:
            self.stdout.write(self.style.ERROR(f"--- ERROR: Missing columns: {missing_cols}"))
            self.stdout.write(self.style.WARNING("Please check for typos or extra spaces in your Excel column headers."))
            raise CommandError("Column names in Excel file do not match the required names.")
        else:
            self.stdout.write(self.style.SUCCESS("--- Column check passed successfully. ---"))
        
        self.stdout.write("---------------------------\n")

        try:
            admin_user = User.objects.get(username='admin')
            self.stdout.write(self.style.SUCCESS("Found 'admin' user. All visits will be assigned to this user."))
        except User.DoesNotExist:
            raise CommandError("Admin user with username 'admin' does not exist. Please create it first.")

        log_wb = Workbook()
        log_ws = log_wb.active
        log_ws.title = "Skipped Visits"
        log_ws.append(list(df.columns) + ['Reason'])

        imported_count = 0
        skipped_count = 0

        incident_type_map = {name: key for key, name in INCIDENT_TYPE_CHOICES}

        for index, row in df.iterrows():
            phone_number = clean_phone_number(row['شماره موبایل'])
            
            patient_found = None
            if phone_number:
                try:
                    patient_found = Patient.objects.get(phone_number=phone_number)
                except Patient.DoesNotExist:
                    pass

            if not patient_found:
                first_name_excel, last_name_excel = clean_full_name(row['نام کامل'])
                if first_name_excel:
                    try:
                        patient_found = Patient.objects.get(Q(first_name=first_name_excel) & Q(last_name=last_name_excel))
                    except Patient.DoesNotExist:
                        pass
            
            if not patient_found:
                skipped_count += 1
                log_ws.append(list(row) + ['Patient not found by phone number or name.'])
                continue

            reason, _ = ReasonForVisit.objects.get_or_create(name=row['علت مراجعه'])
            result, _ = TreatmentResult.objects.get_or_create(name=row['نتیجه درمان'])

            try:
                if pd.isna(row['تاریخ ویزیت']) or pd.isna(row['ساعت ویزیت']):
                    skipped_count += 1
                    log_ws.append(list(row) + ['Date or time is missing.'])
                    continue
                
                if isinstance(row['تاریخ ویزیت'], datetime):
                    date_str = row['تاریخ ویزیت'].strftime('%d/%m/%Y')
                else:
                    date_str = convert_persian_to_latin_digits(str(row['تاریخ ویزیت']).split()[0])
                
                if isinstance(row['ساعت ویزیت'], datetime) or isinstance(row['ساعت ویزیت'], time):
                    time_str = row['ساعت ویزیت'].strftime('%H:%M:%S')
                else:
                    time_str = convert_persian_to_latin_digits(str(row['ساعت ویزیت']).split()[0])
                    if ':' not in time_str:
                        time_str = f"{time_str[:2]}:{time_str[2:]:02}:00"
                
                date_time_str = f"{date_str} {time_str}"
                
                visit_datetime = datetime.strptime(date_time_str, '%d/%m/%Y %H:%M:%S')
                
            except (ValueError, TypeError) as e:
                skipped_count += 1
                log_ws.append(list(row) + [f"Invalid date or time format: {e}"])
                continue
            
            incident_type_key = incident_type_map.get(row['نوع حادثه'], 'none')
            
            visit = Visit.objects.create(
                patient=patient_found,
                doctor=admin_user, 
                visit_date=visit_datetime,
                reason_for_visit=reason,
                treatment_result=result,
                incident_type=incident_type_key,
                notes=row['توضیحات'] if not pd.isna(row['توضیحات']) else '',
                status='completed' # مقداردهی صحیح فیلد status
            )

            imported_count += 1
            self.stdout.write(self.style.SUCCESS(f"Successfully imported visit for patient '{patient_found.full_name}'"))

        log_wb.save(log_file)
        self.stdout.write(self.style.SUCCESS(f'\nImport complete. {imported_count} visits imported, {skipped_count} skipped.'))
        self.stdout.write(self.style.SUCCESS(f'Skipped records logged to {log_file}'))