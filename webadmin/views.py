from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db import models
import requests
from .models import ParkingSpace, History, Vehicle
from account.models import User
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import uuid
import json
from django.core.paginator import Paginator

# Các decorator xác thực
def login_required(view_func):
    """
    Decorator để kiểm tra đăng nhập trong các view
    """
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.info(request, 'Vui lòng đăng nhập để tiếp tục.')
            return redirect('/account/login/')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    """
    Decorator để kiểm tra quyền admin trong các view
    """
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.info(request, 'Vui lòng đăng nhập để tiếp tục.')
            return redirect('/account/login/')
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Bạn không có quyền truy cập trang này.')
            return redirect('/account/login/')
        return view_func(request, *args, **kwargs)
    return wrapper

# Sử dụng decorator admin_required cho các view yêu cầu quyền admin
@admin_required
def index(request):
    try:
        # Get counts of parked and exited vehicles
        total_spaces = ParkingSpace.objects.count()
        
        parked_vehicles = History.objects.filter(time_out__isnull=True).count()
        available_spaces = total_spaces - parked_vehicles
        
        # Get hourly vehicle traffic for the last 24 hours
        now = timezone.now()
        last_24_hours = now - timedelta(days=1)
        
        # Tạo danh sách 24 giờ với số lượng xe là 0
        hourly_data = {i: 0 for i in range(24)}
        
        # Lấy dữ liệu thực tế
        traffic_data = History.objects.filter(
            time_in__gte=last_24_hours
        ).extra(
            select={'hour': 'HOUR(time_in)'}
        ).values('hour').annotate(count=Count('id'))

        # Cập nhật số liệu thực tế vào danh sách
        for entry in traffic_data:
            hour = entry['hour']
            if hour in hourly_data:
                hourly_data[hour] = entry['count']

        # Chuyển đổi dữ liệu thành danh sách để dễ xử lý trong template
        hourly_traffic = [{'hour': hour, 'count': count} for hour, count in hourly_data.items()]
        
        # Get vehicles that have been parked for more than 24 hours
        long_term_vehicles = History.objects.filter(
            time_in__lte=last_24_hours,
            time_out__isnull=True
        ).all()[:5]  # Giới hạn 5 xe
        
        # Get unregistered vehicles (không tìm thấy trong bảng Vehicle)
        active_histories = History.objects.filter(time_out__isnull=True)
        plate_numbers = active_histories.values_list('plate_number', flat=True)
        registered_plates = Vehicle.objects.filter(license_plate__in=plate_numbers).values_list('license_plate', flat=True)
        
        # Lọc ra các biển số không đăng ký (không có trong bảng Vehicle)
        unregistered_plates = set(plate_numbers) - set(registered_plates)
        unregistered_vehicles = active_histories.filter(plate_number__in=unregistered_plates)[:5]

        context = {
            'parking_spaces': ParkingSpace.objects.all(),
            'parked_vehicles': parked_vehicles,
            'available_spaces': available_spaces,
            'total_spaces': total_spaces,
            'occupancy_rate': (parked_vehicles / total_spaces * 100) if total_spaces > 0 else 0,
            'hourly_traffic': json.dumps(hourly_traffic),
            'long_term_vehicles': long_term_vehicles,
            'unregistered_vehicles': unregistered_vehicles,
        }
        
        return render(request, 'home/index.html', context)
    
    except Exception as e:
        print(f"Error in index view: {str(e)}")
        messages.error(request, "Có lỗi xảy ra khi tải trang. Vui lòng thử lại sau.")
        context = {
            'parking_spaces': [],
            'parked_vehicles': 0,
            'available_spaces': 0,
            'total_spaces': 0,
            'occupancy_rate': 0,
            'hourly_traffic': json.dumps([{'hour': i, 'count': 0} for i in range(24)]),
            'long_term_vehicles': [],
            'unregistered_vehicles': [],
        }
        return render(request, 'home/index.html', context)

