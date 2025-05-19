import os
import django

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PBL_5.settings')
django.setup()

from django.db import connection

def fix_vehicle_id_column():
    """Sửa lỗi cột trong bảng histories"""
    with connection.cursor() as cursor:
        # Kiểm tra xem cột vehicle_id đã tồn tại chưa
        cursor.execute("SHOW COLUMNS FROM histories LIKE 'vehicle_id'")
        if not cursor.fetchone():
            print('Thêm cột vehicle_id...')
            cursor.execute("ALTER TABLE histories ADD COLUMN vehicle_id varchar(36) DEFAULT NULL")
            print('Đã thêm cột vehicle_id')
            
            # Sao chép dữ liệu từ vehicle_plate_id sang vehicle_id
            print('Sao chép dữ liệu từ vehicle_plate_id sang vehicle_id...')
            cursor.execute("UPDATE histories SET vehicle_id = vehicle_plate_id")
            print('Đã sao chép dữ liệu')
        else:
            print('Cột vehicle_id đã tồn tại')
        
        # Kiểm tra xem cột vehicle_plate_id có tồn tại không
        cursor.execute("SHOW COLUMNS FROM histories LIKE 'vehicle_plate_id'")
        if cursor.fetchone():
            print('Xóa cột vehicle_plate_id...')
            cursor.execute("ALTER TABLE histories DROP COLUMN vehicle_plate_id")
            print('Đã xóa cột vehicle_plate_id')
        else:
            print('Cột vehicle_plate_id không tồn tại')
            
        # Đánh dấu migration 0002_alter_history_vehicle_id là đã được áp dụng
        print('Đánh dấu migration là đã hoàn thành...')
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
            ["webadmin", "0002_alter_history_vehicle_id"]
        )
        print('Đã đánh dấu migration hoàn thành')

if __name__ == "__main__":
    fix_vehicle_id_column()
