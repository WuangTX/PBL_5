from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
import json
import re
from webadmin.models import User, Vehicle, History, ParkingSpace
from datetime import datetime

def vehicle_management_view(request):
    """Trang chính quản lý xe"""
    user = None
    user_vehicles = []
    
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            # Lấy tất cả xe của user với thông tin lịch sử mới nhất
            user_vehicles = Vehicle.objects.filter(user=user).prefetch_related('histories')
        except User.DoesNotExist:
            pass

    context = {
        'user': user,
        'vehicles': user_vehicles,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'vehicle_management/vehicle_list.html', context)

def add_vehicle_view(request):
    """Trang thêm xe mới"""
    user = None
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass
    
    if request.method == 'POST':
        license_plate = request.POST.get('license_plate')
        vehicle_type = request.POST.get('vehicle_type')
        vehicle_image = request.FILES.get('vehicle_image')
        
        # Validation
        if not license_plate or not vehicle_type:
            return JsonResponse({'error': 'Vui lòng điền đầy đủ thông tin'}, status=400)
        
        # Kiểm tra biển số xe đã tồn tại
        if Vehicle.objects.filter(license_plate=license_plate.strip().upper()).exists():
            return JsonResponse({'error': 'Biển số xe đã được đăng ký'}, status=400)
        
        # Validation biển số xe Việt Nam
        license_pattern = r'^[0-9]{2}[A-Z]{1,2}[0-9]{4,5}$'
        if not re.match(license_pattern, license_plate.strip().upper()):
            return JsonResponse({'error': 'Biển số xe không đúng định dạng'}, status=400)
        
        try:
            # Lưu hình ảnh nếu có
            image_path = None
            if vehicle_image:
                fs = FileSystemStorage(location=settings.MEDIA_ROOT)
                filename = f"{license_plate}_{int(datetime.now().timestamp())}.{vehicle_image.name.split('.')[-1]}"
                image_path = fs.save(f"vehicles/{filename}", vehicle_image)
            
            # Tạo xe mới
            vehicle = Vehicle.objects.create(
                license_plate=license_plate.strip().upper(),
                vehicle_type=vehicle_type,
                image_path=image_path,
                user=user
            )
            
            return JsonResponse({
                'message': 'Đăng ký xe thành công!',
                'vehicle_id': vehicle.id
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Có lỗi xảy ra: {str(e)}'}, status=500)
    
    context = {
        'user': user,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'vehicle_management/add_vehicle.html', context)

@csrf_exempt
def check_license_plate(request):
    """API kiểm tra biển số xe đã tồn tại"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            license_plate = data.get('license_plate', '').strip().upper()
            
            if not license_plate:
                return JsonResponse({'error': 'Thiếu biển số xe'}, status=400)
            
            # Validation format biển số
            license_pattern = r'^[0-9]{2}[A-Z]{1,2}[0-9]{4,5}$'
            if not re.match(license_pattern, license_plate):
                return JsonResponse({
                    'exists': False, 
                    'error': 'Biển số xe không đúng định dạng (VD: 51F12345, 29A12345)'
                })
            
            # Kiểm tra biển số đã tồn tại
            exists = Vehicle.objects.filter(license_plate=license_plate).exists()
            
            return JsonResponse({
                'exists': exists,
                'message': 'Biển số xe đã được đăng ký' if exists else 'Biển số xe hợp lệ'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Dữ liệu JSON không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Lỗi server: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Phương thức không được hỗ trợ'}, status=405)

def vehicle_detail_view(request, vehicle_id):
    """Trang chi tiết xe và lịch sử"""
    user = None
    vehicle = None
    vehicle_histories = []
    current_parking = None
    
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            # Lấy xe thuộc về user
            vehicle = get_object_or_404(Vehicle, id=vehicle_id, user=user)
            
            # Lấy lịch sử của xe (sắp xếp theo thời gian mới nhất)
            vehicle_histories = History.objects.filter(vehicle=vehicle).order_by('-time_in')
            
            # Kiểm tra xe có đang đỗ không (có time_in nhưng chưa có time_out)
            current_parking = History.objects.filter(
                vehicle=vehicle,
                time_out__isnull=True
            ).first()
            
        except User.DoesNotExist:
            pass
    
    context = {
        'user': user,
        'vehicle': vehicle,
        'vehicle_histories': vehicle_histories,
        'current_parking': current_parking,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'vehicle_management/vehicle_detail.html', context)

def vehicle_status_api(request, vehicle_id):
    """API lấy trạng thái hiện tại của xe"""
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
        
        user = User.objects.get(id=user_id)
        vehicle = get_object_or_404(Vehicle, id=vehicle_id, user=user)
        
        # Kiểm tra xe có đang đỗ không
        current_parking = History.objects.filter(
            vehicle=vehicle,
            time_out__isnull=True
        ).select_related('parking_space').first()
        
        if current_parking:
            # Tính thời gian đỗ
            now = timezone.now()
            duration = now - current_parking.time_in
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            
            return JsonResponse({
                'status': 'parked',
                'parking_space': current_parking.parking_space.space_number if current_parking.parking_space else 'Không xác định',
                'entry_time': current_parking.time_in.strftime('%d/%m/%Y %H:%M:%S'),
                'duration': f"{hours} giờ {minutes} phút",
                'duration_hours': hours,
                'duration_minutes': minutes
            })
        else:
            return JsonResponse({
                'status': 'not_parked',
                'message': 'Xe hiện không đỗ trong bãi'
            })
            
    except User.DoesNotExist:
        return JsonResponse({'error': 'Người dùng không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