@admin_required
def parked_cars(request):
    try:
        # Lấy danh sách xe đang đỗ dựa vào lịch sử (xe có time_out là null)
        active_histories = History.objects.filter(
            time_out__isnull=True
        ).select_related('parking_space')
        
        # Lấy thông tin xe từ biển số trong lịch sử
        plate_numbers = active_histories.values_list('plate_number', flat=True)
        parked_vehicles = Vehicle.objects.filter(
            license_plate__in=plate_numbers
        ).select_related('user')
        
        # Kết hợp thông tin lịch sử và xe
        for vehicle in parked_vehicles:
            # Tìm history tương ứng
            history = next((h for h in active_histories if h.plate_number == vehicle.license_plate), None)
            if history:
                # Thêm thời gian vào và vị trí đỗ vào vehicle để hiển thị
                vehicle.entry_time = history.time_in
                vehicle.parking_space = history.parking_space
        
        return render(request, 'menu/parked_cars.html', {
            'parked_vehicles': parked_vehicles
        })
    except Exception as e:
        messages.error(request, f"Có lỗi xảy ra: {str(e)}")
        return render(request, 'menu/parked_cars.html', {
            'parked_vehicles': []
        })

@admin_required
@csrf_exempt
def add_vehicle(request):
    if request.method == 'POST':
        try:
            license_plate = request.POST.get('license_plate')
            vehicle_type = request.POST.get('vehicle_type')
            owner_name = request.POST.get('owner_name')
            phone_number = request.POST.get('phone_number')
            email = request.POST.get('email', None)  # Email là tùy chọn
            
            # Kiểm tra biển số xe
            existing_vehicle = Vehicle.objects.filter(license_plate=license_plate).first()
            if existing_vehicle:
                messages.error(request, f'Biển số {license_plate} đã được đăng ký cho {existing_vehicle.user.name}')
                return redirect('add_vehicle')
            
            # Tìm hoặc tạo user mới
            user = None
            try:
                user = User.objects.get(phone_number=phone_number)
                # Cập nhật tên và email nếu đã thay đổi
                if user.name != owner_name or (email and user.email != email):
                    user.name = owner_name
                    if email:  # Chỉ cập nhật email nếu có
                        user.email = email
                    user.save()
            except User.DoesNotExist:
                # Tạo user mới với mật khẩu mặc định 123456
                user = User.objects.create(
                    id=uuid.uuid4(),
                    name=owner_name,
                    email=email,  # Có thể None
                    phone_number=phone_number,
                    password=make_password("123456"),  # Mật khẩu mặc định
                    role='customer'
                )
            
            # Xử lý ảnh xe nếu có
            image_path = None
            if 'vehicle_image' in request.FILES:
                # Lấy file hình ảnh từ request
                image = request.FILES['vehicle_image']
                
                # Tạo thư mục lưu ảnh nếu chưa tồn tại
                import os
                from django.conf import settings
                
                # Thư mục lưu ảnh nằm trong thư mục media/vehicles/
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'vehicles')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Tạo tên file duy nhất dựa trên biển số xe và timestamp
                import time
                filename = f"{license_plate.replace(' ', '_')}_{int(time.time())}{os.path.splitext(image.name)[1]}"
                file_path = os.path.join(upload_dir, filename)
                
                # Lưu file
                with open(file_path, 'wb+') as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)
                
                # Đường dẫn tương đối để lưu vào database
                image_path = f"vehicles/{filename}"
            
            # Tạo xe mới
            vehicle = Vehicle.objects.create(
                id=uuid.uuid4(),
                license_plate=license_plate,
                vehicle_type=vehicle_type,
                user=user,
                image_path=image_path
            )
            
            messages.success(request, f'Đã đăng ký thành công xe {license_plate} cho {owner_name}')
            return redirect('add_vehicle')
            
        except Exception as e:
            messages.error(request, f'Lỗi khi đăng ký xe: {str(e)}')
            return render(request, 'menu/add_vehicle.html')
            
    return render(request, 'menu/add_vehicle.html')

