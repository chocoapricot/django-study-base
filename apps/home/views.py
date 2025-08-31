from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.staff.models import Staff
from apps.client.models import Client
from apps.contract.models import ClientContract, StaffContract
from apps.connect.models import (
    ConnectStaff, ConnectClient, MynumberRequest, ProfileRequest,
    BankRequest, ContactRequest, ConnectInternationalRequest, DisabilityRequest
)
from apps.information.models import InformationFromCompany
from django.utils import timezone
from django.db.models import Q

@login_required
def home(request):
    today = timezone.now().date()
    information_list = InformationFromCompany.objects.filter(
        (Q(start_date__lte=today) | Q(start_date__isnull=True)),
        (Q(end_date__gte=today) | Q(end_date__isnull=True)),
    ).order_by('-start_date')[:5]

    staff_count = Staff.objects.count()
    approved_staff_count = ConnectStaff.objects.filter(status='approved').count()

    client_count = Client.objects.count()
    approved_client_count = ConnectClient.objects.filter(status='approved').count()

    # Get all ConnectStaff ids that have pending requests
    pending_mynumber_cs_ids = MynumberRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
    pending_profile_cs_ids = ProfileRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
    pending_bank_cs_ids = BankRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
    pending_contact_cs_ids = ContactRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
    pending_international_cs_ids = ConnectInternationalRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)
    pending_disability_cs_ids = DisabilityRequest.objects.filter(status='pending').values_list('connect_staff_id', flat=True)

    all_pending_cs_ids = set()
    all_pending_cs_ids.update(pending_mynumber_cs_ids)
    all_pending_cs_ids.update(pending_profile_cs_ids)
    all_pending_cs_ids.update(pending_bank_cs_ids)
    all_pending_cs_ids.update(pending_contact_cs_ids)
    all_pending_cs_ids.update(pending_international_cs_ids)
    all_pending_cs_ids.update(pending_disability_cs_ids)

    # Get the emails of these ConnectStaff objects
    pending_emails = ConnectStaff.objects.filter(id__in=list(all_pending_cs_ids)).values_list('email', flat=True)

    # Count the number of Staff with these emails
    staff_request_count = Staff.objects.filter(email__in=pending_emails).distinct().count()

    context = {
        'staff_count': staff_count,
        'approved_staff_count': approved_staff_count,
        'client_count': client_count,
        'approved_client_count': approved_client_count,
        'staff_request_count': staff_request_count,
        'information_list': information_list,
    }

    return render(request, 'home/home.html', context)
