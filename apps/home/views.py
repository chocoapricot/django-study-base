from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company
from apps.contract.models import ClientContract, StaffContract
from apps.connect.models import (
    ConnectStaff, ConnectClient, MynumberRequest, ProfileRequest,
    BankRequest, ContactRequest, ConnectInternationalRequest, DisabilityRequest
)
from apps.master.models import Information
from django.utils import timezone
from django.db.models import Q

def get_filtered_informations(user):
    """
    ユーザーに基づいてフィルタリングされたお知らせを取得する
    """
    today = timezone.now().date()
    
    # 基本的な絞り込み
    base_query = Information.objects.filter(
        (Q(start_date__lte=today) | Q(start_date__isnull=True)),
        (Q(end_date__gte=today) | Q(end_date__isnull=True)),
    )

    # ユーザーの属性に応じてフィルタリング
    company_info = Company.objects.first()
    
    # 接続済みの法人番号リストを取得
    approved_staff_corporate_numbers = ConnectStaff.objects.filter(
        email=user.email, status='approved'
    ).values_list('corporate_number', flat=True)
    
    approved_client_corporate_numbers = ConnectClient.objects.filter(
        email=user.email, status='approved'
    ).values_list('corporate_number', flat=True)
    
    # OR条件を構築
    filter_conditions = Q()

    # 会社向けお知らせ
    if company_info:
        filter_conditions |= Q(target='company', corporation_number=company_info.corporate_number)

    # スタッフ向けお知らせ
    if approved_staff_corporate_numbers:
        filter_conditions |= Q(target='staff', corporation_number__in=list(approved_staff_corporate_numbers))

    # クライアント向けお知らせ
    if approved_client_corporate_numbers:
        filter_conditions |= Q(target='client', corporation_number__in=list(approved_client_corporate_numbers)) 

    return base_query.filter(filter_conditions)

@login_required
def home(request):
    all_informations = get_filtered_informations(request.user).order_by('-start_date')
    information_list = all_informations[:5]
    information_count = all_informations.count()
    
    # お知らせに会社名を付与
    corporation_numbers = [info.corporation_number for info in information_list if info.corporation_number]
    if corporation_numbers:
        companies = Company.objects.filter(corporate_number__in=corporation_numbers).in_bulk(field_name='corporate_number')
        for info in information_list:
            if info.corporation_number in companies:
                info.company_name = companies[info.corporation_number].name

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
        'information_count': information_count,
    }

    return render(request, 'home/home.html', context)


from django.shortcuts import get_object_or_404

@login_required
def information_list(request):
    information_list = get_filtered_informations(request.user).order_by('-start_date')
    
    # お知らせに会社名を付与
    corporation_numbers = [info.corporation_number for info in information_list if info.corporation_number]
    if corporation_numbers:
        companies = Company.objects.filter(corporate_number__in=corporation_numbers).in_bulk(field_name='corporate_number')
        for info in information_list:
            if info.corporation_number in companies:
                info.company_name = companies[info.corporation_number].name
    
    paginator = Paginator(information_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'home/information_list.html', context)

@login_required
def information_detail(request, pk):
    informations = get_filtered_informations(request.user)
    information = get_object_or_404(informations, pk=pk)
    
    # お知らせに会社名を付与
    if information.corporation_number:
        try:
            company = Company.objects.get(corporate_number=information.corporation_number)
            information.company_name = company.name
        except Company.DoesNotExist:
            information.company_name = None
    
    context = {
        'information': information,
        'next': request.GET.get('next', ''),
    }
    return render(request, 'home/information_detail.html', context)