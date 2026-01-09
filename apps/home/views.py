from django.shortcuts import render, redirect
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
from apps.common.constants import Constants

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
        filter_conditions |= Q(target='20', corporation_number=company_info.corporate_number)

    # スタッフ向けお知らせ
    if approved_staff_corporate_numbers:
        filter_conditions |= Q(target='1', corporation_number__in=list(approved_staff_corporate_numbers))

    # クライアント向けお知らせ
    if approved_client_corporate_numbers:
        filter_conditions |= Q(target='10', corporation_number__in=list(approved_client_corporate_numbers))

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

def start_page(request):
    """
    ログイン不要なスタートページ
    """
    return render(request, 'home/start_page.html')


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .setup_utils import create_setup_task, get_setup_task, start_setup_async


@require_http_methods(["POST"])
def setup_start(request):
    """
    セットアップを開始し、タスクIDを返す
    """
    task_id = create_setup_task()
    return JsonResponse({'task_id': task_id})


@require_http_methods(["POST"])
def setup_process(request, task_id):
    """
    セットアップ処理を非同期で実行
    """
    task = get_setup_task(task_id)
    if not task:
        return JsonResponse({'error': '無効なタスクIDです'}, status=400)
    
    # 非同期でセットアップを開始
    start_setup_async(task_id)
    
    return JsonResponse({'status': 'started'})


@require_http_methods(["GET"])
def setup_progress(request, task_id):
    """
    セットアップの進捗状況を返す
    """
    task = get_setup_task(task_id)
    if not task:
        return JsonResponse({'error': '無効なタスクIDです'}, status=400)
    
    return JsonResponse(task.to_dict())


from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from apps.staff.models import Staff
from apps.client.models import Client, ClientDepartment, ClientUser, ClientContacted, ClientFile
from apps.connect.models import (
    ConnectStaff, ConnectClient, ConnectStaffAgree,
    MynumberRequest, ProfileRequest, BankRequest,
    ContactRequest, ConnectInternationalRequest, DisabilityRequest
)
from apps.contract.models import (
    ContractAssignment, ClientContract, StaffContract,
    ClientContractNumber, StaffContractNumber, StaffContractTeishokubi,
    ClientContractPrint, StaffContractPrint, ContractAssignmentConfirm,
    ContractAssignmentHaken, ContractAssignmentHakenPrint,
)
from apps.kintai.models import (
    StaffTimesheet, StaffTimecard, StaffTimerecord, StaffTimerecordBreak
)
from apps.system.logs.models import MailLog, AppLog, AccessLog
from apps.accounts.models import MyUser
from apps.profile.models import StaffProfile, StaffProfileQualification, StaffProfileSkill, StaffProfileMynumber, StaffProfileInternational, StaffProfileBank, StaffProfileDisability, StaffProfileContact

@require_POST
@user_passes_test(lambda u: u.is_superuser)
def delete_application_data(request):
    """
    マスターデータと管理者アカウントを除く、すべてのアプリケーションデータを削除する。
    """
    try:
        with transaction.atomic():
            # 外部キー制約を考慮し、依存関係の末端から削除していく

            # 1. 契約アサイン関連 (ContractAssignmentがClient/StaffContractを参照)
            ContractAssignmentHakenPrint.objects.all().delete()
            ContractAssignmentHaken.objects.all().delete()
            ContractAssignmentConfirm.objects.all().delete()
            ContractAssignment.objects.all().delete()

            # 2. 契約書印刷履歴
            ClientContractPrint.objects.all().delete()
            StaffContractPrint.objects.all().delete()

            # 3. 勤怠データ (StaffTimesheet/StaffTimecardがStaffContractを参照)
            StaffTimerecordBreak.objects.all().delete()
            StaffTimerecord.objects.all().delete()
            StaffTimecard.objects.all().delete()
            StaffTimesheet.objects.all().delete()

            # 4. 契約本体
            ClientContract.objects.all().delete()
            StaffContract.objects.all().delete()

            # 5. 接続申請関連 (ConnectStaffがStaffを参照)
            MynumberRequest.objects.all().delete()
            ProfileRequest.objects.all().delete()
            BankRequest.objects.all().delete()
            ContactRequest.objects.all().delete()
            ConnectInternationalRequest.objects.all().delete()
            DisabilityRequest.objects.all().delete()
            ConnectStaffAgree.objects.all().delete()
            ConnectStaff.objects.all().delete()
            ConnectClient.objects.all().delete()

            # 6. クライアント関連データ (ClientUserなどがClientを参照)
            ClientFile.objects.all().delete()
            ClientContacted.objects.all().delete()
            ClientUser.objects.all().delete()
            ClientDepartment.objects.all().delete()
            Client.objects.all().delete()

            # 7. スタッフプロフィール関連 (StaffProfileがUserを参照)
            StaffProfileQualification.objects.all().delete()
            StaffProfileSkill.objects.all().delete()
            StaffProfileMynumber.objects.all().delete()
            StaffProfileInternational.objects.all().delete()
            StaffProfileBank.objects.all().delete()
            StaffProfileDisability.objects.all().delete()
            StaffProfileContact.objects.all().delete()
            StaffProfile.objects.all().delete()

            # 8. スタッフ本体
            Staff.objects.all().delete()

            # 9. ログデータ
            MailLog.objects.all().delete()
            AppLog.objects.all().delete()
            AccessLog.objects.all().delete()

            # 10. 独立したテーブル
            ClientContractNumber.objects.all().delete()
            StaffContractNumber.objects.all().delete()
            StaffContractTeishokubi.objects.all().delete()

            # 11. 管理者以外のアカウント
            MyUser.objects.filter(is_superuser=False).delete()

        messages.success(request, "アプリケーションデータを削除しました。")
    except Exception as e:
        messages.error(request, f"データの削除中にエラーが発生しました: {e}")

    return redirect('home:start_page')