@admin_required
@csrf_exempt
def exit_vehicle(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            vehicle_id = data.get('vehicle_id')
            
            # Lấy thông tin xe
            vehicle = Vehicle.objects.get(id=vehicle_id)
            
            # Cập nhật lịch sử
            history = History.objects.filter(
                plate_number=vehicle.license_plate,
                time_out__isnull=True
            ).latest('time_in')
            
            # Lấy thông tin vị trí đỗ trước khi cập nhật history
            parking_space = history.parking_space
            
            # Cập nhật thời gian xuất xe
            history.time_out = timezone.now()
            history.save()
            
            # Cập nhật trạng thái vị trí đỗ xe (nếu có)
            if parking_space:
                parking_space.is_occupied = 0  # Đánh dấu là không còn xe đỗ
                parking_space.save()
            
            messages.success(request, f'Xe {vehicle.license_plate} đã xuất thành công')
            return HttpResponse(status=200)
            
        except Exception as e:
            messages.error(request, f'Lỗi khi xuất xe: {str(e)}')
            return HttpResponse(str(e), status=500)
            
    return HttpResponse('Method not allowed', status=405)

@admin_required
def vehicle_history(request):
    try:
        # Lấy các tham số lọc từ query string
        license_plate = request.GET.get('license_plate', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        page = request.GET.get('page', 1)
        
        # Query cơ bản - đã xóa select_related('user') vì không còn mối quan hệ trực tiếp với user
        history_query = History.objects.all()
        
        # Áp dụng các bộ lọc
        if license_plate:
            history_query = history_query.filter(plate_number__icontains=license_plate)
        
        if date_from:
            history_query = history_query.filter(time_in__gte=date_from)
            
        if date_to:
            history_query = history_query.filter(time_in__lte=date_to + ' 23:59:59')
            
        # Sắp xếp theo thời gian vào gần nhất
        history_query = history_query.order_by('-time_in')
        
        # Phân trang
        paginator = Paginator(history_query, 10)  # 10 bản ghi mỗi trang
        page_obj = paginator.get_page(page)
        
        context = {
            'records': page_obj,
            'page_obj': page_obj,
            'license_plate': license_plate,
            'date_from': date_from,
            'date_to': date_to
        }
        
        return render(request, 'menu/vehicle_history.html', context)
        
    except Exception as e:
        messages.error(request, f'Lỗi khi tải lịch sử: {str(e)}')
        return render(request, 'menu/vehicle_history.html', {
            'records': [],
            'page_obj': None
        })

@admin_required
@csrf_exempt
def check_license_plate(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            license_plate = data.get('license_plate')
            
            # Kiểm tra biển số đã tồn tại chưa
            existing_vehicle = Vehicle.objects.filter(license_plate=license_plate).first()
            
            if existing_vehicle:
                return JsonResponse({
                    'isAvailable': False,
                    'ownerName': existing_vehicle.user.name
                })
            return JsonResponse({'isAvailable': True})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@admin_required
@csrf_exempt
def check_phone(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone')
            
            # Kiểm tra số điện thoại đã tồn tại chưa
            existing_user = User.objects.filter(phone_number=phone).first()
            
            if existing_user:
                return JsonResponse({
                    'isNewUser': False,
                    'ownerName': existing_user.name,
                    'userId': str(existing_user.id)
                })
            return JsonResponse({'isNewUser': True})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@admin_required
def manage_users(request):
    try:
        # Lấy tham số tìm kiếm
        search_query = request.GET.get('q', '')
        
        # Query cơ bản
        users = User.objects.all()
        
        # Áp dụng bộ lọc tìm kiếm
        if search_query:
            users = users.filter(
                models.Q(name__icontains=search_query) |
                models.Q(phone_number__icontains=search_query) |
                models.Q(email__icontains=search_query)
            )
        
        # Phân trang
        page = request.GET.get('page', 1)
        paginator = Paginator(users, 10)  # 10 users per page
        users_page = paginator.get_page(page)
        
        context = {
            'users': users_page,
            'search_query': search_query,
        }
        
        return render(request, 'menu/manage_users.html', context)
        
    except Exception as e:
        messages.error(request, f'Lỗi khi tải danh sách người dùng: {str(e)}')
        return render(request, 'menu/manage_users.html', {'users': []})

@admin_required
@csrf_exempt
def update_user(request, user_id):
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            data = json.loads(request.body)
            
            # Kiểm tra email mới có bị trùng không
            new_email = data.get('email')
            if new_email and new_email != user.email:
                if User.objects.filter(email=new_email).exists():
                    return JsonResponse({
                        'error': 'Email đã được sử dụng bởi tài khoản khác'
                    }, status=400)
            
            # Kiểm tra số điện thoại mới có bị trùng không
            new_phone = data.get('phone_number')
            if new_phone and new_phone != user.phone_number:
                if User.objects.filter(phone_number=new_phone).exists():
                    return JsonResponse({
                        'error': 'Số điện thoại đã được sử dụng bởi tài khoản khác'
                    }, status=400)
            
            # Cập nhật thông tin user
            user.name = data.get('name', user.name)
            user.email = new_email or user.email
            user.phone_number = new_phone or user.phone_number
            
            # Nếu có mật khẩu mới
            new_password = data.get('password')
            if new_password:
                user.password = make_password(new_password)
                
            user.save()
            
            # Cập nhật số điện thoại trong lịch sử nếu có thay đổi
            if new_phone and new_phone != user.phone_number:
                History.objects.filter(user=user).update(phone_number=new_phone)
            
            return JsonResponse({
                'message': 'Cập nhật thành công',
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'role': user.role
                }
            })
            
        except User.DoesNotExist:
            return JsonResponse({'error': 'Không tìm thấy người dùng'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@admin_required
def vehicle_detail(request, vehicle_id):
    try:
        # Lấy thông tin xe
        vehicle = Vehicle.objects.get(id=vehicle_id)
        
        # Lấy thông tin lịch sử đỗ xe hiện tại (nếu đang đỗ)
        current_parking = History.objects.filter(
            plate_number=vehicle.license_plate,
            time_out__isnull=True
        ).select_related('parking_space').first()
        
        # Lấy lịch sử đỗ xe trước đây
        past_parkings = History.objects.filter(
            plate_number=vehicle.license_plate,
            time_out__isnull=False
        ).order_by('-time_in')[:5]  # lấy 5 lần gần nhất
        
        context = {
            'vehicle': vehicle,
            'current_parking': current_parking,
            'past_parkings': past_parkings,
        }
        
        return render(request, 'menu/vehicle_detail.html', context)
        
    except Vehicle.DoesNotExist:
        messages.error(request, 'Không tìm thấy thông tin xe')
        return redirect('parked_cars')
    except Exception as e:
        messages.error(request, f'Lỗi: {str(e)}')
        return redirect('parked_cars')

@admin_required
def manage_vehicles(request):
    try:
        # Lấy tham số tìm kiếm
        search_query = request.GET.get('q', '')
        
        # Query cơ bản
        vehicles = Vehicle.objects.select_related('user').all()
        
        # Áp dụng bộ lọc tìm kiếm
        if search_query:
            vehicles = vehicles.filter(
                models.Q(license_plate__icontains=search_query) |
                models.Q(user__name__icontains=search_query) |
                models.Q(vehicle_type__icontains=search_query)
            )
        
        # Phân trang
        page = request.GET.get('page', 1)
        paginator = Paginator(vehicles, 10)  # 10 vehicles per page
        vehicles_page = paginator.get_page(page)
        
        context = {
            'vehicles': vehicles_page,
            'search_query': search_query,
        }
        
        return render(request, 'menu/manage_vehicles.html', context)
        
    except Exception as e:
        messages.error(request, f'Lỗi khi tải danh sách xe: {str(e)}')
        return render(request, 'menu/manage_vehicles.html', {'vehicles': []})

