from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import User  # Import User từ models trong cùng app
import uuid

def login_required(view_func):
    """
    Decorator để kiểm tra đăng nhập trong các view
    """
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.info(request, 'Vui lòng đăng nhập để tiếp tục.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    """
    Decorator để kiểm tra quyền admin trong các view
    """
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.info(request, 'Vui lòng đăng nhập để tiếp tục.')
            return redirect('login')
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Bạn không có quyền truy cập trang này.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def home(request):
    """Xử lý trang chủ của ứng dụng"""
    # Đối với URL gốc (127.0.0.1:8000), luôn chuyển hướng đến trang đăng nhập
    if not request.path.startswith('/account/'):
        return redirect('login')
        
    # Nếu người dùng đã đăng nhập, chuyển hướng tùy theo vai trò
    if 'user_id' in request.session:
        user_role = request.session.get('user_role')
        if user_role == 'admin':
            return redirect('/webadmin/admin-home')  # Trang chủ admin
        else:
            return redirect('/webuser/')  # Trang chủ người dùng
    
    # Nếu chưa đăng nhập, chuyển đến trang đăng nhập
    return redirect('login')

def login(request):
    """Xử lý đăng nhập người dùng"""
    # Kiểm tra nếu người dùng đã đăng nhập
    if 'user_id' in request.session:
        user_role = request.session.get('user_role')
        if user_role == 'admin':
            return redirect('/webadmin/admin-home')  # Trang chủ admin - corrected URL
        else:
            return redirect('/webuser/')  # Trang chủ người dùng
            
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        
        # Tìm kiếm người dùng theo email hoặc số điện thoại
        user = None
        if '@' in identifier:
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(phone_number=identifier)
            except User.DoesNotExist:
                pass
        
        # Kiểm tra mật khẩu
        if user and check_password(password, user.password):
            # Lưu thông tin vào session
            request.session['user_id'] = str(user.id)
            request.session['user_name'] = user.name
            request.session['user_role'] = user.role
            
            # Chuyển hướng dựa vào role
            if user.role == 'admin':
                return redirect('/webadmin/admin-home')  # Trang chủ admin - corrected URL
            else:
                return redirect('/webuser/')  # Trang chủ người dùng
        else:
            messages.error(request, 'Email/số điện thoại hoặc mật khẩu không đúng!')
    
    return render(request, 'account/login.html')

def register(request):
    """Đăng ký tài khoản người dùng mới"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        print(f"DEBUG: Dữ liệu đăng ký - Tên: {name}, Email: {email}, SĐT: {phone}")
        
        # Thêm xác thực dữ liệu đầu vào
        if not name or not email or not phone or not password:
            messages.error(request, 'Vui lòng điền đầy đủ thông tin!')
            return render(request, 'account/register.html')
        
        # Kiểm tra mật khẩu và xác nhận mật khẩu có khớp không
        if password != confirm_password:
            messages.error(request, 'Mật khẩu xác nhận không khớp!')
            return render(request, 'account/register.html')
        
        # Kiểm tra xem email hoặc số điện thoại đã tồn tại chưa
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email đã được sử dụng!')
            return render(request, 'account/register.html')
        
        if User.objects.filter(phone_number=phone).exists():
            messages.error(request, 'Số điện thoại đã được sử dụng!')
            return render(request, 'account/register.html')
        
        try:
            # Tạo người dùng mới
            user_id = str(uuid.uuid4())
            print(f"DEBUG: Đang tạo người dùng với ID: {user_id}")
            
            user = User(
                id=user_id,
                name=name,
                email=email,
                phone_number=phone,
                password=make_password(password),
                role='customer'  # Mặc định là người dùng thường
            )
            user.save()
            print(f"DEBUG: Đã lưu người dùng thành công với ID: {user.id}")
            
            messages.success(request, 'Đăng ký thành công! Bạn có thể đăng nhập ngay bây giờ.')
            return redirect('login')
        except Exception as e:
            print(f"DEBUG: Lỗi khi lưu người dùng: {str(e)}")
            messages.error(request, f'Đã xảy ra lỗi khi đăng ký: {str(e)}')
            return render(request, 'account/register.html')
    
    return render(request, 'account/register.html')

def logout(request):
    """Đăng xuất người dùng"""
    # Xóa thông tin phiên
    for key in list(request.session.keys()):
        if key != 'cart':  # Giữ lại giỏ hàng nếu cần
            del request.session[key]
    
    messages.success(request, 'Đăng xuất thành công!')
    return redirect('login')

@login_required
def profile(request):
    """Xem và cập nhật thông tin cá nhân"""
    if 'user_id' not in request.session:
        return redirect('login')
    
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
        
        # Cập nhật lại thông tin session
        request.session['user_name'] = user.name
        
        # Chuyển hướng dựa vào role
        if user.role == 'admin':
            return redirect('profile')
        else:
            return redirect('user_profile')
    
    return render(request, 'account/profile.html', {'user': user})

@login_required
def change_password(request):
    """Thay đổi mật khẩu người dùng"""
    if 'user_id' not in request.session:
        return redirect('login')
    
    if request.method == 'POST':
        user_id = request.session['user_id']
        user = User.objects.get(id=user_id)
        
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Kiểm tra mật khẩu hiện tại
        if not check_password(current_password, user.password):
            messages.error(request, 'Mật khẩu hiện tại không đúng!')
            return redirect('change_password')
        
        # Kiểm tra mật khẩu mới và xác nhận
        if new_password != confirm_password:
            messages.error(request, 'Mật khẩu mới và xác nhận không khớp!')
            return redirect('change_password')
        
        # Cập nhật mật khẩu mới
        user.password = make_password(new_password)
        user.save()
        
        messages.success(request, 'Mật khẩu đã được thay đổi thành công!')
        
        # Chuyển hướng dựa vào role
        if user.role == 'admin':
            return redirect('profile')
        else:
            return redirect('user_profile')
    
    return render(request, 'account/change_password.html')