from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.client.models import Client, ClientDepartment
from apps.common.constants import Constants
from apps.master.models import DefaultValue
from apps.staff.models import Staff
from apps.system.logs.models import AppLog

from .forms import ClientContractTtpForm, ClientContractHakenExemptForm, StaffContractTeishokubiDetailForm
from .models import (ClientContract, ClientContractHaken, ClientContractPrint,
                     ClientContractTtp, ClientContractHakenExempt, ContractAssignment,
                     StaffContractTeishokubi, StaffContractTeishokubiDetail)
from .utils import generate_teishokubi_notification_pdf


# 紹介予定派遣
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_ttp_view(request, haken_pk):
    """紹介予定派遣情報の有無に応じて、詳細画面か作成画面にリダイレクトする"""
    haken = get_object_or_404(ClientContractHaken, pk=haken_pk)
    if hasattr(haken, 'ttp_info'):
        # Use parent client contract's start_date/end_date to validate TTP period
        contract = haken.client_contract
        try:
            if contract.start_date and contract.end_date:
                dstart = contract.start_date
                dend = contract.end_date
                months = (dend.year - dstart.year) * 12 + (dend.month - dstart.month)
                if dend.day < dstart.day:
                    months -= 1
                if months > 6:
                    messages.error(request, '労働者派遣法（第40条の6および第40条の7）により紹介予定派遣の派遣期間は6ヶ月までです')
                    return redirect('contract:client_contract_detail', pk=haken.client_contract.pk)
        except Exception:
            # any unexpected issue, allow normal flow
            pass
        return redirect('contract:client_contract_ttp_detail', pk=haken.ttp_info.pk)
    else:
        return redirect('contract:client_contract_ttp_create', haken_pk=haken.pk)


@login_required
@permission_required('contract.add_clientcontract', raise_exception=True)
def client_contract_ttp_create(request, haken_pk):
    """紹介予定派遣情報 作成"""
    haken = get_object_or_404(ClientContractHaken, pk=haken_pk)
    if hasattr(haken, 'ttp_info'):
        messages.info(request, '既にご紹介予定派遣情報が存在します。')
        return redirect('contract:client_contract_ttp_detail', pk=haken.ttp_info.pk)

    # 親契約が「作成中」でない場合はエラー
    if haken.client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, '契約が作成中でないため、紹介予定派遣情報は作成できません。')
        return redirect('contract:client_contract_detail', pk=haken.client_contract.pk)

    if request.method == 'POST':
        form = ClientContractTtpForm(request.POST)
        if form.is_valid():
            ttp_info = form.save(commit=False)
            ttp_info.haken = haken
            ttp_info.created_by = request.user
            ttp_info.updated_by = request.user
            ttp_info.save()
            messages.success(request, '紹介予定派遣情報を作成しました。')
            return redirect('contract:client_contract_ttp_detail', pk=ttp_info.pk)
    else:
        # GETリクエストの場合、初期値をマスタから設定
        initial_data = {}
        default_keys = {
            'contract_period': 'ClientContractTtp.contract_period',
            'probation_period': 'ClientContractTtp.probation_period',
            'working_hours': 'ClientContractTtp.working_hours',
            'break_time': 'ClientContractTtp.break_time',
            'overtime': 'ClientContractTtp.overtime',
            'holidays': 'ClientContractTtp.holidays',
            'vacations': 'ClientContractTtp.vacations',
            'wages': 'ClientContractTtp.wages',
            'insurances': 'ClientContractTtp.insurances',
            'other': 'ClientContractTtp.other',
        }
        for field, key in default_keys.items():
            try:
                default_value = DefaultValue.objects.get(pk=key)
                initial_data[field] = default_value.value
            except DefaultValue.DoesNotExist:
                pass  # マスタにキーが存在しない場合は何もしない

        # 派遣情報から初期値を設定
        if haken.client_contract and haken.client_contract.client:
            initial_data['employer_name'] = haken.client_contract.client.name
        if haken.client_contract.business_content:
            initial_data['business_content'] = haken.client_contract.business_content
        if haken.work_location:
            initial_data['work_location'] = haken.work_location

        form = ClientContractTtpForm(initial=initial_data)

    context = {
        'form': form,
        'haken': haken,
        'contract': haken.client_contract,
        'title': '紹介予定派遣情報 作成',
    }
    return render(request, 'contract/client_contract_ttp_form.html', context)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_ttp_detail(request, pk):
    """紹介予定派遣情報 詳細"""
    ttp_info = get_object_or_404(ClientContractTtp, pk=pk)
    context = {
        'ttp_info': ttp_info,
        'haken': ttp_info.haken,
        'contract': ttp_info.haken.client_contract,
    }
    return render(request, 'contract/client_contract_ttp_detail.html', context)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_ttp_update(request, pk):
    """紹介予定派遣情報 更新"""
    ttp_info = get_object_or_404(ClientContractTtp, pk=pk)
    contract = ttp_info.haken.client_contract
    if contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, '契約が作成中でないため、紹介予定派遣情報は編集できません。')
        return redirect('contract:client_contract_detail', pk=contract.pk)

    if request.method == 'POST':
        form = ClientContractTtpForm(request.POST, instance=ttp_info)
        if form.is_valid():
            ttp_info = form.save(commit=False)
            ttp_info.updated_by = request.user
            ttp_info.save()
            messages.success(request, '紹介予定派遣情報を更新しました。')
            return redirect('contract:client_contract_ttp_detail', pk=ttp_info.pk)
    else:
        form = ClientContractTtpForm(instance=ttp_info)

    context = {
        'form': form,
        'ttp_info': ttp_info,
        'haken': ttp_info.haken,
        'contract': ttp_info.haken.client_contract,
        'title': '紹介予定派遣情報 編集',
    }
    return render(request, 'contract/client_contract_ttp_form.html', context)


