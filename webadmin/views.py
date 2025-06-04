from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db import models
import requests
from .models import ParkingSpace, History, Vehicle
from account.models import User, TransactionHistory
from .models import Payment
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
import uuid
import json
import time
import traceback
from django.core.paginator import Paginator
import os
from django.conf import settings
from decimal import Decimal

# Helper function for UUID conversion
def parse_uuid(uuid_str):
    """Convert a string to a UUID object, return None if invalid"""
    try:
        # Skip conversion if already a UUID
        if isinstance(uuid_str, uuid.UUID):
            return uuid_str
            
        # Handle None or empty string
        if uuid_str is None or uuid_str == '':
            return None
        
        # Remove any curly braces, dashes, and whitespace
        clean_uuid = uuid_str.strip().replace('{', '').replace('}', '').replace('-', '').strip()
        
        # Handle potential hexadecimal formatting issues
        if len(clean_uuid) == 32:
            # Insert hyphens to form a valid UUID format
            formatted_uuid = f"{clean_uuid[0:8]}-{clean_uuid[8:12]}-{clean_uuid[12:16]}-{clean_uuid[16:20]}-{clean_uuid[20:]}"
            return uuid.UUID(formatted_uuid)
        
        # Try standard conversion
        return uuid.UUID(uuid_str)
    except (ValueError, AttributeError, TypeError) as e:
        print(f"UUID parse error: {e}, value: {uuid_str}")
        return None

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
        hourly_data = {}
        for i in range(24):
            hourly_data[i] = {'entrance': 0, 'exit': 0}
        
        # Lấy dữ liệu xe vào trong 24h qua
        entrance_data = History.objects.filter(
            time_in__gte=last_24_hours
        ).extra(
            select={'hour': 'HOUR(time_in)'}
        ).values('hour').annotate(count=Count('id'))

        # Lấy dữ liệu xe ra trong 24h qua
        exit_data = History.objects.filter(
            time_out__gte=last_24_hours
        ).extra(
            select={'hour': 'HOUR(time_out)'}
        ).values('hour').annotate(count=Count('id'))

        # Cập nhật số liệu thực tế vào danh sách
        for entry in entrance_data:
            hour = entry['hour']
            if hour in hourly_data:
                hourly_data[hour]['entrance'] = entry['count']
        
        for entry in exit_data:
            hour = entry['hour']
            if hour in hourly_data:
                hourly_data[hour]['exit'] = entry['count']

        # Chuyển đổi dữ liệu thành danh sách để dễ xử lý trong template
        hourly_traffic = [{'hour': hour, 'entrance': data['entrance'], 'exit': data['exit']} 
                          for hour, data in hourly_data.items()]
        
        # Get vehicles that have been parked for more than 24 hours
        long_term_vehicles = History.objects.filter(
            time_in__lte=last_24_hours,
            time_out__isnull=True
        ).all()[:5]  # Giới hạn 5 xe
        
        # Get unregistered vehicles (không tìm thấy trong bảng Vehicle)
        active_histories = History.objects.filter(time_out__isnull=True)
        
        # Tìm những lịch sử mà vehicle_id không có trong bảng Vehicle
        vehicle_ids = active_histories.values_list('vehicle_id', flat=True)
        registered_vehicle_ids = Vehicle.objects.filter(id__in=vehicle_ids).values_list('id', flat=True)
        
        # Lọc ra các vehicle_id không đăng ký (không có trong bảng Vehicle)
        unregistered_vehicle_ids = set(vehicle_ids) - set(registered_vehicle_ids)
        unregistered_vehicles = active_histories.filter(vehicle_id__in=unregistered_vehicle_ids)[:5]

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
        
        # Lấy thông tin xe từ vehicle_id trong lịch sử
        vehicle_ids = active_histories.values_list('vehicle_id', flat=True)
        parked_vehicles = Vehicle.objects.filter(
            id__in=vehicle_ids
        ).select_related('user')
        
        # Kết hợp thông tin lịch sử và xe
        for vehicle in parked_vehicles:
            # Tìm history tương ứng
            history = next((h for h in active_histories if h.vehicle_id == vehicle.id), None)
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
                vehicle_id=vehicle.id,
                time_out__isnull=True
            ).latest('time_in')
            
            # Lấy thông tin vị trí đỗ trước khi cập nhật history
            parking_space = history.parking_space
            
            # Cập nhật thời gian xuất xe
            history.time_out = timezone.now()
            history.save()
            
            # Tạo Payment record tự động sau khi xe xuất
            try:
                # Kiểm tra xem đã có Payment cho history này chưa
                existing_payment = Payment.objects.filter(history=history).first()
                if not existing_payment:
                    # Tính phí đỗ xe
                    parking_fee = history.calculate_fee()
                    if parking_fee is not None and parking_fee > 0:
                        # Tạo Payment record mới
                        Payment.objects.create(
                            history=history,
                            fee=Decimal(str(parking_fee)),
                            status=False  # Chưa thanh toán
                        )
                        print(f"Created payment record for history {history.id} with fee {parking_fee}")
            except Exception as payment_error:
                print(f"Error creating payment record: {str(payment_error)}")
                # Không dừng quá trình xuất xe nếu tạo payment lỗi
            
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
            # Tìm các vehicle_id có license_plate phù hợp
            vehicles = Vehicle.objects.filter(license_plate__icontains=license_plate)
            vehicle_ids = vehicles.values_list('id', flat=True)
            history_query = history_query.filter(vehicle_id__in=vehicle_ids)
        
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
            vehicle_id=vehicle.id,
            time_out__isnull=True
        ).select_related('parking_space').first()
        
        # Lấy lịch sử đỗ xe trước đây
        past_parkings = History.objects.filter(
            vehicle_id=vehicle.id,
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
        vehicles = Vehicle.objects.select_related('user').all().order_by('-created_at')
        
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

@admin_required
def manage_parking_spaces(request):
    try:
        # Lấy tham số tìm kiếm
        search_query = request.GET.get('q', '')
        level_filter = request.GET.get('level', '')
        status_filter = request.GET.get('status', '')
        
        # Query cơ bản
        parking_spaces = ParkingSpace.objects.all()
        
        # Áp dụng bộ lọc tìm kiếm và lọc
        if search_query:
            parking_spaces = parking_spaces.filter(
                models.Q(space_number__icontains=search_query) |
                models.Q(notes__icontains=search_query)
            )
        
        if level_filter:
            parking_spaces = parking_spaces.filter(level=level_filter)
            
        if status_filter in ['0', '1']:
            parking_spaces = parking_spaces.filter(is_occupied=status_filter)
        
        # Sắp xếp theo tầng và số vị trí
        parking_spaces = parking_spaces.order_by('level', 'space_number')
        
        # Đếm số lượng theo trạng thái
        total_spaces = ParkingSpace.objects.count()
        occupied_spaces = ParkingSpace.objects.filter(is_occupied=1).count()
        available_spaces = total_spaces - occupied_spaces
        
        # Phân trang
        page = request.GET.get('page', 1)
        paginator = Paginator(parking_spaces, 10)  # 10 vị trí đỗ xe mỗi trang
        spaces_page = paginator.get_page(page)
        
        # Chuẩn bị mảng level để hiển thị bộ lọc
        levels = ParkingSpace.objects.values_list('level', flat=True).distinct().order_by('level')
        
        context = {
            'parking_spaces': spaces_page,
            'search_query': search_query,
            'level_filter': level_filter,
            'status_filter': status_filter,
            'levels': levels,
            'total_spaces': total_spaces,
            'occupied_spaces': occupied_spaces,
            'available_spaces': available_spaces
        }
        
        return render(request, 'menu/manage_parking_spaces.html', context)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in manage_parking_spaces: {str(e)}")
        print(f"Error details: {error_details}")
        messages.error(request, f'Lỗi khi tải danh sách vị trí đỗ xe: {str(e)}')
        return render(request, 'menu/manage_parking_spaces.html', {
            'parking_spaces': [],
            'levels': [],
            'total_spaces': 0,
            'occupied_spaces': 0,
            'available_spaces': 0
        })

@admin_required
@csrf_exempt
def add_parking_space(request):
    if request.method == 'POST':
        try:
            space_number = request.POST.get('space_number')
            level = request.POST.get('level')
            notes = request.POST.get('notes', '')
            
            # Kiểm tra xem vị trí đỗ đã tồn tại chưa
            existing_space = ParkingSpace.objects.filter(level=level, space_number=space_number).first()
            if existing_space:
                messages.error(request, f'Vị trí đỗ Tầng {level} - Ô {space_number} đã tồn tại')
                return redirect('manage_parking_spaces')
            
            # Tạo vị trí đỗ mới
            ParkingSpace.objects.create(
                id=uuid.uuid4(),
                space_number=space_number,
                level=level,
                notes=notes,
                is_occupied=0
            )
            
            messages.success(request, f'Đã thêm thành công vị trí đỗ Tầng {level} - Ô {space_number}')
            return redirect('manage_parking_spaces')
            
        except Exception as e:
            messages.error(request, f'Lỗi khi thêm vị trí đỗ xe: {str(e)}')
            return redirect('manage_parking_spaces')
    
    return redirect('manage_parking_spaces')

@admin_required
@csrf_exempt
def delete_parking_space(request, space_id):
    try:
        # Convert string ID to UUID
        uuid_id = parse_uuid(space_id)
        if uuid_id is None:
            messages.error(request, f'ID không hợp lệ')
            return redirect('manage_parking_spaces')
        
        parking_space = ParkingSpace.objects.get(id=uuid_id)
        
        # Kiểm tra xem vị trí đỗ có đang được sử dụng không
        if parking_space.is_occupied == 1:
            messages.error(request, f'Không thể xóa vị trí đỗ đang có xe')
            return redirect('manage_parking_spaces')
        
        # Kiểm tra xem vị trí đỗ có trong lịch sử không
        if History.objects.filter(parking_space=parking_space, time_out__isnull=True).exists():
            messages.error(request, f'Không thể xóa vị trí đỗ đang được sử dụng trong lịch sử')
            return redirect('manage_parking_spaces')
        
        # Lưu thông tin để hiển thị thông báo
        space_info = f'Tầng {parking_space.level} - Ô {parking_space.space_number}'
        
        # Xóa vị trí đỗ
        parking_space.delete()
        
        messages.success(request, f'Đã xóa thành công vị trí đỗ {space_info}')
        return redirect('manage_parking_spaces')
        
    except ParkingSpace.DoesNotExist:
        messages.error(request, f'Không tìm thấy vị trí đỗ')
        return redirect('manage_parking_spaces')
    except Exception as e:
        messages.error(request, f'Lỗi khi xóa vị trí đỗ: {str(e)}')
        return redirect('manage_parking_spaces')

@admin_required
@csrf_exempt
def update_parking_space(request, space_id):
    if request.method == 'POST':
        try:
            # Convert string ID to UUID
            uuid_id = parse_uuid(space_id)
            if uuid_id is None:
                messages.error(request, f'ID không hợp lệ')
                return redirect('manage_parking_spaces')
                
            parking_space = ParkingSpace.objects.get(id=uuid_id)
            
            # Lấy dữ liệu từ form
            space_number = request.POST.get('space_number')
            level = request.POST.get('level')
            notes = request.POST.get('notes', '')
            
            # Kiểm tra xem có vị trí đỗ khác với cùng level và space_number không
            if ParkingSpace.objects.filter(level=level, space_number=space_number).exclude(id=uuid_id).exists():
                messages.error(request, f'Vị trí đỗ Tầng {level} - Ô {space_number} đã tồn tại')
                return redirect('manage_parking_spaces')
            
            # Cập nhật thông tin
            parking_space.space_number = space_number
            parking_space.level = level
            parking_space.notes = notes
            parking_space.save()
            
            messages.success(request, f'Đã cập nhật thành công vị trí đỗ Tầng {level} - Ô {space_number}')
            return redirect('manage_parking_spaces')
            
        except ParkingSpace.DoesNotExist:
            messages.error(request, f'Không tìm thấy vị trí đỗ')
            return redirect('manage_parking_spaces')
        except Exception as e:
            messages.error(request, f'Lỗi khi cập nhật vị trí đỗ: {str(e)}')
            return redirect('manage_parking_spaces')
    
    return redirect('manage_parking_spaces')

@admin_required
def traffic_data(request):
    """API endpoint để lấy dữ liệu lưu lượng xe trong 24h qua"""
    try:
        # Lấy dữ liệu lưu lượng xe của 24h trước
        now = timezone.now()
        last_24_hours = now - timedelta(days=1)
        
        # Tạo danh sách 24 giờ với số lượng xe là 0
        hourly_data = {}
        for i in range(24):
            hourly_data[i] = {'entrance': 0, 'exit': 0}
        
        # Lấy dữ liệu xe vào trong 24h qua
        entrance_data = History.objects.filter(
            time_in__gte=last_24_hours
        ).extra(
            select={'hour': 'HOUR(time_in)'}
        ).values('hour').annotate(count=Count('id'))

        # Lấy dữ liệu xe ra trong 24h qua
        exit_data = History.objects.filter(
            time_out__gte=last_24_hours
        ).extra(
            select={'hour': 'HOUR(time_out)'}
        ).values('hour').annotate(count=Count('id'))

        # Cập nhật số liệu thực tế vào danh sách
        for entry in entrance_data:
            hour = entry['hour']
            if hour in hourly_data:
                hourly_data[hour]['entrance'] = entry['count']
        
        for entry in exit_data:
            hour = entry['hour']
            if hour in hourly_data:
                hourly_data[hour]['exit'] = entry['count']

        # Chuyển đổi dữ liệu thành danh sách để JSON hóa
        hourly_traffic = [{'hour': hour, 'entrance': data['entrance'], 'exit': data['exit']} 
                          for hour, data in hourly_data.items()]
        
        return JsonResponse(hourly_traffic, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
@csrf_exempt
def update_vehicle_image(request, vehicle_id):
    """Cập nhật hoặc thêm ảnh xe"""
    if request.method == 'POST':
        try:
            # Lấy thông tin xe
            vehicle = Vehicle.objects.get(id=vehicle_id)
            
            # Kiểm tra xem có file ảnh được gửi lên không
            if 'vehicle_image' not in request.FILES:
                return JsonResponse({'error': 'Không có file ảnh được chọn'}, status=400)
            
            image = request.FILES['vehicle_image']
            
            # Xóa ảnh cũ nếu có
            if vehicle.image_path:
                old_image_path = os.path.join(settings.MEDIA_ROOT, vehicle.image_path)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Tạo thư mục lưu ảnh nếu chưa tồn tại
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'vehicles')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Tạo tên file duy nhất dựa trên biển số xe và timestamp
            import time
            filename = f"{vehicle.license_plate.replace(' ', '_')}_{int(time.time())}{os.path.splitext(image.name)[1]}"
            file_path = os.path.join(upload_dir, filename)
            
            # Lưu file
            with open(file_path, 'wb+') as destination:
                for chunk in image.chunks():
                    destination.write(chunk)
            
            # Cập nhật đường dẫn ảnh trong database
            vehicle.image_path = f"vehicles/{filename}"
            vehicle.save()
            
            return JsonResponse({
                'message': 'Cập nhật ảnh xe thành công',
                'image_url': f'/media/{vehicle.image_path}'
            })
            
        except Vehicle.DoesNotExist:
            return JsonResponse({'error': 'Không tìm thấy thông tin xe'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Lỗi khi cập nhật ảnh xe: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ===== QUẢN LÝ TÀI CHÍNH =====

@login_required
@admin_required  
def financial_overview(request):
    """Tổng quan tài chính"""
    # Thống kê tài chính
    total_revenue = Payment.objects.filter(status=True).aggregate(Sum('fee'))['fee__sum'] or 0
    pending_payments = Payment.objects.filter(status=False).count()
    total_users_balance = User.objects.aggregate(Sum('balance'))['balance__sum'] or 0
    
    # Doanh thu theo tháng (6 tháng gần nhất)
    from datetime import datetime
    import calendar
    monthly_revenue = []
    for i in range(6):
        month = (datetime.now().month - i - 1) % 12 + 1
        year = datetime.now().year
        if month > datetime.now().month:
            year -= 1
            
        month_revenue = Payment.objects.filter(
            status=True,
            created_at__year=year,
            created_at__month=month
        ).aggregate(Sum('fee'))['fee__sum'] or 0
        
        monthly_revenue.append({
            'month': f"{calendar.month_name[month]} {year}",
            'revenue': float(month_revenue)
        })
    
    monthly_revenue.reverse()
    
    # Giao dịch gần đây
    recent_transactions = TransactionHistory.objects.select_related('user').order_by('-created_at')[:10]
    
    # Thanh toán chưa xử lý
    pending_payments_list = Payment.objects.filter(status=False).select_related('history__vehicle__user').order_by('-created_at')[:10]
    
    context = {
        'total_revenue': total_revenue,
        'pending_payments_count': pending_payments,
        'total_users_balance': total_users_balance,
        'monthly_revenue': monthly_revenue,
        'recent_transactions': recent_transactions,
        'pending_payments': pending_payments_list,
    }
    
    return render(request, 'menu/financial_overview.html', context)

@login_required
@admin_required  
def manage_user_balance(request):
    """Quản lý số dư tài khoản người dùng"""
    search_query = request.GET.get('search', '')
    
    # Tìm kiếm người dùng
    users = User.objects.all()
    if search_query:
        users = users.filter(
            Q(name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Phân trang
    paginator = Paginator(users.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'menu/manage_user_balance.html', context)

@login_required
@admin_required
def adjust_user_balance(request, user_id):
    """Điều chỉnh số dư tài khoản người dùng"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            adjustment_type = request.POST.get('adjustment_type')  # 'add' hoặc 'subtract'
            amount = Decimal(request.POST.get('amount', '0'))
            reason = request.POST.get('reason', '')
            
            if amount <= 0:
                return JsonResponse({'error': 'Số tiền phải lớn hơn 0'}, status=400)
            
            # Điều chỉnh số dư
            if adjustment_type == 'add':
                user.balance += amount
                transaction_type = 'ADMIN_ADD'
                transaction_amount = amount
            elif adjustment_type == 'subtract':
                if user.balance < amount:
                    return JsonResponse({'error': 'Số dư không đủ để trừ'}, status=400)
                user.balance -= amount
                transaction_type = 'ADMIN_SUBTRACT'
                transaction_amount = -amount
            else:
                return JsonResponse({'error': 'Loại điều chỉnh không hợp lệ'}, status=400)
            
            user.save()
            
            # Tạo giao dịch
            TransactionHistory.objects.create(
                user=user,
                transaction_type=transaction_type,
                amount=transaction_amount,
                payment_method='ADMIN_ADJUSTMENT',
                status='COMPLETED'
            )
            
            return JsonResponse({
                'success': True,
                'new_balance': float(user.balance),
                'message': f'Đã điều chỉnh số dư thành công. Lý do: {reason}'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'error': 'Người dùng không tồn tại'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Phương thức không được hỗ trợ'}, status=405)

@login_required
@admin_required
def transaction_history(request):
    """Lịch sử giao dịch"""
    # Lọc theo loại giao dịch
    transaction_type = request.GET.get('type', '')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    transactions = TransactionHistory.objects.select_related('user', 'payment').all()
    
    # Áp dụng các bộ lọc
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if search_query:
        transactions = transactions.filter(
            Q(user__name__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)
        )
    
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    # Phân trang
    paginator = Paginator(transactions.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Danh sách loại giao dịch để hiển thị trong dropdown
    transaction_types = TransactionHistory.objects.values_list('transaction_type', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'transaction_type': transaction_type,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'transaction_types': transaction_types,
    }
    
    return render(request, 'menu/transaction_history.html', context)

@login_required
@admin_required
def payment_management(request):
    """Quản lý thanh toán"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    payments = Payment.objects.select_related('history__vehicle__user').all()
    
    # Áp dụng bộ lọc
    if status_filter == 'paid':
        payments = payments.filter(status=True)
    elif status_filter == 'unpaid':
        payments = payments.filter(status=False)
    
    if search_query:
        payments = payments.filter(
            Q(history__vehicle__license_plate__icontains=search_query) |
            Q(history__vehicle__user__name__icontains=search_query) |
            Q(history__vehicle__user__phone_number__icontains=search_query)
        )
    
    # Phân trang
    paginator = Paginator(payments.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'menu/payment_management.html', context)

@login_required
@admin_required
def mark_payment_paid(request, payment_id):
    """Đánh dấu thanh toán đã hoàn thành"""
    if request.method == 'POST':
        try:
            payment = Payment.objects.get(id=payment_id)
            
            if payment.status:
                return JsonResponse({'error': 'Thanh toán này đã được xử lý'}, status=400)
            
            # Đánh dấu đã thanh toán
            payment.status = True
            payment.save()
            
            # Tạo giao dịch
            user = payment.history.vehicle.user
            TransactionHistory.objects.create(
                user=user,
                transaction_type='PARKING_PAYMENT',
                amount=-payment.fee,
                payment_method='ADMIN_CONFIRM',
                status='COMPLETED',
                payment=payment
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Đã xác nhận thanh toán thành công'
            })
            
        except Payment.DoesNotExist:
            return JsonResponse({'error': 'Thanh toán không tồn tại'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Phương thức không được hỗ trợ'}, status=405)

@login_required
@admin_required
def user_financial_detail(request, user_id):
    """Chi tiết tài chính của người dùng"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Người dùng không tồn tại')
        return redirect('manage_user_balance')
    
    # Lịch sử giao dịch của người dùng
    transactions = TransactionHistory.objects.filter(user=user).order_by('-created_at')
    
    # Thống kê
    total_deposited = transactions.filter(
        transaction_type__in=['ADMIN_ADD', 'DEPOSIT']
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_spent = abs(transactions.filter(
        transaction_type__in=['PARKING_PAYMENT', 'ADMIN_SUBTRACT']
    ).aggregate(Sum('amount'))['amount__sum'] or 0)
    
    # Phân trang giao dịch
    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'user': user,
        'page_obj': page_obj,
        'total_deposited': total_deposited,
        'total_spent': total_spent,
    }
    
    return render(request, 'menu/user_financial_detail.html', context)

