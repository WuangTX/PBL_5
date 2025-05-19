import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PBL_5.settings')
django.setup()

from django.db import connection

def drop_plate_number_column():
    """Xóa cột plate_number từ bảng histories"""
    with connection.cursor() as cursor:
        # Kiểm tra xem cột plate_number có tồn tại không
        cursor.execute("SHOW COLUMNS FROM histories LIKE 'plate_number'")
        if cursor.fetchone():
            print('Đang xóa cột plate_number...')
            cursor.execute("ALTER TABLE histories DROP COLUMN plate_number")
            print('Đã xóa cột plate_number thành công')
        else:
            print('Cột plate_number không tồn tại')
            
        print('Hoàn tất cập nhật cấu trúc bảng')

if __name__ == '__main__':
    drop_plate_number_column()