@login_required
@permission_required('contract.delete_clientcontract', raise_exception=True)
def client_contract_ttp_delete(request, pk):
    """紹介予定派遣情報 削除"""
    ttp_info = get_object_or_404(ClientContractTtp, pk=pk)
    contract = ttp_info.haken.client_contract
    if contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, '契約が作成中でないため、紹介予定派遣情報は削除できません。')
        return redirect('contract:client_contract_detail', pk=contract.pk)

    contract_pk = ttp_info.haken.client_contract.pk
    if request.method == 'POST':
        ttp_info.delete()
        messages.success(request, '紹介予定派遣情報を削除しました。')
        return redirect('contract:client_contract_detail', pk=contract_pk)

    context = {
        'ttp_info': ttp_info,
        'contract': ttp_info.haken.client_contract,
    }
    return render(request, 'contract/client_contract_ttp_delete.html', context)


# 派遣抵触日制限外
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_haken_exempt_view(request, haken_pk):
    """派遣抵触日制限外情報の有無に応じて、詳細画面か作成画面にリダイレクトする"""
    haken = get_object_or_404(ClientContractHaken, pk=haken_pk)
    if hasattr(haken, 'haken_exempt_info'):
        return redirect('contract:client_contract_haken_exempt_detail', pk=haken.haken_exempt_info.pk)
    else:
        return redirect('contract:client_contract_haken_exempt_create', haken_pk=haken.pk)


