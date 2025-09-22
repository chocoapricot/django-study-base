from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, Http404
from django.core.files.base import ContentFile
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint
from .forms import ClientContractForm, StaffContractForm
from django.conf import settings
from django.utils import timezone
import os
from apps.system.logs.models import AppLog
from apps.common.utils import fill_pdf_from_template
from apps.client.models import Client, ClientUser
from apps.staff.models import Staff
from apps.master.models import ContractPattern, StaffAgreement
from apps.connect.models import ConnectStaff, ConnectStaffAgree, ConnectClient, MynumberRequest, ProfileRequest, BankRequest, ContactRequest, ConnectInternationalRequest, DisabilityRequest
from apps.company.models import Company
from apps.system.settings.models import Dropdowns
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from apps.common.pdf_utils import generate_contract_pdf
from .utils import generate_contract_pdf_content, generate_quotation_pdf, generate_client_contract_number
from .resources import ClientContractResource, StaffContractResource

# 契約管理トップページ
@login_required
def contract_index(request):
    """契約管理トップページ"""
    # クライアント契約の統計
    client_contract_count = ClientContract.objects.count()
    current_client_contracts = ClientContract.objects.count()
    recent_client_contracts = ClientContract.objects.select_related('client').order_by('-created_at')[:5]
    
    # スタッフ契約の統計
    staff_contract_count = StaffContract.objects.count()
    current_staff_contracts = StaffContract.objects.count()
    recent_staff_contracts = StaffContract.objects.select_related('staff').order_by('-created_at')[:5]
    
    context = {
        'client_contract_count': client_contract_count,
        'current_client_contracts': current_client_contracts,
        'recent_client_contracts': recent_client_contracts,
        'staff_contract_count': staff_contract_count,
        'current_staff_contracts': current_staff_contracts,
        'recent_staff_contracts': recent_staff_contracts,
    }
    return render(request, 'contract/contract_index.html', context)


# クライアント契約管理
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_list(request):
    """クライアント契約一覧"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    contract_type_filter = request.GET.get('contract_type', '')

    contracts = ClientContract.objects.select_related('client').all()

    if client_filter:
        contracts = contracts.filter(client_id=client_filter)

    if search_query:
        contracts = contracts.filter(
            Q(contract_name__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(contract_number__icontains=search_query)
        )

    if status_filter:
        contracts = contracts.filter(contract_status=status_filter)

    if contract_type_filter:
        contracts = contracts.filter(client_contract_type_code=contract_type_filter)

    contracts = contracts.order_by('-start_date', 'client__name')

    contract_status_list = [{'value': v, 'name': n} for v, n in ClientContract.ContractStatus.choices]
    client_contract_type_list = [{'value': d.value, 'name': d.name} for d in Dropdowns.objects.filter(category='client_contract_type', active=True).order_by('disp_seq')]


    paginator = Paginator(contracts, 20)
    page = request.GET.get('page')
    contracts_page = paginator.get_page(page)

    filtered_client = None
    if client_filter:
        from apps.client.models import Client
        try:
            filtered_client = Client.objects.get(pk=client_filter)
        except Client.DoesNotExist:
            pass

    company = Company.objects.first()
    corporate_number = company.corporate_number if company else None

    client_user_emails = {}
    for contract in contracts_page:
        client = contract.client
        if client and client.pk not in client_user_emails:
            client_user_emails[client.pk] = list(client.users.values_list('email', flat=True))

    if corporate_number:
        all_emails = [email for emails in client_user_emails.values() for email in emails if email]

        approved_connections = set(ConnectClient.objects.filter(
            corporate_number=corporate_number,
            email__in=all_emails,
            status='approved'
        ).values_list('email', flat=True))

        pending_connections = set(ConnectClient.objects.filter(
            corporate_number=corporate_number,
            email__in=all_emails,
            status='pending'
        ).values_list('email', flat=True))

        for contract in contracts_page:
            client = contract.client
            client.has_connected_approved_user = False
            client.has_pending_connection_request = False

            if client and client.pk in client_user_emails:
                user_emails = set(client_user_emails[client.pk])
                if not approved_connections.isdisjoint(user_emails):
                    client.has_connected_approved_user = True
                if not pending_connections.isdisjoint(user_emails):
                    client.has_pending_connection_request = True
    else:
        for contract in contracts_page:
            client = contract.client
            client.has_connected_approved_user = False
            client.has_pending_connection_request = False

    context = {
        'contracts': contracts_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'filtered_client': filtered_client,
        'contract_status_list': contract_status_list,
        'contract_type_filter': contract_type_filter,
        'client_contract_type_list': client_contract_type_list,
    }
    return render(request, 'contract/client_contract_list.html', context)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_detail(request, pk):
    """クライアント契約詳細"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    # クライアントフィルタ情報を取得
    client_filter = request.GET.get('client', '')
    from_client_detail = bool(client_filter)
    
    # 遷移元を判定（リファラーから）
    referer = request.META.get('HTTP_REFERER', '')
    from_client_detail_direct = False
    if client_filter and referer:
        # クライアント詳細画面から直接遷移した場合
        if f'/client/client/detail/{client_filter}/' in referer:
            from_client_detail_direct = True
    
    # AppLogから履歴を取得
    all_change_logs = AppLog.objects.filter(
        model_name='ClientContract',
        object_id=str(contract.pk),
        action__in=['create', 'update', 'delete', 'print']
    ).order_by('-timestamp')
    change_logs_count = all_change_logs.count()
    change_logs = all_change_logs[:10]  # 最新10件
    
    # 発行履歴を取得
    all_prints = ClientContractPrint.objects.filter(client_contract=contract).order_by('-printed_at')
    issue_history = all_prints

    context = {
        'contract': contract,
        'issue_history': issue_history,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
        'client_filter': client_filter,
        'from_client_detail': from_client_detail,
        'from_client_detail_direct': from_client_detail_direct,
    }
    return render(request, 'contract/client_contract_detail.html', context)


