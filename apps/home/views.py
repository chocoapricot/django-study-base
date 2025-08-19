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

    contract_count = ClientContract.objects.count() + StaffContract.objects.count()

    context = {
        'staff_count': staff_count,
        'approved_staff_count': approved_staff_count,
        'client_count': client_count,
        'approved_client_count': approved_client_count,
        'contract_count': contract_count,
    }

    return render(request, 'home/home.html', context)