@login_required
@permission_required('contract.add_clientcontract', raise_exception=True)
def client_contract_haken_exempt_create(request, haken_pk):
    """派遣抵触日制限外情報 作成"""
    haken = get_object_or_404(ClientContractHaken, pk=haken_pk)
    if hasattr(haken, 'haken_exempt_info'):
        messages.info(request, '既に派遣抵触日制限外情報が存在します。')
        return redirect('contract:client_contract_haken_exempt_detail', pk=haken.haken_exempt_info.pk)

    # 親契約が「作成中」でない場合はエラー
    if haken.client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, '契約が作成中でないため、派遣抵触日制限外情報は作成できません。')
        return redirect('contract:client_contract_detail', pk=haken.client_contract.pk)

    if request.method == 'POST':
        form = ClientContractHakenExemptForm(request.POST)
        if form.is_valid():
            haken_exempt_info = form.save(commit=False)
            haken_exempt_info.haken = haken
            haken_exempt_info.created_by = request.user
            haken_exempt_info.updated_by = request.user
            haken_exempt_info.save()
            messages.success(request, '派遣抵触日制限外情報を作成しました。')
            return redirect('contract:client_contract_haken_exempt_detail', pk=haken_exempt_info.pk)
    else:
        # GETリクエストの場合、初期値をマスタから設定
        initial_data = {}
        default_keys = {
            'period_exempt_detail': 'ClientContractHakenExempt.period_exempt_detail',
        }
        for field, key in default_keys.items():
            try:
                default_value = DefaultValue.objects.get(pk=key)
                initial_data[field] = default_value.value
            except DefaultValue.DoesNotExist:
                pass  # マスタにキーが存在しない場合は何もしない

        form = ClientContractHakenExemptForm(initial=initial_data)

    context = {
        'form': form,
        'haken': haken,
        'contract': haken.client_contract,
        'title': '派遣抵触日制限外情報 作成',
    }
    return render(request, 'contract/client_contract_haken_exempt_form.html', context)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_haken_exempt_detail(request, pk):
    """派遣抵触日制限外情報 詳細"""
    haken_exempt_info = get_object_or_404(ClientContractHakenExempt, pk=pk)
    context = {
        'haken_exempt_info': haken_exempt_info,
        'haken': haken_exempt_info.haken,
        'contract': haken_exempt_info.haken.client_contract,
    }
    return render(request, 'contract/client_contract_haken_exempt_detail.html', context)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_haken_exempt_update(request, pk):
    """派遣抵触日制限外情報 更新"""
    haken_exempt_info = get_object_or_404(ClientContractHakenExempt, pk=pk)
    contract = haken_exempt_info.haken.client_contract
    if contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, '契約が作成中でないため、派遣抵触日制限外情報は編集できません。')
        return redirect('contract:client_contract_detail', pk=contract.pk)

    if request.method == 'POST':
        form = ClientContractHakenExemptForm(request.POST, instance=haken_exempt_info)
        if form.is_valid():
            haken_exempt_info = form.save(commit=False)
            haken_exempt_info.updated_by = request.user
            haken_exempt_info.save()
            messages.success(request, '派遣抵触日制限外情報を更新しました。')
            return redirect('contract:client_contract_haken_exempt_detail', pk=haken_exempt_info.pk)
    else:
        form = ClientContractHakenExemptForm(instance=haken_exempt_info)

    context = {
        'form': form,
        'haken_exempt_info': haken_exempt_info,
        'haken': haken_exempt_info.haken,
        'contract': haken_exempt_info.haken.client_contract,
        'title': '派遣抵触日制限外情報 編集',
    }
    return render(request, 'contract/client_contract_haken_exempt_form.html', context)


@login_required
@permission_required('contract.delete_clientcontract', raise_exception=True)
def client_contract_haken_exempt_delete(request, pk):
    """派遣抵触日制限外情報 削除"""
    haken_exempt_info = get_object_or_404(ClientContractHakenExempt, pk=pk)
    contract = haken_exempt_info.haken.client_contract
    if contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, '契約が作成中でないため、派遣抵触日制限外情報は削除できません。')
        return redirect('contract:client_contract_detail', pk=contract.pk)

    contract_pk = haken_exempt_info.haken.client_contract.pk
    if request.method == 'POST':
        haken_exempt_info.delete()
        messages.success(request, '派遣抵触日制限外情報を削除しました。')
        return redirect('contract:client_contract_detail', pk=contract_pk)

    context = {
        'haken_exempt_info': haken_exempt_info,
        'contract': haken_exempt_info.haken.client_contract,
    }
    return render(request, 'contract/client_contract_haken_exempt_delete.html', context)








