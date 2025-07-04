from django.shortcuts import render
from webadmin.models import History
from account.models import User
from webadmin.models import Payment  # import bảng payment
from datetime import datetime
from django.core.paginator import Paginator

def history_view(request):
    user = None
    user_id = request.session.get('user_id')
    histories = []

    if user_id:
        try:
            user = User.objects.get(id=user_id)
            histories = History.objects.filter(vehicle__user=user).order_by('-time_in')
        except User.DoesNotExist:
            pass

    history_data = []
    for history in histories:
        hours, minutes = history.get_parking_duration()
        payment = Payment.objects.filter(history=history).first()

        if history.time_out:
            if payment:
                fee_display = payment.fee
                if payment.status:
                    status = "Đã thanh toán"
                else:
                    status = "Chưa thanh toán"
            else:
                # Tính phí tạm nếu chưa thanh toán
                fee_display = history.calculate_fee()
                status = "Chưa thanh toán"
        else:
            fee_display = "Chưa tính"
            status = "Đang đỗ"

        history_data.append({
            'id': history.id,
            'license_plate': history.vehicle.license_plate,
            'time_in': history.time_in,
            'time_out': history.time_out,
            'duration': f"{hours} giờ {minutes} phút" if history.time_out else "Đang đỗ",
            'fee': fee_display,
            'status': status,
        })
        
        

    # Phân trang
    page_number = request.GET.get('page', 1)
    paginator = Paginator(history_data, 4)  # 4 bản ghi mỗi trang
    page_obj = paginator.get_page(page_number)
    context = {
        'user': user,
        'histories': history_data,
        'page_obj': page_obj,
    }
    return render(request, 'history/history2.html', context)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.timezone import localtime

def search_history_ajax(request):
    if request.method == 'GET':
        query = request.GET.get('query', '')
        status_filter = request.GET.get('status', 'all')
        page_number = int(request.GET.get('page', 1))
        user_id = request.session.get('user_id')
        
        if not user_id:
            return JsonResponse({'histories': [], 'pagination_html': ''})

        try:
            user = User.objects.get(id=user_id)
            histories = History.objects.filter(vehicle__user=user).order_by('-time_in')
            
            # Áp dụng bộ lọc tìm kiếm
            if query:
                histories = histories.filter(vehicle__license_plate__icontains=query)
            
            # Áp dụng bộ lọc trạng thái
            if status_filter != 'all':
                if status_filter == 'parking':
                    histories = histories.filter(time_out__isnull=True)
                elif status_filter == 'unpaid':
                    # Lấy những lịch sử đã có time_out và có payment nhưng payment.status=False
                    unpaid_ids = Payment.objects.filter(status=False).values_list('history_id', flat=True)
                    histories = histories.filter(time_out__isnull=False, id__in=unpaid_ids)
                elif status_filter == 'paid':
                    paid_ids = Payment.objects.filter(status=True).values_list('history_id', flat=True)
                    histories = histories.filter(id__in=paid_ids)


            paginator = Paginator(histories, 4)
            page_obj = paginator.get_page(page_number)

            history_data = []
            for history in page_obj:
                hours, minutes = history.get_parking_duration()
                payment = Payment.objects.filter(history=history).first()

                if history.time_out:
                    if payment:
                        fee_display = f"{int(payment.fee):,} VNĐ"
                        if payment.status:
                            status = "Đã thanh toán"
                        else:
                            status = "Chưa thanh toán"
                    
                    duration = f"{hours} giờ {minutes} phút"
                else:
                    status = "Đang đỗ"
                    fee_display = "Chưa tính"
                    duration = "Đang đỗ"

                history_data.append({
                    'license_plate': history.vehicle.license_plate,
                    'time_in': history.time_in.strftime('%d/%m/%Y %H:%M'),
                    'time_out': history.time_out.strftime('%d/%m/%Y %H:%M') if history.time_out else "-",
                    'duration': duration,
                    'fee': fee_display,
                    'status': status,
                })

            pagination_html = render_to_string('history/_pagination.html', {
                'page_obj': page_obj,
                'query': query,
                'status_filter': status_filter,
            }) if paginator.num_pages > 1 else ""

            return JsonResponse({
                'histories': history_data,
                'pagination_html': pagination_html,
                'current_page': page_obj.number,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_pages': paginator.num_pages,
            })

        except User.DoesNotExist:
            pass

    return JsonResponse({'histories': [], 'pagination_html': ''})