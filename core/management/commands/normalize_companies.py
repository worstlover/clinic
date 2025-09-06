# core/management/commands/normalize_companies.py

from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Patient, Company # مطمئن شوید نام مدل‌ها درست است

class Command(BaseCommand):
    help = 'Normalizes any company name containing "تالی" or "پامیدکو" to "تالی سازان آتیه بهاباد" and deletes old records.'

    def handle(self, *args, **options):
        self.stdout.write("Starting company normalization process...")

        # 1. پیدا کردن یا ایجاد شرکت مقصد
        target_company_name = "تالی سازان آتیه بهاباد"
        target_company, created = Company.objects.get_or_create(
            name=target_company_name
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created target company: '{target_company_name}'"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Found target company: '{target_company_name}'"))

        # 2. پیدا کردن بیماران مرتبط با شرکت‌های قدیمی با استفاده از icontains
        # icontains به معنای "شامل می‌شود" و به حروف کوچک و بزرگ حساس نیست.
        patients_to_update = Patient.objects.filter(
            Q(company__name__icontains="تالی") | Q(company__name__icontains="پامیدکو")
        ).exclude(company__name=target_company_name) # برای جلوگیری از تغییر شرکت مقصد

        count_patients_found = patients_to_update.count()
        if count_patients_found == 0:
            self.stdout.write(self.style.WARNING("No patients found for 'تالی' or 'پامیدکو'."))
            self.delete_old_companies()
            return

        self.stdout.write(f"Found {count_patients_found} patients to update...")
        
        # 3. به‌روزرسانی بیماران
        updated_count = 0
        for patient in patients_to_update:
            patient.company = target_company
            patient.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} patients."))

        # 4. حذف شرکت‌های قدیمی
        self.delete_old_companies()

        self.stdout.write(self.style.SUCCESS("\nCompany normalization process completed."))

    def delete_old_companies(self):
        # حذف شرکت‌هایی که در نام آن‌ها "تالی" یا "پامیدکو" وجود دارد
        # این بخش خطرناک است، مطمئن شوید که می‌خواهید همه آن‌ها حذف شوند.
        companies_to_delete = Company.objects.filter(
            Q(name__icontains="تالی") | Q(name__icontains="پامیدکو")
        ).exclude(name="تالی سازان آتیه بهاباد")
        
        deleted_count, _ = companies_to_delete.delete()
        
        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} old company records."))
        else:
            self.stdout.write(self.style.WARNING("No old companies ('تالی', 'پامیدکو') were found to delete."))