@login_required
def client_teishokubi_list(request):
    """事業所抵触日一覧"""
    from apps.client.models import ClientDepartment

    search_query = request.GET.get('q', '')
    # デフォルトで「派遣契約あり」を設定（リセット時は'all'）
    dispatch_filter = request.GET.get('dispatch_filter', 'with_contract')  # 'all' または 'with_contract'

    # 派遣事業所該当の組織で抵触日が設定されているものを取得
    departments = ClientDepartment.objects.filter(
        is_haken_office=True,
        haken_jigyosho_teishokubi__isnull=False
    ).select_related('client')

    # 派遣契約ありフィルタ
    if dispatch_filter == 'with_contract':
        from datetime import date
        today = date.today()
        # 事業所抵触日が今日以降のもののみ
        departments = departments.filter(haken_jigyosho_teishokubi__gte=today)

        # 派遣契約があるもののみに絞り込み
        # ContractAssignmentを通じて派遣契約がある事業所のIDを取得
        valid_department_ids = ContractAssignment.objects.filter(
            client_contract__client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            client_contract__end_date__gte=today  # 終了日が今日以降
        ).values_list('client_contract__haken_info__haken_office_id', flat=True).distinct()

        departments = departments.filter(id__in=valid_department_ids)

    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(client__corporate_number__icontains=search_query)
        )

    departments = departments.order_by('haken_jigyosho_teishokubi', 'client__name', 'name')

    paginator = Paginator(departments, 20)
    page = request.GET.get('page')
    departments_page = paginator.get_page(page)

    # 各事業所で現在派遣中のスタッフ数を取得
    for department in departments_page:
        # この事業所で現在派遣中のスタッフ数を計算（未来分も含む）
        from datetime import date
        current_assignments = ContractAssignment.objects.filter(
            client_contract__haken_info__haken_office=department,
            client_contract__client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            client_contract__end_date__gte=date.today()  # 終了日が今日以降（未来分も含む）
        ).select_related('staff_contract__staff__international', 'staff_contract__staff__disability').distinct()

        department.current_staff_count = current_assignments.count()

        # 抵触日までの残り日数を計算
        if department.haken_jigyosho_teishokubi:
            today = date.today()
            if department.haken_jigyosho_teishokubi >= today:
                delta = department.haken_jigyosho_teishokubi - today
                department.days_remaining = delta.days
                department.is_expired = False
            else:
                delta = today - department.haken_jigyosho_teishokubi
                department.days_overdue = delta.days
                department.is_expired = True

        # 現在派遣中のスタッフ一覧（最大5名まで表示）
        staff_assignments = current_assignments[:5]
        department.current_staff_list = []
        for assignment in staff_assignments:
            staff = assignment.staff_contract.staff
            department.current_staff_list.append({
                'staff_id': staff.id,
                'staff_name': staff.name,
                'contract_start': assignment.client_contract.start_date,
                'contract_end': assignment.client_contract.end_date,
                'has_international': hasattr(staff, 'international'),
                'has_disability': hasattr(staff, 'disability'),
            })

    context = {
        'departments': departments_page,
        'search_query': search_query,
        'dispatch_filter': dispatch_filter,
    }
    return render(request, 'contract/client_teishokubi_list.html', context)


