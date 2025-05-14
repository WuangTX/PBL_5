from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from account.models import User
from webadmin.models import Vehicle, History
from django.http import JsonResponse
import uuid

# Các decorator xác thực
def login_required(view_func):
    """
    Decorator để kiểm tra đăng nhập trong các view
    """
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.info(request, 'Vui lòng đăng nhập để tiếp tục.')
            return redirect('user_login')
        return view_func(request, *args, **kwargs)
    return wrapper

def customer_required(view_func):
    """
    Decorator để kiểm tra quyền người dùng thường trong các view
    """
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.info(request, 'Vui lòng đăng nhập để tiếp tục.')
            return redirect('user_login')
        if request.session.get('user_role') != 'customer':
            messages.error(request, 'Bạn không có quyền truy cập trang này.')
            return redirect('user_login')
        return view_func(request, *args, **kwargs)
    return wrapper

@customer_required
def index(request):
    """Trang chủ cho người dùng thông thường"""
    user_id = request.session['user_id']
    user = User.objects.get(id=user_id)
    
    return render(request, 'user/index.html', {'user': user})

@customer_required
def profile(request):
    """Trang thông tin cá nhân của người dùng"""
    user_id = request.session['user_id']
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        # Xử lý cập nhật thông tin người dùng
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        user.name = name
        user.email = email
        user.phone_number = phone
        user.save()
        
        messages.success(request, 'Thông tin cá nhân đã được cập nhật!')
        return redirect('user_profile')
    
    return render(request, 'user/profile.html', {'user': user})

@customer_required
def my_vehicles(request):
    """Trang quản lý xe của người dùng"""
    user_id = request.session['user_id']
    user = User.objects.get(id=user_id)
    vehicles = Vehicle.objects.filter(user=user)
    
    return render(request, 'user/vehicles.html', {'user': user, 'vehicles': vehicles})

@customer_required
def parking_history(request):
    """Trang lịch sử đỗ xe của người dùng"""
    user_id = request.session['user_id']
    user = User.objects.get(id=user_id)
    
    # Lấy tất cả xe của người dùng
    vehicles = Vehicle.objects.filter(user=user)
    license_plates = [vehicle.license_plate for vehicle in vehicles]
    
    # Lấy lịch sử đỗ xe dựa trên biển số xe
    histories = History.objects.filter(plate_number__in=license_plates).order_by('-time_in')
    
    return render(request, 'user/history.html', {'user': user, 'histories': histories})

def register(request):
    """Đăng ký tài khoản người dùng mới"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        # Kiểm tra xem email hoặc số điện thoại đã tồn tại chưa
        if email and User.objects.filter(email=email).exists():
            messages.error(request, 'Email đã được sử dụng!')
            return redirect('user_register')
        
        if User.objects.filter(phone_number=phone).exists():
            messages.error(request, 'Số điện thoại đã được sử dụng!')
            return redirect('user_register')
        
        # Tạo người dùng mới
        user = User(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            phone_number=phone,
            password=make_password(password),
            role='customer'
        )
        user.save()
        
        messages.success(request, 'Đăng ký thành công! Bạn có thể đăng nhập ngay bây giờ.')
        return redirect('user_login')
    
    return render(request, 'user/register.html')

def login_view(request):
    """Đăng nhập người dùng"""
    # Nếu người dùng đã đăng nhập, chuyển hướng đến trang chủ của webuser
    if 'user_id' in request.session:
        if request.session.get('user_role') == 'customer':
            return redirect('user_index')
        elif request.session.get('user_role') == 'admin':
            return redirect('/webadmin/admin-home')
            
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        
        # Tìm kiếm người dùng theo email hoặc số điện thoại
        user = None
        if '@' in identifier:
            try:
                user = User.objects.get(email=identifier, role='customer')
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(phone_number=identifier, role='customer')
            except User.DoesNotExist:
                pass
        
        # Kiểm tra mật khẩu
        if user and check_password(password, user.password):
            request.session['user_id'] = str(user.id)
            request.session['user_name'] = user.name
            request.session['user_role'] = user.role
            return redirect('user_index')
        else:
            messages.error(request, 'Email/số điện thoại hoặc mật khẩu không đúng!')
    
    return render(request, 'user/login.html')

def logout_view(request):
    """Đăng xuất người dùng"""
    # Xóa thông tin phiên
    for key in list(request.session.keys()):
        if key != 'cart':  # Giữ lại giỏ hàng nếu cần
            del request.session[key]
    
    messages.success(request, 'Đăng xuất thành công!')
    return redirect('user_login')