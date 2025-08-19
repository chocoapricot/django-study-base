from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.staff.models import Staff
from apps.client.models import Client
from apps.contract.models import ClientContract, StaffContract
from apps.connect.models import ConnectStaff, ConnectClient

@login_required
def home(request):
    staff_count = Staff.objects.count()
    approved_staff_count = ConnectStaff.objects.filter(status='approved').count()

    client_count = Client.objects.count()
    approved_client_count = ConnectClient.objects.filter(status='approved').count()

    # 契約情報の取得
    client_contract_count = ClientContract.objects.count()
    current_client_contracts = ClientContract.objects.filter(is_active=True).count()
    recent_client_contracts = ClientContract.objects.select_related('client').filter(
        is_active=True
    ).order_by('-created_at')[:5]

    staff_contract_count = StaffContract.objects.count()
    current_staff_contracts = StaffContract.objects.filter(is_active=True).count()
    recent_staff_contracts = StaffContract.objects.select_related('staff').filter(
        is_active=True
    ).order_by('-created_at')[:5]

    context = {
        'staff_count': staff_count,
        'approved_staff_count': approved_staff_count,
        'client_count': client_count,
        'approved_client_count': approved_client_count,

        'client_contract_count': client_contract_count,
        'current_client_contracts': current_client_contracts,
        'recent_client_contracts': recent_client_contracts,
        'staff_contract_count': staff_contract_count,
        'current_staff_contracts': current_staff_contracts,
        'recent_staff_contracts': recent_staff_contracts,
    }

    return render(request, 'home/home.html', context)