@login_required
def staff_contract_teishokubi_list(request):
    """個人抵触日管理一覧"""
    search_query = request.GET.get('q', '')
    # デフォルトで「派遣契約あり」を設定（リセット時は'all'）
    dispatch_filter = request.GET.get('dispatch_filter', 'with_contract')  # 'all' または 'with_contract'

    teishokubi_list = StaffContractTeishokubi.objects.all()

    # 派遣契約ありフィルタ
    if dispatch_filter == 'with_contract':
        from datetime import date
        today = date.today()
        # 個人抵触日が今日以降のもののみ
        teishokubi_list = teishokubi_list.filter(conflict_date__gte=today)

        # 派遣契約があるもののみに絞り込み
        # ContractAssignmentを通じて派遣契約があるスタッフ・クライアント・組織の組み合わせを取得
        valid_combinations = ContractAssignment.objects.filter(
            client_contract__client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            client_contract__end_date__gte=today  # 終了日が今日以降
        ).values_list(
            'staff_contract__staff__email',
            'client_contract__client__corporate_number',
            'client_contract__haken_info__haken_unit__name'
        ).distinct()

        # 有効な組み合わせでフィルタリング
        if valid_combinations:
            filter_conditions = Q()
            for staff_email, corp_number, org_name in valid_combinations:
                if staff_email and corp_number and org_name:
                    filter_conditions |= Q(
                        staff_email=staff_email,
                        client_corporate_number=corp_number,
                        organization_name=org_name
                    )
            teishokubi_list = teishokubi_list.filter(filter_conditions)
        else:
            # 派遣契約がない場合は空のクエリセットを返す
            teishokubi_list = teishokubi_list.none()

    if search_query:
        staff_emails_from_name_search = list(Staff.objects.filter(name__icontains=search_query).values_list('email', flat=True))
        client_corp_numbers_from_name_search = list(Client.objects.filter(name__icontains=search_query).values_list('corporate_number', flat=True))

        teishokubi_list = teishokubi_list.filter(
            Q(staff_email__icontains=search_query) |
            Q(organization_name__icontains=search_query) |
            Q(client_corporate_number__icontains=search_query) |
            Q(staff_email__in=staff_emails_from_name_search) |
            Q(client_corporate_number__in=client_corp_numbers_from_name_search)
        )

    teishokubi_list = teishokubi_list.order_by('-dispatch_start_date', 'staff_email')

    paginator = Paginator(teishokubi_list, 20)
    page = request.GET.get('page')
    teishokubi_page = paginator.get_page(page)

    staff_emails = [item.staff_email for item in teishokubi_page if item.staff_email]
    client_corporate_numbers = [item.client_corporate_number for item in teishokubi_page if item.client_corporate_number]

    # スタッフ情報を外国人・障害者情報と一緒に取得
    staff_queryset = Staff.objects.filter(email__in=staff_emails).select_related('international', 'disability')
    staff_map = {}
    for staff in staff_queryset:
        staff_map[staff.email] = {
            'id': staff.id,
            'name': staff.name,
            'has_international': hasattr(staff, 'international'),
            'has_disability': hasattr(staff, 'disability')
        }

    client_map = {client.corporate_number: {'id': client.id, 'name': client.name} for client in Client.objects.filter(corporate_number__in=client_corporate_numbers)}

    for item in teishokubi_page:
        staff_info = staff_map.get(item.staff_email)
        if staff_info:
            item.staff_id = staff_info['id']
            item.staff_name = staff_info['name']
            item.staff_has_international = staff_info['has_international']
            item.staff_has_disability = staff_info['has_disability']
        else:
            item.staff_id = None
            item.staff_name = None
            item.staff_has_international = False
            item.staff_has_disability = False

        client_info = client_map.get(item.client_corporate_number)
        if client_info:
            item.client_id = client_info['id']
            item.client_name = client_info['name']
        else:
            item.client_id = None
            item.client_name = None

        # 抵触日までの残り日数を計算
        if item.conflict_date:
            from datetime import date
            today = date.today()
            if item.conflict_date >= today:
                delta = item.conflict_date - today
                item.days_remaining = delta.days
                item.is_expired = False
            else:
                delta = today - item.conflict_date
                item.days_overdue = delta.days
                item.is_expired = True

        # 現在派遣中かどうかを確認（未来分も含む）
        current_assignments = ContractAssignment.objects.filter(
            staff_contract__staff__email=item.staff_email,
            client_contract__client__corporate_number=item.client_corporate_number,
            client_contract__haken_info__haken_unit__name=item.organization_name,
            client_contract__client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            client_contract__end_date__gte=date.today()  # 終了日が今日以降（未来分も含む）
        ).select_related('client_contract').first()

        if current_assignments:
            item.is_currently_dispatched = True
            item.current_contract_end = current_assignments.client_contract.end_date
        else:
            item.is_currently_dispatched = False
            item.current_contract_end = None

    context = {
        'teishokubi_list': teishokubi_page,
        'search_query': search_query,
        'dispatch_filter': dispatch_filter,
    }
    return render(request, 'contract/staff_teishokubi_list.html', context)


