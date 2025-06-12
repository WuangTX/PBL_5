from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from webadmin.models import User, Vehicle
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
from django.conf import settings

def register_view(request):
    """Trang đăng ký người dùng"""
    user = None
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

    if request.method == 'POST':
        full_name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        # Kiểm tra email đã tồn tại
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email đã được sử dụng'}, status=400)

        # Kiểm tra phone đã tồn tại
        if User.objects.filter(phone_number=phone).exists():
            return JsonResponse({'error': 'Số điện thoại đã được sử dụng'}, status=400)

        # Tạo người dùng mới
        user = User.objects.create(
            name=full_name,
            email=email,
            phone_number=phone,
            password=make_password(password)
        )
        return JsonResponse({'message': 'Đăng ký thành công'})
    
    context = {
        'user': user,
    }
    return render(request, 'register/registerUser.html', context)


@csrf_exempt
def check_user_exists(request):
    """API kiểm tra email/phone đã tồn tại"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            field_type = data.get('type')  # 'email' hoặc 'phone'
            value = data.get('value', '').strip()
            
            if not value:
                return JsonResponse({'error': 'Thiếu giá trị'}, status=400)
            
            if field_type == 'email':
                exists = User.objects.filter(email=value).exists()
                message = 'Email đã được sử dụng' if exists else 'Email có thể sử dụng'
            elif field_type == 'phone':
                exists = User.objects.filter(phone_number=value).exists()
                message = 'Số điện thoại đã được sử dụng' if exists else 'Số điện thoại có thể sử dụng'
            else:
                return JsonResponse({'error': 'Loại kiểm tra không hợp lệ'}, status=400)
            
            return JsonResponse({
                'exists': exists,
                'message': message
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Dữ liệu JSON không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Lỗi server: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Phương thức không được hỗ trợ'}, status=405)