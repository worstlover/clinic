# core/management/commands/clean_phones.py

from django.core.management.base import BaseCommand
from core.models import Patient  # Replace 'Patient' if your model has a different name

class Command(BaseCommand):
    help = 'Cleans up phone number formatting by removing .0 at the end.'

    def handle(self, *args, **options):
        self.stdout.write("Starting phone number cleanup...")

        records = Patient.objects.all()  # Replace 'Patient' if your model has a different name
        updated_count = 0

        for record in records:
            current_number = record.phone_number
            if current_number and isinstance(current_number, str) and current_number.endswith('.0'):
                new_number = current_number[:-2]
                record.phone_number = new_number
                record.save()
                updated_count += 1
                self.stdout.write(f"Updated record ID {record.pk}: {current_number} -> {new_number}")

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} phone numbers.'))