@login_required
def staff_contract_teishokubi_detail(request, pk):
    """個人抵触日詳細"""
    teishokubi = get_object_or_404(StaffContractTeishokubi, pk=pk)

    # 削除処理
    if request.method == 'POST' and 'delete_detail_id' in request.POST:
        detail_id = request.POST.get('delete_detail_id')
        detail = get_object_or_404(StaffContractTeishokubiDetail, pk=detail_id, teishokubi=teishokubi)
        if detail.is_manual:  # 手動作成のもののみ削除可能
            detail.delete()

            # 削除後に抵触日を再計算
            from .teishokubi_calculator import TeishokubiCalculator
            calculator = TeishokubiCalculator(
                staff_email=teishokubi.staff_email,
                client_corporate_number=teishokubi.client_corporate_number,
                organization_name=teishokubi.organization_name
            )
            calculator.calculate_and_update()

            messages.success(request, '詳細情報を削除し、抵触日を再計算しました。')
        else:
            messages.error(request, '自動作成された詳細情報は削除できません。')
        return redirect('contract:staff_contract_teishokubi_detail', pk=pk)

    teishokubi_details = StaffContractTeishokubiDetail.objects.filter(teishokubi=teishokubi).order_by('assignment_start_date')

    staff = Staff.objects.filter(email=teishokubi.staff_email).select_related('international', 'disability').first()
    client = Client.objects.filter(corporate_number=teishokubi.client_corporate_number).first()

    # 変更履歴を取得
    from apps.system.logs.models import AppLog
    change_logs = AppLog.objects.filter(
        model_name__in=['StaffContractTeishokubi', 'StaffContractTeishokubiDetail'],
        object_id=str(teishokubi.pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]

    context = {
        'teishokubi': teishokubi,
        'teishokubi_details': teishokubi_details,
        'staff': staff,
        'client': client,
        'change_logs': change_logs,
    }
    return render(request, 'contract/staff_teishokubi_detail.html', context)

@login_required
def staff_contract_teishokubi_detail_create(request, pk):
    """個人抵触日詳細新規作成"""
    teishokubi = get_object_or_404(StaffContractTeishokubi, pk=pk)

    if request.method == 'POST':
        form = StaffContractTeishokubiDetailForm(request.POST)
        if form.is_valid():
            detail = form.save(commit=False)
            detail.teishokubi = teishokubi
            detail.is_manual = True  # 手動作成フラグを設定
            detail.is_calculated = False  # デフォルト値（再計算で正しい値に更新される）
            detail.save()

            # 手動登録後に抵触日を再計算
            from .teishokubi_calculator import TeishokubiCalculator
            calculator = TeishokubiCalculator(
                staff_email=teishokubi.staff_email,
                client_corporate_number=teishokubi.client_corporate_number,
                organization_name=teishokubi.organization_name
            )
            calculator.calculate_and_update()

            messages.success(request, '詳細情報を作成し、抵触日を再計算しました。')
            return redirect('contract:staff_contract_teishokubi_detail', pk=pk)
    else:
        form = StaffContractTeishokubiDetailForm()

    staff = Staff.objects.filter(email=teishokubi.staff_email).first()
    client = Client.objects.filter(corporate_number=teishokubi.client_corporate_number).first()

    context = {
        'form': form,
        'teishokubi': teishokubi,
        'staff': staff,
        'client': client,
    }
    return render(request, 'contract/staff_teishokubi_detail_form.html', context)
