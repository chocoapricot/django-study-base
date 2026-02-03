from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from apps.staff.models import Staff, StaffInternational
from apps.staff.models_other import StaffFlag
from apps.client.models import Client, ClientFlag
from apps.company.models import Company, CompanyUser
from apps.contract.models import (
    ClientContract, StaffContract, ContractAssignment, StaffContractTeishokubi,
    ContractClientFlag, ContractStaffFlag, ContractAssignmentFlag
)
from apps.connect.models import (
    ConnectStaff, ConnectClient, MynumberRequest, ProfileRequest,
    BankRequest, ContactRequest, ConnectInternationalRequest, DisabilityRequest
)
from apps.master.models import (
    Information, UserParameter, StaffContactType, ClientContactType,
    StaffTag, ClientTag
)
from apps.staff.models_inquiry import StaffInquiry
from apps.staff.models_payroll import StaffPayroll
from apps.profile.models import StaffProfileMynumber, StaffProfileBank
from django.utils import timezone
from django.db.models import Q, Exists, OuterRef, Subquery
from apps.common.constants import Constants
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from apps.staff.models import StaffContactSchedule
from apps.client.models import ClientContactSchedule
import jpholiday

@login_required
def contact_schedule_summary(request):
    """
    連絡予定のサマリ画面
    昨日から1週間の日別件数と、1ヶ月以内の残り件数を表示する
    """
    # 閲覧権限チェック
    has_staff_perm = request.user.has_perm('staff.view_staffcontactschedule')
    has_client_perm = request.user.has_perm('client.view_clientcontactschedule')
    
    if not (has_staff_perm or has_client_perm):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    jp_weeks = ['月', '火', '水', '木', '金', '土', '日']
    
    # 昨日より前（過去分）の件数
    past_staff_count = StaffContactSchedule.objects.filter(contact_date__lt=yesterday).count() if has_staff_perm else 0
    past_client_count = ClientContactSchedule.objects.filter(contact_date__lt=yesterday).count() if has_client_perm else 0

    daily_schedules = []
    # 昨日から10日間
    for i in range(10):
        current_date = yesterday + timedelta(days=i)
        staff_count = StaffContactSchedule.objects.filter(contact_date=current_date).count() if has_staff_perm else 0
        client_count = ClientContactSchedule.objects.filter(contact_date=current_date).count() if has_client_perm else 0
        
        is_holiday = jpholiday.is_holiday(current_date)
        holiday_name = None
        if is_holiday:
            try:
                holiday_name = jpholiday.is_holiday_name(current_date)
            except Exception:
                pass

        daily_schedules.append({
            'date': current_date,
            'day_of_week': jp_weeks[current_date.weekday()],
            'staff_count': staff_count,
            'client_count': client_count,
            'is_today': current_date == today,
            'is_yesterday': current_date == yesterday,
            'is_holiday': is_holiday,
            'holiday_name': holiday_name,
            'weekday_num': current_date.weekday(), # 5:土, 6:日
        })
    
    # 10日後以降から昨日から1ヶ月まで
    start_of_other = yesterday + timedelta(days=10)
    one_month_later = yesterday + relativedelta(months=1)
    
    other_staff_count = StaffContactSchedule.objects.filter(
        contact_date__gte=start_of_other,
        contact_date__lte=one_month_later
    ).count() if has_staff_perm else 0
    
    other_client_count = ClientContactSchedule.objects.filter(
        contact_date__gte=start_of_other,
        contact_date__lte=one_month_later
    ).count() if has_client_perm else 0

    # 10日間の予定詳細リストを取得（過去分も含む）
    staff_schedules = []
    if has_staff_perm:
        staff_schedules = StaffContactSchedule.objects.filter(
            contact_date__lt=start_of_other
        ).select_related('staff').order_by('contact_date', 'id')
        for s in staff_schedules:
            s.day_of_week = jp_weeks[s.contact_date.weekday()]
            s.weekday_num = s.contact_date.weekday()
            s.is_holiday = jpholiday.is_holiday(s.contact_date)
            try:
                s.holiday_name = jpholiday.is_holiday_name(s.contact_date)
            except Exception:
                s.holiday_name = None

    client_schedules = []
    if has_client_perm:
        client_schedules = ClientContactSchedule.objects.filter(
            contact_date__lt=start_of_other
        ).select_related('client').order_by('contact_date', 'id')
        for s in client_schedules:
            s.day_of_week = jp_weeks[s.contact_date.weekday()]
            s.weekday_num = s.contact_date.weekday()
            s.is_holiday = jpholiday.is_holiday(s.contact_date)
            try:
                s.holiday_name = jpholiday.is_holiday_name(s.contact_date)
            except Exception:
                s.holiday_name = None

    # 1ヶ月以内の全予定数
    total_scheduled_count = StaffContactSchedule.objects.filter(
        contact_date__lte=one_month_later
    ).count() if has_staff_perm else 0
    if has_client_perm:
        total_scheduled_count += ClientContactSchedule.objects.filter(
            contact_date__lte=one_month_later
        ).count()

    context = {
        'past_staff_count': past_staff_count,
        'past_client_count': past_client_count,
        'daily_schedules': daily_schedules,
        'other_staff_count': other_staff_count,
        'other_client_count': other_client_count,
        'staff_schedules': staff_schedules,
        'client_schedules': client_schedules,
        'today': today,
        'yesterday': yesterday,
        'one_month_later': one_month_later,
        'start_of_other': start_of_other,
        'has_staff_perm': has_staff_perm,
        'has_client_perm': has_client_perm,
        'total_scheduled_count': total_scheduled_count,
    }
    return render(request, 'home/contact_schedule_summary.html', context)