@login_required
@permission_required('contract.add_clientcontract', raise_exception=True)
def client_contract_create(request):
    """クライアント契約作成"""
    selected_client_id_from_get = request.GET.get('selected_client_id')
    client_contract_type_code = request.GET.get('client_contract_type_code')

    selected_client = None

    if request.method == 'POST':
        form = ClientContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user
            contract.updated_by = request.user
            contract.client_contract_type_code = form.cleaned_data.get('client_contract_type_code')
            contract.save()
            messages.success(request, f'クライアント契約「{contract.contract_name}」を作成しました。')
            return redirect('contract:client_contract_detail', pk=contract.pk)
        else:
            client_id = request.POST.get('client')
            if client_id:
                try:
                    selected_client = Client.objects.get(pk=client_id)
                except (Client.DoesNotExist, ValueError):
                    pass
    else:
        initial_data = {}
        if selected_client_id_from_get:
            initial_data['client'] = selected_client_id_from_get
            try:
                selected_client = Client.objects.get(pk=selected_client_id_from_get)
            except (Client.DoesNotExist, ValueError):
                pass
        if client_contract_type_code:
            initial_data['client_contract_type_code'] = client_contract_type_code
        form = ClientContractForm(initial=initial_data)

    context = {
        'form': form,
        'title': 'クライアント契約作成',
        'client_contract_type_code': client_contract_type_code,
        'selected_client': selected_client,
    }
    return render(request, 'contract/client_contract_form.html', context)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_update(request, pk):
    """クライアント契約更新"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    if contract.contract_status not in [ClientContract.ContractStatus.DRAFT, ClientContract.ContractStatus.PENDING]:
        messages.error(request, 'この契約は編集できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    if request.method == 'POST':
        form = ClientContractForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.updated_by = request.user
            contract.client_contract_type_code = form.cleaned_data.get('client_contract_type_code')
            contract.save()
            messages.success(request, f'クライアント契約「{contract.contract_name}」を更新しました。')
            return redirect('contract:client_contract_detail', pk=contract.pk)
    else:
        form = ClientContractForm(instance=contract)
    
    context = {
        'form': form,
        'contract': contract,
        'title': 'クライアント契約編集',
    }
    return render(request, 'contract/client_contract_form.html', context)


@login_required
@permission_required('contract.delete_clientcontract', raise_exception=True)
def client_contract_delete(request, pk):
    """クライアント契約削除"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    if contract.contract_status not in [ClientContract.ContractStatus.DRAFT, ClientContract.ContractStatus.PENDING]:
        messages.error(request, 'この契約は削除できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    if request.method == 'POST':
        contract_name = contract.contract_name
        contract.delete()
        messages.success(request, f'クライアント契約「{contract_name}」を削除しました。')
        return redirect('contract:client_contract_list')
    
    context = {
        'contract': contract,
    }
    return render(request, 'contract/client_contract_delete.html', context)


# スタッフ契約管理
@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_list(request):
    """スタッフ契約一覧"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    staff_filter = request.GET.get('staff', '')  # スタッフフィルタを追加
    contract_pattern_filter = request.GET.get('contract_pattern', '')
    
    contracts = StaffContract.objects.select_related('staff', 'contract_pattern').all()
    
    # スタッフフィルタを適用
    if staff_filter:
        contracts = contracts.filter(staff_id=staff_filter)
    
    # 検索条件を適用
    if search_query:
        contracts = contracts.filter(
            Q(contract_name__icontains=search_query) |
            Q(staff__name_last__icontains=search_query) |
            Q(staff__name_first__icontains=search_query) |
            Q(contract_number__icontains=search_query)
        )
    
    # ステータスフィルタを適用
    if status_filter:
        contracts = contracts.filter(contract_status=status_filter)

    # 契約パターンフィルタを適用
    if contract_pattern_filter:
        contracts = contracts.filter(contract_pattern_id=contract_pattern_filter)

    contracts = contracts.order_by('-start_date', 'staff__name_last', 'staff__name_first')

    # 契約状況のドロップダウンリストを取得
    contract_status_list = [{'value': v, 'name': n} for v, n in StaffContract.ContractStatus.choices]
    contract_pattern_list = ContractPattern.objects.filter(domain='1')
    
    # ページネーション
    paginator = Paginator(contracts, 20)
    page = request.GET.get('page')
    contracts_page = paginator.get_page(page)
    
    # フィルタ対象のスタッフ情報を取得（パンくずリスト用）
    filtered_staff = None
    if staff_filter:
        from apps.staff.models import Staff
        try:
            filtered_staff = Staff.objects.get(pk=staff_filter)
        except Staff.DoesNotExist:
            pass

    # 各スタッフの接続情報などを効率的に取得
    company = Company.objects.first()
    corporate_number = company.corporate_number if company else None

    staff_emails = [contract.staff.email for contract in contracts_page if contract.staff and contract.staff.email]
    connect_staff_map = {}
    pending_requests = {}

    if corporate_number and staff_emails:
        connect_staff_qs = ConnectStaff.objects.filter(
            corporate_number=corporate_number,
            email__in=staff_emails
        )
        connect_staff_map = {cs.email: cs for cs in connect_staff_qs}

        approved_connect_staff_ids = [
            cs.id for cs in connect_staff_map.values() if cs.status == 'approved'
        ]

        if approved_connect_staff_ids:
            pending_requests = {
                'mynumber': set(MynumberRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'profile': set(ProfileRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'bank': set(BankRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'contact': set(ContactRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'international': set(ConnectInternationalRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
                'disability': set(DisabilityRequest.objects.filter(connect_staff_id__in=approved_connect_staff_ids, status='pending').values_list('connect_staff__email', flat=True)),
            }

    # 各契約のスタッフに情報を付与
    for contract in contracts_page:
        staff = contract.staff
        staff.is_connected_approved = False
        staff.has_pending_connection_request = False
        staff.has_pending_mynumber_request = False
        staff.has_pending_profile_request = False
        staff.has_pending_bank_request = False
        staff.has_pending_contact_request = False
        staff.has_pending_international_request = False
        staff.has_pending_disability_request = False

        connect_request = connect_staff_map.get(staff.email)
        if connect_request:
            staff.is_connected_approved = connect_request.status == 'approved'
            staff.has_pending_connection_request = connect_request.status == 'pending'
            if staff.is_connected_approved:
                staff.has_pending_mynumber_request = staff.email in pending_requests.get('mynumber', set())
                staff.has_pending_profile_request = staff.email in pending_requests.get('profile', set())
                staff.has_pending_bank_request = staff.email in pending_requests.get('bank', set())
                staff.has_pending_contact_request = staff.email in pending_requests.get('contact', set())
                staff.has_pending_international_request = staff.email in pending_requests.get('international', set())
                staff.has_pending_disability_request = staff.email in pending_requests.get('disability', set())

        # has_internationalはモデルのプロパティで処理
        staff.has_international_info = hasattr(staff, 'international')
    
    context = {
        'contracts': contracts_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'staff_filter': staff_filter,
        'filtered_staff': filtered_staff,
        'contract_status_list': contract_status_list,
        'contract_pattern_filter': contract_pattern_filter,
        'contract_pattern_list': contract_pattern_list,
    }
    return render(request, 'contract/staff_contract_list.html', context)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_detail(request, pk):
    """スタッフ契約詳細"""
    contract = get_object_or_404(StaffContract, pk=pk)
    
    # スタッフフィルタ情報を取得
    staff_filter = request.GET.get('staff', '')
    from_staff_detail = bool(staff_filter)
    
    # 遷移元を判定（リファラーから）
    referer = request.META.get('HTTP_REFERER', '')
    from_staff_detail_direct = False
    if staff_filter and referer:
        # スタッフ詳細画面から直接遷移した場合
        if f'/staff/staff/detail/{staff_filter}/' in referer:
            from_staff_detail_direct = True
    
    # AppLogから履歴を取得
    all_change_logs = AppLog.objects.filter(
        model_name='StaffContract',
        object_id=str(contract.pk),
        action__in=['create', 'update', 'delete', 'print']
    ).order_by('-timestamp')
    change_logs_count = all_change_logs.count()
    change_logs = all_change_logs[:10]  # 最新10件

    # 発行履歴を取得
    print_history = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at')
    
    context = {
        'contract': contract,
        'print_history': print_history,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
        'staff_filter': staff_filter,
        'from_staff_detail': from_staff_detail,
        'from_staff_detail_direct': from_staff_detail_direct,
        'ContractStatus': StaffContract.ContractStatus,
    }
    return render(request, 'contract/staff_contract_detail.html', context)


@login_required
@permission_required('contract.add_staffcontract', raise_exception=True)
def staff_contract_create(request):
    """スタッフ契約作成"""
    staff = None
    if request.method == 'POST':
        form = StaffContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user
            contract.updated_by = request.user
            contract.save()
            messages.success(request, f'スタッフ契約「{contract.contract_name}」を作成しました。')
            return redirect('contract:staff_contract_detail', pk=contract.pk)
        else:
            # フォームが無効な場合、選択されたスタッフ情報を取得
            staff_id = request.POST.get('staff')
            if staff_id:
                try:
                    staff = Staff.objects.get(pk=staff_id)
                except (Staff.DoesNotExist, ValueError):
                    staff = None
    else:
        form = StaffContractForm()

    context = {
        'form': form,
        'title': 'スタッフ契約作成',
        'staff': staff,
    }
    return render(request, 'contract/staff_contract_form.html', context)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_update(request, pk):
    """スタッフ契約更新"""
    contract = get_object_or_404(StaffContract, pk=pk)
    
    if contract.contract_status not in [StaffContract.ContractStatus.DRAFT, StaffContract.ContractStatus.PENDING]:
        messages.error(request, 'この契約は編集できません。')
        return redirect('contract:staff_contract_detail', pk=pk)

    if request.method == 'POST':
        form = StaffContractForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.updated_by = request.user
            contract.save()
            messages.success(request, f'スタッフ契約「{contract.contract_name}」を更新しました。')
            return redirect('contract:staff_contract_detail', pk=contract.pk)
    else:
        form = StaffContractForm(instance=contract)
    
    context = {
        'form': form,
        'contract': contract,
        'title': 'スタッフ契約編集',
    }
    return render(request, 'contract/staff_contract_form.html', context)


@login_required
@permission_required('contract.delete_staffcontract', raise_exception=True)
def staff_contract_delete(request, pk):
    """スタッフ契約削除"""
    contract = get_object_or_404(StaffContract, pk=pk)

    if contract.contract_status not in [StaffContract.ContractStatus.DRAFT, StaffContract.ContractStatus.PENDING]:
        messages.error(request, 'この契約は削除できません。')
        return redirect('contract:staff_contract_detail', pk=pk)
    
    if request.method == 'POST':
        contract_name = contract.contract_name
        contract.delete()
        messages.success(request, f'スタッフ契約「{contract_name}」を削除しました。')
        return redirect('contract:staff_contract_list')
    
    context = {
        'contract': contract,
    }
    return render(request, 'contract/staff_contract_delete.html', context)


# 選択用ビュー
@login_required
def client_select(request):
    """クライアント選択画面"""
    search_query = request.GET.get('q', '')
    return_url = request.GET.get('return_url', '')
    from_modal = request.GET.get('from_modal')
    
    client_contract_type_code = request.GET.get('client_contract_type_code')

    # 契約種別に応じて、適切な基本契約締結日でフィルタリング
    if client_contract_type_code == '20':  # 派遣の場合
        clients = Client.objects.filter(basic_contract_date_haken__isnull=False)
    else:  # それ以外（業務委託など）の場合
        clients = Client.objects.filter(basic_contract_date__isnull=False)

    # 法人番号が設定されているクライアントのみを対象とする
    clients = clients.exclude(corporate_number__isnull=True).exclude(corporate_number__exact='')
    
    if search_query:
        clients = clients.filter(
            Q(name__icontains=search_query) |
            Q(corporate_number__icontains=search_query)
        )
    
    clients = clients.order_by('name')
    
    # ページネーション
    paginator = Paginator(clients, 20)
    page = request.GET.get('page')
    clients_page = paginator.get_page(page)
    
    context = {
        'page_obj': clients_page,
        'search_query': search_query,
        'return_url': return_url,
        'client_contract_type_code': client_contract_type_code,
    }

    if from_modal:
        return render(request, 'contract/_client_select_modal.html', context)
    else:
        return render(request, 'contract/client_select.html', context)


@login_required
def staff_select(request):
    """スタッフ選択画面"""
    search_query = request.GET.get('q', '')
    return_url = request.GET.get('return_url', '')
    from_modal = request.GET.get('from_modal')

    # 社員番号と入社日が入っているスタッフのみを対象とする
    staff_list = Staff.objects.filter(
        employee_no__isnull=False,
        hire_date__isnull=False
    ).exclude(employee_no='')
    
    if search_query:
        staff_list = staff_list.filter(
            Q(name_last__icontains=search_query) |
            Q(name_first__icontains=search_query) |
            Q(employee_no__icontains=search_query)
        )
    
    staff_list = staff_list.order_by('name_last', 'name_first')
    
    # ページネーション
    paginator = Paginator(staff_list, 20)
    page = request.GET.get('page')
    staff_page = paginator.get_page(page)
    
    context = {
        'page_obj': staff_page,
        'search_query': search_query,
        'return_url': return_url,
    }

    if from_modal:
        return render(request, 'contract/_staff_select_modal.html', context)
    else:
        return render(request, 'contract/staff_select.html', context)


# 変更履歴ビュー
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_change_history_list(request, pk):
    """クライアント契約変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    
    contract = get_object_or_404(ClientContract, pk=pk)
    
    # 該当契約の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name='ClientContract',
        object_id=str(pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    return render(request, 'contract/contract_change_history_list.html', {
        'logs': logs_page,
        'title': f'クライアント契約変更履歴 - {contract.contract_name}',
        'list_url': 'contract:client_contract_detail',
        'list_url_pk': pk,
        'model_name': 'ClientContract'
    })


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_change_history_list(request, pk):
    """スタッフ契約変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    
    contract = get_object_or_404(StaffContract, pk=pk)
    
    # 該当契約の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name='StaffContract',
        object_id=str(pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    return render(request, 'contract/contract_change_history_list.html', {
        'logs': logs_page,
        'title': f'スタッフ契約変更履歴 - {contract.contract_name}',
        'list_url': 'contract:staff_contract_detail',
        'list_url_pk': pk,
        'model_name': 'StaffContract'
    })


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_pdf(request, pk):
    """クライアント契約書のPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    # 承認済みの場合は発行済みに更新
    if contract.contract_status == ClientContract.ContractStatus.APPROVED:
        contract.contract_status = ClientContract.ContractStatus.ISSUED
        contract.issued_at = timezone.now()
        contract.issued_by = request.user
        contract.save()
        messages.success(request, f'契約「{contract.contract_name}」の契約書を発行しました。')

    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        new_print = ClientContractPrint(
            client_contract=contract,
            printed_by=request.user,
            print_type=ClientContractPrint.PrintType.CONTRACT,
            document_title=document_title
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        AppLog.objects.create(
            user=request.user,
            action='print',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'契約書PDF出力: {contract.contract_name}'
        )

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_approve(request, pk):
    """クライアント契約の承認ステータスを更新する"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST':
        is_approved = request.POST.get('is_approved')
        if is_approved:
            # 「承認する」アクションは「申請中」からのみ可能
            if contract.contract_status == ClientContract.ContractStatus.PENDING:
                try:
                    # 契約番号を採番
                    contract.contract_number = generate_client_contract_number(contract)
                    contract.contract_status = ClientContract.ContractStatus.APPROVED
                    contract.approved_at = timezone.now()
                    contract.approved_by = request.user
                    contract.save()
                    messages.success(request, f'契約「{contract.contract_name}」を承認済にしました。契約番号: {contract.contract_number}')
                except ValueError as e:
                    messages.error(request, f'契約番号の採番に失敗しました。理由: {e}')
            else:
                messages.error(request, 'このステータスからは承認できません。')
        else:
            # 「承認解除」アクションは「承認済」以降からのみ可能
            if int(contract.contract_status) >= int(ClientContract.ContractStatus.APPROVED):
                # 関連する発行履歴（契約書・見積書）を削除
                for print_history in contract.print_history.all():
                    if print_history.pdf_file:
                        print_history.pdf_file.delete(save=False)
                    print_history.delete()

                contract.contract_status = ClientContract.ContractStatus.DRAFT
                contract.contract_number = None  # 契約番号をクリア
                contract.approved_at = None
                contract.approved_by = None
                contract.issued_at = None
                contract.issued_by = None
                contract.confirmed_at = None
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を作成中に戻しました。')
            else:
                messages.error(request, 'この契約の承認は解除できません。')

    return redirect('contract:client_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_issue(request, pk):
    """クライアント契約を発行済にする"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST':
        if contract.contract_status == ClientContract.ContractStatus.APPROVED:
            pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)
            if pdf_content:
                new_print = ClientContractPrint(
                    client_contract=contract,
                    printed_by=request.user,
                    print_type=ClientContractPrint.PrintType.CONTRACT,
                    document_title=document_title
                )
                new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

                AppLog.objects.create(
                    user=request.user,
                    action='print',
                    model_name='ClientContract',
                    object_id=str(contract.pk),
                    object_repr=f'契約書PDF出力: {contract.contract_name}'
                )
                contract.contract_status = ClientContract.ContractStatus.ISSUED
                contract.issued_at = timezone.now()
                contract.issued_by = request.user
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」の契約書を発行しました。')
            else:
                messages.error(request, "契約書の発行に失敗しました。")
        else:
            messages.error(request, "この契約は発行できません。")

    return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_quotation(request, pk):
    """クライアント契約の見積書を発行する"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if int(contract.contract_status) < int(ClientContract.ContractStatus.APPROVED):
        messages.error(request, 'この契約の見積書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # 既に発行済みの場合はエラー
    if ClientContractPrint.objects.filter(client_contract=contract, print_type=ClientContractPrint.PrintType.QUOTATION).exists():
        messages.error(request, 'この契約の見積書は既に発行済みです。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_quotation_pdf(contract, request.user, issued_at)

    if pdf_content:
        new_print = ClientContractPrint(
            client_contract=contract,
            printed_by=request.user,
            printed_at=issued_at,
            print_type=ClientContractPrint.PrintType.QUOTATION,
            document_title=document_title
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        AppLog.objects.create(
            user=request.user,
            action='quotation_issue',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'見積書PDF出力: {contract.contract_name}'
        )
        messages.success(request, f'契約「{contract.contract_name}」の見積書を発行しました。')
    else:
        messages.error(request, "見積書のPDFの生成に失敗しました。")

    return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.confirm_clientcontract', raise_exception=True)
def client_contract_confirm(request, pk):
    """クライアント契約を確認済にする"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST':
        is_confirmed = 'is_confirmed' in request.POST
        if is_confirmed:
            if contract.contract_status == ClientContract.ContractStatus.ISSUED:
                contract.contract_status = ClientContract.ContractStatus.CONFIRMED
                contract.confirmed_at = timezone.now()
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を確認済にしました。')
        else:
            if contract.contract_status == ClientContract.ContractStatus.CONFIRMED:
                contract.contract_status = ClientContract.ContractStatus.ISSUED
                contract.confirmed_at = None
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を未確認に戻しました。')
    return redirect('contract:client_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_approve(request, pk):
    """スタッフ契約の承認ステータスを更新する"""
    contract = get_object_or_404(StaffContract, pk=pk)
    if request.method == 'POST':
        is_approved = request.POST.get('is_approved')
        if is_approved:
            contract.contract_status = StaffContract.ContractStatus.APPROVED
            contract.approved_at = timezone.now()
            contract.approved_by = request.user
            messages.success(request, f'契約「{contract.contract_name}」を承認済にしました。')
        else:
            contract.contract_status = StaffContract.ContractStatus.DRAFT
            contract.approved_at = None
            contract.approved_by = None
            contract.issued_at = None
            contract.issued_by = None
            contract.confirmed_at = None
            messages.success(request, f'契約「{contract.contract_name}」を作成中に戻しました。')
        contract.save()
    return redirect('contract:staff_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_issue(request, pk):
    """スタッフ契約を発行済にする"""
    contract = get_object_or_404(StaffContract, pk=pk)
    if request.method == 'POST':
        is_issued = 'is_issued' in request.POST
        if is_issued:
            if contract.contract_status == StaffContract.ContractStatus.APPROVED:
                pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)
                if pdf_content:
                    new_print = StaffContractPrint(
                        staff_contract=contract,
                        printed_by=request.user,
                        document_title=document_title
                    )
                    new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

                    AppLog.objects.create(
                        user=request.user,
                        action='print',
                        model_name='StaffContract',
                        object_id=str(contract.pk),
                        object_repr=f'契約書PDF出力: {contract.contract_name}'
                    )
                    contract.contract_status = StaffContract.ContractStatus.ISSUED
                    contract.issued_at = timezone.now()
                    contract.issued_by = request.user
                    contract.save()
                    messages.success(request, f'契約「{contract.contract_name}」の契約書を発行しました。')
                else:
                    messages.error(request, "契約書の発行に失敗しました。")
        else:
            if contract.contract_status == StaffContract.ContractStatus.ISSUED:
                contract.contract_status = StaffContract.ContractStatus.APPROVED
                contract.issued_at = None
                contract.issued_by = None
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を承認済に戻しました。')
    return redirect('contract:staff_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def download_client_contract_pdf(request, pk):
    """Downloads a previously generated client contract PDF."""
    print_history = get_object_or_404(ClientContractPrint, pk=pk)

    if print_history.pdf_file:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(print_history.pdf_file.name)}"'
        return response

    raise Http404

@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def download_staff_contract_pdf(request, pk):
    """Downloads a previously generated staff contract PDF."""
    print_history = get_object_or_404(StaffContractPrint, pk=pk)

    if print_history.pdf_file:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(print_history.pdf_file.name)}"'
        return response

    raise Http404


@login_required
def staff_contract_confirm_list(request):
    """スタッフ契約確認一覧"""
    user = request.user

    if request.method == 'POST':
        contract_id = request.POST.get('contract_id')
        action = request.POST.get('action')
        contract = get_object_or_404(StaffContract, pk=contract_id)

        if action == 'confirm':
            # スタッフ同意文言を取得
            staff_agreement = StaffAgreement.objects.filter(
                Q(corporation_number=contract.corporate_number) | Q(corporation_number__isnull=True) | Q(corporation_number=''),
                is_active=True
            ).order_by('-corporation_number', '-created_at').first()

            if staff_agreement:
                ConnectStaffAgree.objects.update_or_create(
                    email=user.email,
                    corporate_number=contract.corporate_number,
                    staff_agreement=staff_agreement,
                    defaults={'is_agreed': True}
                )
                contract.contract_status = StaffContract.ContractStatus.CONFIRMED
                contract.confirmed_at = timezone.now()
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を確認しました。')
            else:
                messages.error(request, '確認可能な同意文言が見つかりませんでした。')

        elif action == 'unconfirm':
            contract.contract_status = StaffContract.ContractStatus.ISSUED
            contract.confirmed_at = None
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を未確認に戻しました。')

        return redirect('contract:staff_contract_confirm_list')

    try:
        staff = Staff.objects.get(email=user.email)
    except Staff.DoesNotExist:
        staff = None

    if not staff:
        context = {
            'contracts_with_status': [],
            'title': 'スタッフ契約確認',
        }
        return render(request, 'contract/staff_contract_confirm_list.html', context)

    # 接続許可されている法人番号を取得
    approved_corporate_numbers = ConnectStaff.objects.filter(
        email=user.email,
        status='approved'
    ).values_list('corporate_number', flat=True)

    # 契約を取得
    contracts = StaffContract.objects.filter(
        staff=staff,
        corporate_number__in=approved_corporate_numbers,
        contract_status__in=[StaffContract.ContractStatus.ISSUED, StaffContract.ContractStatus.CONFIRMED]
    ).select_related('staff').order_by('-start_date')

    # 同意状況とPDFの情報を追加
    contracts_with_status = []
    for contract in contracts:
        # 同意文言の取得
        staff_agreement = StaffAgreement.objects.filter(
            Q(corporation_number=contract.corporate_number) | Q(corporation_number__isnull=True) | Q(corporation_number=''),
            is_active=True
        ).order_by('-corporation_number', '-created_at').first()

        is_agreed = False
        if staff_agreement:
            is_agreed = ConnectStaffAgree.objects.filter(
                email=user.email,
                corporate_number=contract.corporate_number,
                staff_agreement=staff_agreement,
                is_agreed=True
            ).exists()

        # 最新のPDFを取得
        latest_pdf = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at').first()

        contracts_with_status.append({
            'contract': contract,
            'is_agreed': is_agreed,
            'latest_pdf': latest_pdf,
        })

    context = {
        'contracts_with_status': contracts_with_status,
        'title': 'スタッフ契約確認',
        'ContractStatus': StaffContract.ContractStatus,
    }
    return render(request, 'contract/staff_contract_confirm_list.html', context)


@login_required
def client_contract_confirm_list(request):
    """クライアント契約確認一覧"""
    user = request.user

    if request.method == 'POST':
        contract_id = request.POST.get('contract_id')
        action = request.POST.get('action')
        contract = get_object_or_404(ClientContract, pk=contract_id)

        if action == 'confirm':
            contract.contract_status = ClientContract.ContractStatus.CONFIRMED
            contract.confirmed_at = timezone.now()
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を確認しました。')

        elif action == 'unconfirm':
            contract.contract_status = ClientContract.ContractStatus.ISSUED
            contract.confirmed_at = None
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を未確認に戻しました。')

        return redirect('contract:client_contract_confirm_list')

    try:
        client_user = ClientUser.objects.get(email=user.email)
        client = client_user.client
    except ClientUser.DoesNotExist:
        client = None

    if not client:
        context = {
            'contracts_with_status': [],
            'title': 'クライアント契約確認',
        }
        return render(request, 'contract/client_contract_confirm_list.html', context)

    # 接続許可されている法人番号を取得
    approved_corporate_numbers = ConnectClient.objects.filter(
        email=user.email,
        status='approved'
    ).values_list('corporate_number', flat=True)

    # 契約を取得
    contracts = ClientContract.objects.filter(
        client=client,
        corporate_number__in=approved_corporate_numbers,
        contract_status__in=[ClientContract.ContractStatus.ISSUED, ClientContract.ContractStatus.CONFIRMED]
    ).select_related('client').order_by('-start_date')

    # PDFの情報を追加
    contracts_with_status = []
    for contract in contracts:
        # 最新のPDFを取得
        latest_pdf = ClientContractPrint.objects.filter(client_contract=contract).order_by('-printed_at').first()

        contracts_with_status.append({
            'contract': contract,
            'latest_pdf': latest_pdf,
        })

    context = {
        'contracts_with_status': contracts_with_status,
        'title': 'クライアント契約確認',
    }
    return render(request, 'contract/client_contract_confirm_list.html', context)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_pdf(request, pk):
    """スタッフ契約書のPDFを生成して返す"""
    contract = get_object_or_404(StaffContract, pk=pk)

    # 承認済みの場合は発行済みに更新
    if contract.contract_status == StaffContract.ContractStatus.APPROVED:
        contract.contract_status = StaffContract.ContractStatus.ISSUED
        contract.issued_at = timezone.now()
        contract.issued_by = request.user
        contract.save()
        messages.success(request, f'契約「{contract.contract_name}」の契約書を発行しました。')

    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        new_print = StaffContractPrint(
            staff_contract=contract,
            printed_by=request.user,
            document_title=document_title
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        AppLog.objects.create(
            user=request.user,
            action='print',
            model_name='StaffContract',
            object_id=str(contract.pk),
            object_repr=f'契約書PDF出力: {contract.contract_name}'
        )

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:staff_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_export(request):
    """クライアント契約データのエクスポート（CSV/Excel）"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    contract_pattern_filter = request.GET.get('contract_pattern', '')
    format_type = request.GET.get('format', 'csv')

    contracts = ClientContract.objects.select_related('client', 'contract_pattern').all()

    if client_filter:
        contracts = contracts.filter(client_id=client_filter)
    if search_query:
        contracts = contracts.filter(
            Q(contract_name__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(contract_number__icontains=search_query)
        )
    if status_filter:
        contracts = contracts.filter(contract_status=status_filter)
    if contract_pattern_filter:
        contracts = contracts.filter(contract_pattern_id=contract_pattern_filter)

    contracts = contracts.order_by('-start_date', 'client__name')

    resource = ClientContractResource()
    dataset = resource.export(contracts)

    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    if format_type == 'excel':
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="client_contracts_{timestamp}.xlsx"'
    else:
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="client_contracts_{timestamp}.csv"'

    return response


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_pdf(request, pk):
    """クライアント契約書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)
    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_draft_pdf(request, pk):
    """スタッフ契約書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(StaffContract, pk=pk)
    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:staff_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_quotation(request, pk):
    """クライアント契約の見積書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_quotation_pdf(
        contract, request.user, issued_at, watermark_text="DRAFT"
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "見積書のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_export(request):
    """スタッフ契約データのエクスポート（CSV/Excel）"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    staff_filter = request.GET.get('staff', '')
    contract_pattern_filter = request.GET.get('contract_pattern', '')
    format_type = request.GET.get('format', 'csv')

    contracts = StaffContract.objects.select_related('staff', 'contract_pattern').all()

    if staff_filter:
        contracts = contracts.filter(staff_id=staff_filter)
    if search_query:
        contracts = contracts.filter(
            Q(contract_name__icontains=search_query) |
            Q(staff__name_last__icontains=search_query) |
            Q(staff__name_first__icontains=search_query) |
            Q(contract_number__icontains=search_query)
        )
    if status_filter:
        contracts = contracts.filter(contract_status=status_filter)
    if contract_pattern_filter:
        contracts = contracts.filter(contract_pattern_id=contract_pattern_filter)

    contracts = contracts.order_by('-start_date', 'staff__name_last', 'staff__name_first')

    resource = StaffContractResource()
    dataset = resource.export(contracts)

    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    if format_type == 'excel':
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="staff_contracts_{timestamp}.xlsx"'
    else:
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="staff_contracts_{timestamp}.csv"'

    return response

