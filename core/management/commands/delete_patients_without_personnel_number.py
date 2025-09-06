# core/management/commands/delete_patients_without_personnel_number.py

from django.core.management.base import BaseCommand
from core.models import Patient # مطمئن شوید نام مدل Patient درست است

class Command(BaseCommand):
    help = 'Deletes patients from "تالی سازان آتیه بهاباد" who do not have a personnel number.'

    def handle(self, *args, **options):
        self.stdout.write("Starting deletion process...")

        # پیدا کردن بیماران با هر دو شرط
        patients_to_delete = Patient.objects.filter(
            company__name="تالی سازان آتیه بهاباد",
            personnel_number__isnull=True  # یا personnel_number="" اگر فیلد رشته است
        )
        
        count_to_delete = patients_to_delete.count()
        
        if count_to_delete == 0:
            self.stdout.write(self.style.WARNING("No patients found to delete based on the criteria."))
            return

        self.stdout.write(f"Found {count_to_delete} patients to delete...")

        # حذف بیماران
        deleted_count, _ = patients_to_delete.delete()
        
        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} patients."))
        else:
            self.stdout.write(self.style.ERROR("Deletion failed."))