def get_filtered_informations(user):
    """
    ユーザーに基づいてフィルタリングされたお知らせを取得する
    """
    today = timezone.localdate()
    
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
    User = get_user_model()
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

    context = {
        'information_list': information_list,
        'information_count': information_count,
        'staff_count': 0,
        'approved_staff_count': 0,
        'client_count': 0,
        'approved_client_count': 0,
        'client_contract_count': 0,
        'staff_contract_count': 0,
        'staff_payroll_info_unregistered_count': 0,
        'expiring_staff_international_count': 0,
        'staff_request_count': 0,
        'has_staff_perm': False,
        'has_client_perm': False,
        'staff_schedules_today': 0,
        'staff_schedules_yesterday': 0,
        'client_schedules_today': 0,
        'client_schedules_yesterday': 0,
        'pending_connect_staff_count': 0,
        'pending_connect_client_count': 0,
        'has_inquiry_perm': False,
        'unanswered_inquiry_count': 0,
        'has_contract_assignment_perm': False,
        'unconfirmed_staff_contract_extension_count': 0,
        'has_view_client_contract_perm': False,
        'teishokubi_deadline_count': 0,
        'personal_teishokubi_deadline_count': 0,
        'total_flag_count': 0,
    }

    today = timezone.localdate()

    # 登録状況の計算
    if request.user.has_perm('company.view_registration_status'):
        staff_count = Staff.objects.count()
        approved_staff_count = ConnectStaff.objects.filter(status='approved').count()
        client_count = Client.objects.count()
        approved_client_count = ConnectClient.objects.filter(status='approved').count()

        client_contract_count = ClientContract.objects.filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).count()
        staff_contract_count = StaffContract.objects.filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).count()

        context.update({
            'staff_count': staff_count,
            'approved_staff_count': approved_staff_count,
            'client_count': client_count,
            'approved_client_count': approved_client_count,
            'client_contract_count': client_contract_count,
            'staff_contract_count': staff_contract_count,
        })

    # 業務サマリの計算
    if request.user.has_perm('company.view_business_summary'):
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

        # 連絡予定件数
        yesterday = today - timedelta(days=1)

        has_staff_perm = request.user.has_perm('staff.view_staffcontactschedule')
        has_client_perm = request.user.has_perm('client.view_clientcontactschedule')

        staff_schedules_today = 0
        staff_schedules_yesterday = 0
        client_schedules_today = 0
        client_schedules_yesterday = 0

        if has_staff_perm:
            staff_schedules_today = StaffContactSchedule.objects.filter(contact_date=today).count()
            staff_schedules_yesterday = StaffContactSchedule.objects.filter(contact_date=yesterday).count()

        if has_client_perm:
            client_schedules_today = ClientContactSchedule.objects.filter(contact_date=today).count()
            client_schedules_yesterday = ClientContactSchedule.objects.filter(contact_date=yesterday).count()

        has_inquiry_perm = request.user.has_perm('staff.view_staffinquiry')
        unanswered_inquiry_count = 0
        if has_inquiry_perm:
            # 会社ユーザーまたは管理者であるかを判定
            is_company_or_admin = request.user.is_superuser or CompanyUser.objects.filter(email=request.user.email).exists()

            if is_company_or_admin:
                # 自分が担当者の問い合わせ or 管理者
                if request.user.is_superuser:
                    inquiries_qs = StaffInquiry.objects.all()
                else:
                    # CompanyUserとしての権限
                    my_companies = CompanyUser.objects.filter(email=request.user.email).values_list('corporate_number', flat=True)
                    inquiries_qs = StaffInquiry.objects.filter(corporate_number__in=my_companies)

                unanswered_inquiry_count = inquiries_qs.filter(status='open', last_message_by='staff').count()

        # スタッフ契約延長未確認件数
        unconfirmed_staff_contract_extension_count = 0
        has_contract_assignment_perm = request.user.has_perm('contract.view_contractassignment')
        if has_contract_assignment_perm:
            unconfirmed_staff_contract_extension_count = ContractAssignment.objects.filter(
                assignment_end_date__gte=today,
                assignment_confirm__isnull=True
            ).count()

        # 警告日数の取得
        try:
            residence_period_warning_days = UserParameter.objects.get(key='RESIDENCE_PERIOD_WARNING_DAYS').get_number_value()
            if residence_period_warning_days is None:
                residence_period_warning_days = 30
        except UserParameter.DoesNotExist:
            residence_period_warning_days = 30

        try:
            personal_teishokubi_warning_days = UserParameter.objects.get(key='PERSONAL_TEISHOKUBI_WARNING_DAYS').get_number_value()
            if personal_teishokubi_warning_days is None:
                personal_teishokubi_warning_days = 60
        except UserParameter.DoesNotExist:
            personal_teishokubi_warning_days = 60

        try:
            office_teishokubi_warning_days = UserParameter.objects.get(key='OFFICE_TEISHOKUBI_WARNING_DAYS').get_number_value()
            if office_teishokubi_warning_days is None:
                office_teishokubi_warning_days = 60
        except UserParameter.DoesNotExist:
            office_teishokubi_warning_days = 60

        # 外国籍スタッフの在留資格期限切れ件数
        expiring_staff_international_count = 0
        if request.user.has_perm('staff.view_staffinternational'):
            residence_warning_date = today + timedelta(days=residence_period_warning_days)
            expiring_staff_international_count = StaffInternational.objects.filter(
                staff__employee_no__isnull=False,
                residence_period_to__lte=residence_warning_date
            ).exclude(staff__employee_no='').count()

        # 事業所抵触日期限の件数
        teishokubi_deadline_count = 0
        has_view_client_contract_perm = request.user.has_perm('contract.view_clientcontract')
        if has_view_client_contract_perm:
            office_teishokubi_warning_date = today + timedelta(days=office_teishokubi_warning_days)
            teishokubi_deadline_count = ClientContract.objects.filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True),
                start_date__lte=today,
                client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
                haken_info__haken_office__haken_jigyosho_teishokubi__gte=today,
                haken_info__haken_office__haken_jigyosho_teishokubi__lte=office_teishokubi_warning_date,
            ).count()

        # 個人抵触日期限の件数
        personal_teishokubi_deadline_count = 0
        if has_view_client_contract_perm:
            from django.db.models import Exists, OuterRef
            personal_teishokubi_warning_date = today + timedelta(days=personal_teishokubi_warning_days)

            active_assignments = ContractAssignment.objects.filter(
                Q(assignment_end_date__gte=today) | Q(assignment_end_date__isnull=True),
                staff_email=OuterRef('staff_email'),
                client_corporate_number=OuterRef('client_corporate_number'),
                client_contract__haken_info__haken_unit__name=OuterRef('organization_name'),
            )

            personal_teishokubi_deadline_count = StaffContractTeishokubi.objects.filter(
                conflict_date__gte=today,
                conflict_date__lte=personal_teishokubi_warning_date
            ).annotate(has_active_assignment=Exists(active_assignments)).filter(has_active_assignment=True).count()

        # フラッグ総数 (対応残: 有効なステータスのもののみカウント)
        from apps.master.models_other import FlagStatus
        active_status_ids = FlagStatus.objects.filter(is_active=True).values_list('id', flat=True)

        total_flag_count = (
            StaffFlag.objects.filter(flag_status_id__in=active_status_ids).count() +
            ClientFlag.objects.filter(flag_status_id__in=active_status_ids).count() +
            ContractClientFlag.objects.filter(flag_status_id__in=active_status_ids).count() +
            ContractStaffFlag.objects.filter(flag_status_id__in=active_status_ids).count() +
            ContractAssignmentFlag.objects.filter(flag_status_id__in=active_status_ids).count()
        )

        # スタッフ給与情報未登録件数
        staff_payroll_info_unregistered_count = 0
        if request.user.has_perm('staff.view_staff'):
            from django.db.models import Subquery, OuterRef, Exists
            # Staff に対応する User の pk を Subquery で取得
            user_pk_subquery = User.objects.filter(email=OuterRef('email')).values('pk')[:1]

            # 各種情報が存在するかどうかをチェックする Subquery
            mynumber_exists = StaffProfileMynumber.objects.filter(user_id=OuterRef('user_id'))
            bank_exists = StaffProfileBank.objects.filter(user_id=OuterRef('user_id'))
            payroll_exists = StaffPayroll.objects.filter(staff_id=OuterRef('pk'))

            staff_payroll_info_unregistered_count = Staff.objects.annotate(
                user_id=Subquery(user_pk_subquery)
            ).filter(
                employee_no__isnull=False
            ).exclude(
                employee_no=''
            ).annotate(
                has_mynumber=Exists(mynumber_exists),
                has_bank=Exists(bank_exists),
                has_payroll=Exists(payroll_exists)
            ).filter(
                Q(has_mynumber=False) | Q(has_bank=False) | Q(has_payroll=False)
            ).count()

        context.update({
            'staff_payroll_info_unregistered_count': staff_payroll_info_unregistered_count,
            'expiring_staff_international_count': expiring_staff_international_count,
            'staff_request_count': staff_request_count,
            'has_staff_perm': has_staff_perm,
            'has_client_perm': has_client_perm,
            'staff_schedules_today': staff_schedules_today,
            'staff_schedules_yesterday': staff_schedules_yesterday,
            'client_schedules_today': client_schedules_today,
            'client_schedules_yesterday': client_schedules_yesterday,
            'pending_connect_staff_count': ConnectStaff.objects.filter(status=Constants.CONNECT_STATUS.PENDING).count(),
            'pending_connect_client_count': ConnectClient.objects.filter(status=Constants.CONNECT_STATUS.PENDING).count(),
            'has_inquiry_perm': has_inquiry_perm,
            'unanswered_inquiry_count': unanswered_inquiry_count,
            'has_contract_assignment_perm': has_contract_assignment_perm,
            'unconfirmed_staff_contract_extension_count': unconfirmed_staff_contract_extension_count,
            'has_view_client_contract_perm': has_view_client_contract_perm,
            'teishokubi_deadline_count': teishokubi_deadline_count,
            'personal_teishokubi_deadline_count': personal_teishokubi_deadline_count,
            'total_flag_count': total_flag_count,
        })

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

