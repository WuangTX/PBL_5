from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Manually modify the History table structure to add vehicle_id and plate_number fields'

    def handle(self, *args, **options):
        # Check if the vehicle_id column already exists
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM histories LIKE 'vehicle_id'")
            if not cursor.fetchone():
                self.stdout.write('Adding vehicle_id column...')
                cursor.execute("ALTER TABLE histories ADD COLUMN vehicle_id int(11) DEFAULT NULL")
                self.stdout.write(self.style.SUCCESS('Added vehicle_id column'))
            else:
                self.stdout.write('vehicle_id column already exists')
                
            # Check if the plate_number column already exists
            cursor.execute("SHOW COLUMNS FROM histories LIKE 'plate_number'")
            if not cursor.fetchone():
                self.stdout.write('Adding plate_number column...')
                cursor.execute("ALTER TABLE histories ADD COLUMN plate_number varchar(20) DEFAULT NULL")
                self.stdout.write(self.style.SUCCESS('Added plate_number column'))
            else:
                self.stdout.write('plate_number column already exists')
                
            # Update Django migrations table to mark our migration as applied
            cursor.execute(
                "UPDATE django_migrations SET applied = NOW() WHERE app = 'webadmin' AND name = '0004_history_vehicle_id_alter_history_plate_number'"
            )
            
            self.stdout.write(self.style.SUCCESS('Successfully modified History table'))