from apps.staff.models import Staff, StaffContactSchedule
from apps.client.models import Client, ClientDepartment, ClientUser, ClientContacted, ClientFile, ClientContactSchedule
from apps.company.models import CompanyDepartment, CompanyUser
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
from apps.staff.models_inquiry import StaffInquiry, StaffInquiryMessage

def start_page(request):
    """
    ログイン不要なスタートページ
    """
    models_to_delete = [
        # 契約
        ContractAssignment, ClientContract, StaffContract,
        StaffContactSchedule, ClientContactSchedule,
        ClientContractNumber, StaffContractNumber, StaffContractTeishokubi,
        ClientContractPrint, StaffContractPrint, ContractAssignmentConfirm,
        ContractAssignmentHaken, ContractAssignmentHakenPrint,
        # 勤怠
        StaffTimesheet, StaffTimecard, StaffTimerecord, StaffTimerecordBreak,
        # 接続
        ConnectStaff, ConnectClient, ConnectStaffAgree,
        MynumberRequest, ProfileRequest, BankRequest,
        ContactRequest, ConnectInternationalRequest, DisabilityRequest,
        # クライアント
        Client, ClientDepartment, ClientUser, ClientContacted, ClientFile,
        # 自社
        CompanyDepartment, CompanyUser,
        # スタッフ
        Staff,
        # プロフィール
        StaffProfile, StaffProfileQualification, StaffProfileSkill, StaffProfileMynumber,
        StaffProfileInternational, StaffProfileBank, StaffProfileDisability, StaffProfileContact,
        # システム
        MailLog, AppLog, AccessLog,
        # アカウント
        MyUser,
        # 問い合わせ
        StaffInquiry, StaffInquiryMessage,
    ]

    # verbose_nameのリストを作成し、重複を除いてソート
    deleted_data_list = sorted(list(set([model._meta.verbose_name for model in models_to_delete])))
    deleted_data_list.append('ファイル')  # アップロードされたファイルも削除対象

    context = {
        'deleted_data_list': deleted_data_list,
    }
    return render(request, 'home/start_page.html', context)


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
from apps.staff.models import Staff, StaffContactSchedule
from apps.client.models import (
    Client, ClientDepartment, ClientUser, ClientContacted, ClientFile,
    ClientContactSchedule
)
from apps.company.models import CompanyDepartment, CompanyUser
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
from apps.staff.models_inquiry import StaffInquiry, StaffInquiryMessage
import os
import shutil

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

            # 5.5 問い合わせデータ (StaffInquiryMessageがStaffInquiryを参照)
            StaffInquiryMessage.objects.unfiltered().delete()
            StaffInquiry.objects.unfiltered().delete()

            # 6. クライアント関連データ (ClientUserなどがClientを参照)
            ClientFile.objects.unfiltered().delete()
            ClientContactSchedule.objects.unfiltered().delete()
            ClientContacted.objects.unfiltered().delete()
            ClientUser.objects.unfiltered().delete()
            ClientDepartment.objects.unfiltered().delete()
            Client.objects.unfiltered().delete()

            # 6.5. 自社関連データ
            CompanyUser.objects.unfiltered().delete()
            CompanyDepartment.objects.unfiltered().delete()

            # 7. スタッフプロフィール関連 (StaffProfileがUserを参照)
            StaffProfileQualification.objects.all().delete()
            StaffProfileSkill.objects.all().delete()
            StaffProfileMynumber.objects.all().delete()
            StaffProfileInternational.objects.all().delete()
            StaffProfileBank.objects.all().delete()
            StaffProfileDisability.objects.all().delete()
            StaffProfileContact.objects.all().delete()
            StaffProfile.objects.all().delete()
            StaffContactSchedule.objects.unfiltered().delete()

            # 8. スタッフ本体
            Staff.objects.unfiltered().delete()

            # 9. ログデータ
            MailLog.objects.all().delete()
            AppLog.objects.all().delete()
            AccessLog.objects.all().delete()

            # 10. 独立したテーブル
            ClientContractNumber.objects.all().delete()
            StaffContractNumber.objects.all().delete()
            StaffContractTeishokubi.objects.all().delete()

            # 10.5 サンプル用マスタデータの削除
            StaffTag.objects.all().delete()
            ClientTag.objects.all().delete()
            StaffContactType.objects.exclude(display_order=50).delete()
            ClientContactType.objects.exclude(display_order=50).delete()

            # 11. 管理者以外のアカウント
            MyUser.objects.filter(is_superuser=False).delete()

            # 12. 顔写真ファイルの削除
            import shutil
            from django.conf import settings
            staff_photos_dir = os.path.join(settings.MEDIA_ROOT, 'staff_files')
            if os.path.exists(staff_photos_dir):
                for filename in os.listdir(staff_photos_dir):
                    file_path = os.path.join(staff_photos_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f'Failed to delete {file_path}. Reason: {e}')

            # 13. 会社印ファイルの削除
            company_seals_dir = os.path.join(settings.MEDIA_ROOT, 'company_seals')
            if os.path.exists(company_seals_dir):
                for filename in os.listdir(company_seals_dir):
                    file_path = os.path.join(company_seals_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f'Failed to delete {file_path}. Reason: {e}')

            # 14. その他のアップロードファイルの削除
            # mediaルート内の全ファイルを削除（ただし、.gitkeepなどの隠しファイルは残す）
            if os.path.exists(settings.MEDIA_ROOT):
                for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                    for file in files:
                        if not file.startswith('.'):  # .gitkeepなどの隠しファイルは残す
                            file_path = os.path.join(root, file)
                            try:
                                os.unlink(file_path)
                            except Exception as e:
                                print(f'Failed to delete {file_path}. Reason: {e}')

        messages.success(request, "アプリケーションデータを削除しました。")
    except Exception as e:
        messages.error(request, f"データの削除中にエラーが発生しました: {e}")

    return redirect('home:start_page')
