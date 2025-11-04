from .views_assignment import *
from .views_haken import *
from .views_staff import *
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Prefetch, Count
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
import re
from datetime import datetime, date
from django.core.files.base import ContentFile
from datetime import date
from django.forms.models import model_to_dict
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint, ClientContractHaken, ClientContractTtp, ClientContractHakenExempt, StaffContractTeishokubi, StaffContractTeishokubiDetail, ContractAssignmentHakenPrint
from .forms import ClientContractForm, StaffContractForm, ClientContractHakenForm, ClientContractTtpForm, ClientContractHakenExemptForm, StaffContractTeishokubiDetailForm
from apps.common.constants import Constants
from django.conf import settings
from django.utils import timezone
import os
from apps.system.logs.models import AppLog
from apps.common.utils import fill_pdf_from_template
from apps.client.models import Client, ClientUser
from apps.staff.models import Staff
from apps.master.models import ContractPattern, StaffAgreement, DefaultValue
from apps.connect.models import ConnectStaff, ConnectStaffAgree, ConnectClient, MynumberRequest, ProfileRequest, BankRequest, ContactRequest, ConnectInternationalRequest, DisabilityRequest
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company, CompanyDepartment
from apps.system.settings.models import Dropdowns
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from .utils import generate_contract_pdf_content, generate_quotation_pdf, generate_client_contract_number, generate_staff_contract_number, generate_teishokubi_notification_pdf, generate_haken_notification_pdf, generate_haken_motokanri_pdf, generate_haken_sakikanri_pdf

from .resources import ClientContractResource, StaffContractResource
from .models import ContractAssignment
from django.urls import reverse


def _check_assigned_staff_payroll(client_contract):
    """
    クライアント契約に割当されたスタッフの給与関連情報をチェックする
    
    Args:
        client_contract: ClientContractインスタンス
        
    Returns:
        list: 給与関連情報が未登録のスタッフ名のリスト
    """
    from apps.staff.models import StaffPayroll
    
    # この契約に割当されているスタッフ契約を取得
    assignments = ContractAssignment.objects.filter(
        client_contract=client_contract
    ).select_related('staff_contract__staff')
    
    missing_payroll_staff = []
    for assignment in assignments:
        staff = assignment.staff_contract.staff
        try:
            # 給与関連情報が登録されているかチェック
            staff.payroll
        except StaffPayroll.DoesNotExist:
            missing_payroll_staff.append(f"{staff.name_last} {staff.name_first}")
    
    return missing_payroll_staff

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
    
    # 日付フィルタの初期値設定：リセットボタンが押された場合は空、それ以外は「本日以降」
    reset_filter = request.GET.get('reset_filter', '')
    if reset_filter:
        date_filter = ''  # リセット時は「すべて」
    else:
        date_filter = request.GET.get('date_filter', 'future')  # 初期値は「本日以降」

    contracts = ClientContract.objects.select_related('client', 'haken_info__ttp_info').annotate(
        staff_contract_count=Count('staff_contracts')
    )

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

    # 日付フィルタを適用
    if date_filter:
        today = date.today()
        if date_filter == 'today':
            # 本日が契約期間に含まれているもの
            contracts = contracts.filter(
                start_date__lte=today
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )
        elif date_filter == 'future':
            # 本日以降に契約終了があるもの（無期限契約も含む）
            contracts = contracts.filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )

    contracts = contracts.order_by('-start_date', 'client__name')

    contract_status_list = [{'value': d.value, 'name': d.name} for d in Dropdowns.objects.filter(category='contract_status', active=True).order_by('disp_seq')]
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
        'date_filter': date_filter,
    }
    return render(request, 'contract/client_contract_list.html', context)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_detail(request, pk):
    """クライアント契約詳細"""
    contract = get_object_or_404(
        ClientContract.objects.select_related(
            'client', 'job_category', 'contract_pattern', 'payment_site', 'haken_info__ttp_info'
        ).prefetch_related(
            Prefetch(
                'contractassignment_set',
                queryset=ContractAssignment.objects.select_related('staff_contract__staff'),
                to_attr='assigned_assignments'
            )
        ),
        pk=pk
    )
    haken_info = getattr(contract, 'haken_info', None)

    # クライアントフィルタ情報を取得
    client_filter = request.GET.get('client', '')
    from_client_detail = bool(client_filter)
    
    # 遷移元を判定（リファラーから）
    referer = request.META.get('HTTP_REFERER', '')
    from_client_detail_direct = False
    if client_filter and referer and f'/client/client/detail/{client_filter}/' in referer:
        from_client_detail_direct = True
    
    # AppLogから履歴を取得
    from itertools import chain
    contract_logs = AppLog.objects.filter(
        model_name='ClientContract',
        object_id=str(contract.pk),
        action__in=['create', 'update', 'delete', 'print']
    )

    haken_logs = AppLog.objects.none()
    ttp_logs = AppLog.objects.none()
    haken_exempt_logs = AppLog.objects.none()
    
    if haken_info:
        haken_logs = AppLog.objects.filter(
            model_name='ClientContractHaken',
            object_id=str(haken_info.pk),
            action__in=['create', 'update', 'delete']
        )
        
        # TTP情報の変更履歴
        if hasattr(haken_info, 'ttp_info') and haken_info.ttp_info:
            ttp_logs = AppLog.objects.filter(
                model_name='ClientContractTtp',
                object_id=str(haken_info.ttp_info.pk),
                action__in=['create', 'update', 'delete']
            )
        
        # 派遣抵触日制限外情報の変更履歴
        if hasattr(haken_info, 'haken_exempt_info') and haken_info.haken_exempt_info:
            haken_exempt_logs = AppLog.objects.filter(
                model_name='ClientContractHakenExempt',
                object_id=str(haken_info.haken_exempt_info.pk),
                action__in=['create', 'update', 'delete']
            )

    all_change_logs = sorted(
        chain(contract_logs, haken_logs, ttp_logs, haken_exempt_logs),
        key=lambda log: log.timestamp,
        reverse=True
    )
    change_logs_count = len(all_change_logs)
    change_logs = all_change_logs[:5]
    
    # 発行履歴を取得
    all_issue_history = ClientContractPrint.objects.filter(client_contract=contract).order_by('-printed_at', '-pk')
    issue_history_count = all_issue_history.count()
    issue_history_for_display = all_issue_history[:10]

    context = {
        'contract': contract,
        'haken_info': haken_info,
        'issue_history': all_issue_history,
        'issue_history_for_display': issue_history_for_display,
        'issue_history_count': issue_history_count,
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
    copy_from_id = request.GET.get('copy_from')
    extend_from_id = request.GET.get('extend_from')
    selected_client_id = request.GET.get('selected_client_id')
    client_contract_type_code = request.GET.get('client_contract_type_code')

    original_contract = None
    is_extend = False
    
    if copy_from_id:
        try:
            original_contract = get_object_or_404(ClientContract, pk=copy_from_id)
            selected_client_id = original_contract.client_id
            client_contract_type_code = original_contract.client_contract_type_code
        except (ValueError, Http404):
            messages.error(request, "コピー元の契約が見つかりませんでした。")
            return redirect('contract:client_contract_list')
    elif extend_from_id:
        try:
            original_contract = get_object_or_404(ClientContract, pk=extend_from_id)
            selected_client_id = original_contract.client_id
            client_contract_type_code = original_contract.client_contract_type_code
            is_extend = True
        except (ValueError, Http404):
            messages.error(request, "延長元の契約が見つかりませんでした。")
            return redirect('contract:client_contract_list')

    is_haken = client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH
    selected_client = None
    if selected_client_id:
        try:
            selected_client = Client.objects.get(pk=selected_client_id)
        except (Client.DoesNotExist, ValueError):
            pass

    if request.method == 'POST':
        form = ClientContractForm(request.POST)
        post_is_haken = request.POST.get('client_contract_type_code') == Constants.CLIENT_CONTRACT_TYPE.DISPATCH

        client_id = request.POST.get('client')
        post_client = None
        if client_id:
            try:
                post_client = Client.objects.get(pk=client_id)
            except (Client.DoesNotExist, ValueError):
                pass

        haken_form = ClientContractHakenForm(request.POST, client=post_client) if post_is_haken else None

        if form.is_valid() and (not post_is_haken or (haken_form and haken_form.is_valid())):
            try:
                with transaction.atomic():
                    contract = form.save(commit=False)
                    contract.created_by = request.user
                    contract.updated_by = request.user
                    # コピー作成時はステータスを「作成中」に戻す
                    contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                    contract.contract_number = None  # 契約番号はクリア
                    contract.save()

                    if post_is_haken and haken_form:
                        haken_info = haken_form.save(commit=False)
                        haken_info.client_contract = contract
                        haken_info.save()

                    messages.success(request, f'クライアント契約「{contract.contract_name}」を作成しました。')
                    return redirect('contract:client_contract_detail', pk=contract.pk)
            except Exception as e:
                messages.error(request, f"保存中にエラーが発生しました: {e}")
    else:  # GET
        initial_data = {}
        haken_initial_data = {}
        if original_contract:
            # model_to_dictを使用して関連フィールドのIDを正しく取得
            initial_data = model_to_dict(
                original_contract,
                exclude=['id', 'pk', 'contract_number', 'contract_status', 'created_at', 'created_by', 'updated_at', 'updated_by', 'approved_at', 'approved_by', 'issued_at', 'issued_by', 'confirmed_at']
            )
            
            if is_extend:
                # 延長の場合：契約名はそのまま、開始日は元契約の終了日の翌日、終了日は空
                if original_contract.end_date:
                    from datetime import timedelta
                    initial_data['start_date'] = original_contract.end_date + timedelta(days=1)
                initial_data['end_date'] = None
            else:
                # コピーの場合：契約名に「のコピー」を追加
                initial_data['contract_name'] = f"{initial_data.get('contract_name', '')}のコピー"

            if is_haken and hasattr(original_contract, 'haken_info'):
                original_haken_info = original_contract.haken_info
                haken_initial_data = model_to_dict(
                    original_haken_info,
                    exclude=['id', 'pk', 'client_contract', 'created_at', 'created_by', 'updated_at', 'updated_by']
                )
        else:
            if selected_client:
                initial_data['client'] = selected_client.id
            if client_contract_type_code:
                initial_data['client_contract_type_code'] = client_contract_type_code

        form = ClientContractForm(initial=initial_data)
        haken_form = ClientContractHakenForm(initial=haken_initial_data, client=selected_client) if is_haken else None

    context = {
        'form': form,
        'haken_form': haken_form,
        'title': 'クライアント契約作成',
        'is_haken': is_haken,
        'selected_client': selected_client,
        'original_contract': original_contract,
    }
    return render(request, 'contract/client_contract_form.html', context)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_update(request, pk):
    """クライアント契約更新"""
    contract = get_object_or_404(
        ClientContract.objects.select_related('haken_info__ttp_info'),
        pk=pk
    )
    haken_info = getattr(contract, 'haken_info', None)
    
    if contract.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
        messages.error(request, 'この契約は編集できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    post_is_haken = request.POST.get('client_contract_type_code') == Constants.CLIENT_CONTRACT_TYPE.DISPATCH

    if request.method == 'POST':
        form = ClientContractForm(request.POST, instance=contract)
        haken_form = ClientContractHakenForm(request.POST, instance=haken_info, client=contract.client) if post_is_haken else None

        if form.is_valid() and (not post_is_haken or (haken_form and haken_form.is_valid())):
            try:
                # --- TTP 6か月チェック: 保存前にクライアント契約の start_date/end_date を使って確認 ---
                # form.cleaned_data から start_date と end_date を取得し、期間が6か月超であればエラー
                start_date = form.cleaned_data.get('start_date')
                end_date = form.cleaned_data.get('end_date')
                # Determine whether TTP data is present: either existing ttp_info attached to haken_info,
                # or POST contains any TTP-specific fields (user is editing/creating TTP)
                ttp_field_names = [
                    'contract_period', 'probation_period', 'working_hours', 'break_time',
                    'insurances', 'employer_name', 'business_content', 'work_location',
                    'overtime', 'holidays', 'vacations', 'wages', 'other'
                ]
                has_ttp_post = any(name in request.POST for name in ttp_field_names)
                existing_ttp = haken_info and hasattr(haken_info, 'ttp_info')

                if post_is_haken and (has_ttp_post or existing_ttp) and start_date and end_date:
                    d1 = start_date
                    d2 = end_date
                    months = (d2.year - d1.year) * 12 + (d2.month - d1.month)
                    if d2.day < d1.day:
                        months -= 1
                    if months > 6:
                        messages.error(request, '労働者派遣法（第40条の6および第40条の7）により紹介予定派遣の派遣期間は6ヶ月までです')
                        # re-render form with errors
                        raise ValueError('TTP period exceeds 6 months')

                with transaction.atomic():
                    updated_contract = form.save()

                    # 派遣契約の場合
                    if post_is_haken:
                        if haken_form:
                            haken_info = haken_form.save(commit=False)
                            haken_info.client_contract = updated_contract
                            if not haken_info.pk:
                                haken_info.created_by = request.user
                            haken_info.updated_by = request.user
                            haken_info.save()
                    # 派遣契約でなくなった場合
                    elif haken_info:
                        haken_info.delete()

                    messages.success(request, f'クライアント契約「{contract.contract_name}」を更新しました。')
                    return redirect('contract:client_contract_detail', pk=contract.pk)
            except Exception as e:
                # If the exception was our TTP length validation, just show the message already added
                if str(e) == 'TTP period exceeds 6 months':
                    # fall through to re-render
                    pass
                else:
                    messages.error(request, f"更新中にエラーが発生しました: {e}")
        else:
            if not form.is_valid():
                messages.error(request, "入力内容に誤りがあります。各項目をご確認ください。")
            if post_is_haken and haken_form and not haken_form.is_valid():
                messages.error(request, "派遣情報に入力エラーがあります。")
                for field, errors in haken_form.errors.items():
                    for error in errors:
                        label = haken_form.fields[field].label if field != '__all__' else '派遣情報'
                        messages.warning(request, f"{label}: {error}")
    else: # GET
        form = ClientContractForm(instance=contract)
        is_haken = contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH
        haken_form = ClientContractHakenForm(instance=haken_info, client=contract.client) if is_haken else None

    # is_hakenをコンテキストに渡す
    context_is_haken = contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH
    if request.method == 'POST':
        context_is_haken = post_is_haken

    context = {
        'form': form,
        'haken_form': haken_form if 'haken_form' in locals() else (ClientContractHakenForm(instance=haken_info, client=contract.client) if context_is_haken else None),
        'contract': contract,
        'title': 'クライアント契約編集',
        'is_haken': context_is_haken,
    }
    return render(request, 'contract/client_contract_form.html', context)


@login_required
@permission_required('contract.delete_clientcontract', raise_exception=True)
def client_contract_delete(request, pk):
    """クライアント契約削除"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    if contract.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
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


@login_required
@permission_required('contract.add_clientcontract', raise_exception=True)
def client_contract_extend(request, pk):
    """クライアント契約期間延長"""
    original_contract = get_object_or_404(ClientContract, pk=pk)
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        inherit_staff_contracts = request.POST.get('inherit_staff_contracts') == 'on'
        
        if not start_date or not end_date:
            messages.error(request, '契約開始日と契約終了日を入力してください。')
        else:
            try:
                with transaction.atomic():
                    # 元の契約をコピーして新しい契約を作成
                    new_contract = ClientContract()
                    
                    # 元の契約の情報をコピー（IDと日付関連フィールドを除く）
                    exclude_fields = ['id', 'pk', 'contract_number', 'contract_status', 
                                    'created_at', 'created_by', 'updated_at', 'updated_by', 
                                    'approved_at', 'approved_by', 'issued_at', 'issued_by', 
                                    'confirmed_at', 'start_date', 'end_date']
                    
                    for field in original_contract._meta.fields:
                        if field.name not in exclude_fields:
                            setattr(new_contract, field.name, getattr(original_contract, field.name))
                    
                    # 期間延長用の設定
                    new_contract.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    new_contract.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                    new_contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                    new_contract.contract_number = None
                    new_contract.created_by = request.user
                    new_contract.updated_by = request.user
                    
                    new_contract.save()
                    
                    # 派遣情報がある場合はコピー
                    if hasattr(original_contract, 'haken_info') and original_contract.haken_info:
                        from .models import ClientContractHaken
                        new_haken_info = ClientContractHaken()
                        
                        haken_exclude_fields = ['id', 'pk', 'client_contract', 'created_at', 'created_by', 'updated_at', 'updated_by']
                        for field in original_contract.haken_info._meta.fields:
                            if field.name not in haken_exclude_fields:
                                setattr(new_haken_info, field.name, getattr(original_contract.haken_info, field.name))
                        
                        new_haken_info.client_contract = new_contract
                        new_haken_info.created_by = request.user
                        new_haken_info.updated_by = request.user
                        new_haken_info.save()
                    
                    # 割当済みのスタッフ契約を引き継ぐ場合
                    if inherit_staff_contracts:
                        # 元契約の終了日と同じ終了日を持つスタッフ契約を取得
                        target_staff_contracts = StaffContract.objects.filter(
                            client_contracts=original_contract,
                            end_date=original_contract.end_date
                        )
                        
                        for staff_contract in target_staff_contracts:
                            # スタッフ契約をコピー
                            new_staff_contract = StaffContract()
                            
                            staff_exclude_fields = ['id', 'pk', 'contract_number', 'contract_status', 
                                                  'created_at', 'created_by', 'updated_at', 'updated_by', 
                                                  'approved_at', 'approved_by', 'issued_at', 'issued_by', 
                                                  'confirmed_at', 'start_date', 'end_date']
                            
                            for field in staff_contract._meta.fields:
                                if field.name not in staff_exclude_fields:
                                    setattr(new_staff_contract, field.name, getattr(staff_contract, field.name))
                            
                            # 期間を新しいクライアント契約と同じに設定
                            new_staff_contract.start_date = new_contract.start_date
                            new_staff_contract.end_date = new_contract.end_date
                            new_staff_contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                            new_staff_contract.contract_number = None
                            new_staff_contract.created_by = request.user
                            new_staff_contract.updated_by = request.user
                            
                            new_staff_contract.save()
                            
                            # 新しいクライアント契約と新しいスタッフ契約をアサイン
                            ContractAssignment.objects.create(
                                client_contract=new_contract,
                                staff_contract=new_staff_contract,
                                created_by=request.user,
                                updated_by=request.user
                            )
                    
                    if inherit_staff_contracts and target_staff_contracts.exists():
                        messages.success(request, f'クライアント契約「{new_contract.contract_name}」の期間延長契約を作成し、{target_staff_contracts.count()}件のスタッフ契約も延長しました。')
                    else:
                        messages.success(request, f'クライアント契約「{new_contract.contract_name}」の期間延長契約を作成しました。')
                    
                    return redirect('contract:client_contract_detail', pk=new_contract.pk)
                    
            except ValueError:
                messages.error(request, '日付の形式が正しくありません。')
            except Exception as e:
                messages.error(request, f'保存中にエラーが発生しました: {e}')
    
    # 契約開始日のデフォルト値（元契約の終了日の翌日）
    from datetime import timedelta
    default_start_date = original_contract.end_date + timedelta(days=1)
    
    # 割当済みのスタッフ契約で、元契約の終了日と同じ終了日を持つものを取得
    extendable_staff_contracts = StaffContract.objects.filter(
        client_contracts=original_contract,
        end_date=original_contract.end_date
    ).select_related('staff')
    
    context = {
        'original_contract': original_contract,
        'default_start_date': default_start_date,
        'extendable_staff_contracts': extendable_staff_contracts,
        'title': 'クライアント契約期間延長',
    }
    return render(request, 'contract/client_contract_extend.html', context)

# 選択用ビュー
@login_required
def client_select(request):
    """クライアント選択画面"""
    search_query = request.GET.get('q', '')
    return_url = request.GET.get('return_url', '')
    from_modal = request.GET.get('from_modal')
    
    client_contract_type_code = request.GET.get('client_contract_type_code')

    # 契約種別に応じて、適切な基本契約締結日でフィルタリング
    if client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH:  # 派遣の場合
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


# 派遣マスター選択は共通のマスター選択機能に統合されました
# apps.common.views_master.master_select を使用してください

# 変更履歴ビュー
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_issue_history_list(request, pk):
    """クライアント契約の発行履歴一覧"""
    contract = get_object_or_404(ClientContract, pk=pk)

    issue_history_query = ClientContractPrint.objects.filter(client_contract=contract).order_by('-printed_at', '-pk')

    paginator = Paginator(issue_history_query, 20)  # 1ページあたり20件
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'contract': contract,
        'page_obj': page_obj,
    }
    return render(request, 'contract/client_contract_issue_history_list.html', context)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_change_history_list(request, pk):
    """クライアント契約変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    from itertools import chain

    contract = get_object_or_404(ClientContract, pk=pk)
    haken_info = getattr(contract, 'haken_info', None)

    # 該当契約の変更履歴を取得
    contract_logs = AppLog.objects.filter(
        model_name='ClientContract',
        object_id=str(pk),
        action__in=['create', 'update', 'delete', 'print']
    )

    haken_logs = AppLog.objects.none()
    ttp_logs = AppLog.objects.none()
    haken_exempt_logs = AppLog.objects.none()
    
    if haken_info:
        haken_logs = AppLog.objects.filter(
            model_name='ClientContractHaken',
            object_id=str(haken_info.pk),
            action__in=['create', 'update', 'delete']
        )
        
        # TTP情報の変更履歴
        if hasattr(haken_info, 'ttp_info') and haken_info.ttp_info:
            ttp_logs = AppLog.objects.filter(
                model_name='ClientContractTtp',
                object_id=str(haken_info.ttp_info.pk),
                action__in=['create', 'update', 'delete']
            )
        
        # 派遣抵触日制限外情報の変更履歴
        if hasattr(haken_info, 'haken_exempt_info') and haken_info.haken_exempt_info:
            haken_exempt_logs = AppLog.objects.filter(
                model_name='ClientContractHakenExempt',
                object_id=str(haken_info.haken_exempt_info.pk),
                action__in=['create', 'update', 'delete']
            )

    all_logs = sorted(
        chain(contract_logs, haken_logs, ttp_logs, haken_exempt_logs),
        key=lambda log: log.timestamp,
        reverse=True
    )

    # ページネーション
    paginator = Paginator(all_logs, 20)
    page = request.GET.get('page')
    change_logs = paginator.get_page(page)

    context = {
        'object': contract,
        'contract': contract,
        'change_logs': change_logs,
        'page_title': 'クライアント契約 変更履歴一覧',
        'back_url_name': 'contract:client_contract_detail',
    }
    return render(request, 'common/common_change_history_list.html', context)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_pdf(request, pk):
    """クライアント契約書のPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    # 承認済みの場合は発行済みに更新
    if contract.contract_status == Constants.CONTRACT_STATUS.APPROVED:
        contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
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
            document_title=document_title,
            contract_number=contract.contract_number
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
            # 「承認する」アクションは「申請」からのみ可能
            if contract.contract_status == Constants.CONTRACT_STATUS.PENDING:
                try:
                    # TTP（紹介予定派遣）の場合のみ、期間が6か月超でないかチェック
                    if (contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and 
                        contract.start_date and contract.end_date):
                        # 派遣情報とTTP情報が存在するかチェック
                        has_ttp = False
                        try:
                            if hasattr(contract, 'haken_info') and contract.haken_info:
                                has_ttp = hasattr(contract.haken_info, 'ttp_info') and contract.haken_info.ttp_info
                        except:
                            has_ttp = False
                        
                        # TTPが設定されている場合のみ6ヶ月チェック
                        if has_ttp:
                            dstart = contract.start_date
                            dend = contract.end_date
                            months = (dend.year - dstart.year) * 12 + (dend.month - dstart.month)
                            if dend.day < dstart.day:
                                months -= 1
                            if months > 6:
                                messages.error(request, '労働者派遣法（第40条の6および第40条の7）により紹介予定派遣の派遣期間は6ヶ月までです')
                                return redirect('contract:client_contract_detail', pk=contract.pk)

                    # 派遣契約の場合、割当されたスタッフの給与関連情報をチェック
                    if contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
                        missing_payroll_staff = _check_assigned_staff_payroll(contract)
                        if missing_payroll_staff:
                            staff_names = '、'.join(missing_payroll_staff)
                            messages.error(request, 
                                f'派遣契約を承認するには、割当されたスタッフの給与関連情報が必要です。派遣先通知書に保険加入状況を記載する必要があるためです。'
                                f'以下のスタッフの給与関連情報を登録してください：{staff_names}')
                            return redirect('contract:client_contract_detail', pk=contract.pk)

                    # 契約番号を採番
                    contract.contract_number = generate_client_contract_number(contract)
                    contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
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
            if int(contract.contract_status) >= int(Constants.CONTRACT_STATUS.APPROVED):
                # 承認解除: 発行履歴そのものは過去の発行記録として保持する。
                # 契約のステータスと承認/発行関連の日時・ユーザーはクリアする。
                contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                contract.contract_number = None  # 契約番号をクリア
                contract.approved_at = None
                contract.approved_by = None
                # 発行済みフラグは契約上はクリアするが、過去のPDFファイルや履歴は残す
                contract.issued_at = None
                contract.issued_by = None
                # 見積の発行フラグもクリア
                contract.quotation_issued_at = None
                contract.quotation_issued_by = None
                # 抵触日通知書の共有フラグもクリア
                contract.teishokubi_notification_issued_at = None
                contract.teishokubi_notification_issued_by = None
                # 派遣先管理台帳の発行フラグもクリア
                contract.dispatch_ledger_issued_at = None
                contract.dispatch_ledger_issued_by = None
                contract.confirmed_at = None
                contract.save()
                # 承認解除時は見積書をUI上無効化する必要はない。
                # 見積の有効/無効は契約側の quotation_issued_at/quotation_issued_by を参照するため、
                # ClientContractPrint の is_active フラグを更新する操作は削除する。
                messages.success(request, f'契約「{contract.contract_name}」を作成中に戻しました。（発行履歴は保持されます）')
            else:
                messages.error(request, 'この契約の承認は解除できません。')

    return redirect('contract:client_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_issue(request, pk):
    """クライアント契約を発行済にする"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST':
        if contract.contract_status == Constants.CONTRACT_STATUS.APPROVED:
            try:
                with transaction.atomic():
                    # 1. 個別契約書の発行
                    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)
                    if not pdf_content:
                        raise Exception("契約書のPDF生成に失敗しました。")

                    new_print = ClientContractPrint(
                        client_contract=contract,
                        printed_by=request.user,
                        print_type=ClientContractPrint.PrintType.CONTRACT,
                        document_title=document_title,
                        contract_number=contract.contract_number
                    )
                    new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

                    AppLog.objects.create(
                        user=request.user,
                        action='print',
                        model_name='ClientContract',
                        object_id=str(contract.pk),
                        object_repr=f'契約書PDF出力: {contract.contract_name}'
                    )

                    # 2. 派遣契約の場合、派遣通知書も発行
                    if contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
                        issued_at = timezone.now()
                        pdf_content_dispatch, pdf_filename_dispatch, document_title_dispatch = generate_haken_notification_pdf(contract, request.user, issued_at)
                        if not pdf_content_dispatch:
                            raise Exception("派遣先通知書のPDF生成に失敗しました。")

                        new_print_dispatch = ClientContractPrint(
                            client_contract=contract,
                            printed_by=request.user,
                            printed_at=issued_at,
                            print_type=ClientContractPrint.PrintType.DISPATCH_NOTIFICATION,
                            document_title=document_title_dispatch,
                            contract_number=contract.contract_number
                        )
                        new_print_dispatch.pdf_file.save(pdf_filename_dispatch, ContentFile(pdf_content_dispatch), save=True)

                        AppLog.objects.create(
                            user=request.user,
                            action='haken_notification_issue',
                            model_name='ClientContract',
                            object_id=str(contract.pk),
                            object_repr=f'派遣通知書PDF出力 (契約書同時発行): {contract.contract_name}'
                        )
                        messages.success(request, f'派遣通知書を同時に発行しました。')

                    # 3. 契約ステータスを更新
                    contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
                    contract.issued_at = timezone.now()
                    contract.issued_by = request.user
                    contract.save()
                    messages.success(request, f'契約「{contract.contract_name}」の契約書を発行しました。')

            except Exception as e:
                messages.error(request, f"発行処理中にエラーが発生しました: {e}")
        else:
            messages.error(request, "この契約は発行できません。")

    return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_quotation(request, pk):
    """クライアント契約の見積書を発行する"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if int(contract.contract_status) < int(Constants.CONTRACT_STATUS.APPROVED):
        messages.error(request, 'この契約の見積書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # NOTE: allow re-issuing quotations even if a previous quotation exists.
    # This lets users unapprove -> reapprove -> reissue a fresh quotation while
    # preserving past quotation history.

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_quotation_pdf(contract, request.user, issued_at)

    if pdf_content:
        # 履歴として新しい ClientContractPrint を作成
        new_print = ClientContractPrint(
            client_contract=contract,
            printed_by=request.user,
            printed_at=issued_at,
            print_type=ClientContractPrint.PrintType.QUOTATION,
            document_title=document_title,
            contract_number=contract.contract_number
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        # 契約側の見積発行日時/発行者を更新（UI 判定はこれを参照する）
        contract.quotation_issued_at = issued_at
        contract.quotation_issued_by = request.user
        contract.save()

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
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_dispatch_ledger(request, pk):
    """クライアント契約の派遣先管理台帳を発行する"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    # 派遣契約でない場合はエラー
    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, '派遣契約以外では派遣先管理台帳を発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)
    
    # 承認済み以降でない場合はエラー
    if not contract.is_approved_or_later:
        messages.error(request, '承認済み以降の契約でのみ派遣先管理台帳を発行できます。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_sakikanri_pdf(contract, request.user, issued_at)

    if pdf_content:
        new_print = ClientContractPrint.objects.create(
            client_contract=contract,
            printed_by=request.user,
            printed_at=issued_at,
            print_type=ClientContractPrint.PrintType.DISPATCH_LEDGER,
            document_title=document_title,
            contract_number=contract.contract_number
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content))

        # 契約側の派遣先管理台帳発行日時/発行者を更新（UI 判定はこれを参照する）
        contract.dispatch_ledger_issued_at = issued_at
        contract.dispatch_ledger_issued_by = request.user
        contract.save()

        AppLog.objects.create(
            user=request.user,
            action='dispatch_ledger_issue',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'派遣先管理台帳PDF出力: {contract.contract_name}'
        )
        messages.success(request, f'契約「{contract.contract_name}」の派遣先管理台帳を発行しました。')
    else:
        messages.error(request, "派遣先管理台帳のPDFの生成に失敗しました。")

    return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.confirm_clientcontract', raise_exception=True)
def client_contract_confirm(request, pk):
    """クライアント契約を確認済にする"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST':
        is_confirmed = 'is_confirmed' in request.POST
        if is_confirmed:
            if contract.contract_status == Constants.CONTRACT_STATUS.ISSUED:
                contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
                contract.confirmed_at = timezone.now()
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を確認済にしました。')
        else:
            if contract.contract_status == Constants.CONTRACT_STATUS.CONFIRMED:
                contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
                contract.confirmed_at = None
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を未確認に戻しました。')
    return redirect('contract:client_contract_detail', pk=contract.pk)

@login_required
def client_contract_confirm_list(request):
    """クライアント契約確認一覧"""
    user = request.user

    try:
        client_user = ClientUser.objects.get(email=user.email)
        client = client_user.client
    except ClientUser.DoesNotExist:
        client_user = None
        client = None

    if request.method == 'POST':
        contract_id = request.POST.get('contract_id')
        action = request.POST.get('action')
        contract = get_object_or_404(ClientContract, pk=contract_id)

        if action == 'confirm':
            contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
            contract.confirmed_at = timezone.now()
            contract.confirmed_by = client_user
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を確認しました。')

        elif action == 'unconfirm':
            contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
            contract.confirmed_at = None
            contract.confirmed_by = None
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を未確認に戻しました。')

        return redirect('contract:client_contract_confirm_list')

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
    prefetch_prints = Prefetch(
        'print_history',
        queryset=ClientContractPrint.objects.order_by('-printed_at'),
        to_attr='all_prints'
    )
    contracts_query = ClientContract.objects.filter(
        client=client,
        corporate_number__in=approved_corporate_numbers,
        contract_status__in=[
            Constants.CONTRACT_STATUS.APPROVED,
            Constants.CONTRACT_STATUS.ISSUED,
            Constants.CONTRACT_STATUS.CONFIRMED
        ]
    ).select_related('client', 'confirmed_by').prefetch_related(prefetch_prints).order_by('-start_date')

    # ページネーション
    paginator = Paginator(contracts_query, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # PDFの情報を追加
    contracts_with_status = []
    for contract in page_obj:
        # all_printsはprefetchで取得済
        all_prints_for_contract = getattr(contract, 'all_prints', [])

        # 各種の最新PDFを取得
        latest_contract_pdf = next((p for p in all_prints_for_contract if p.print_type == ClientContractPrint.PrintType.CONTRACT), None)
        quotation_pdf = next((p for p in all_prints_for_contract if p.print_type == ClientContractPrint.PrintType.QUOTATION), None)
        teishokubi_notification_pdf = next((p for p in all_prints_for_contract if p.print_type == ClientContractPrint.PrintType.TEISHOKUBI_NOTIFICATION), None)
        dispatch_notification_pdf = next((p for p in all_prints_for_contract if p.print_type == ClientContractPrint.PrintType.DISPATCH_NOTIFICATION), None)
        dispatch_ledger_pdf = next((p for p in all_prints_for_contract if p.print_type == ClientContractPrint.PrintType.DISPATCH_LEDGER), None)

        contracts_with_status.append({
            'contract': contract,
            'latest_contract_pdf': latest_contract_pdf,
            'quotation_pdf': quotation_pdf,
            'teishokubi_notification_pdf': teishokubi_notification_pdf,
            'dispatch_notification_pdf': dispatch_notification_pdf,
            'dispatch_ledger_pdf': dispatch_ledger_pdf,
        })

    context = {
        'contracts_with_status': contracts_with_status,
        'page_obj': page_obj,
        'title': 'クライアント契約確認',
    }
    return render(request, 'contract/client_contract_confirm_list.html', context)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_export(request):
    """クライアント契約データのエクスポート（CSV/Excel）"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    contract_type_filter = request.GET.get('contract_type', '')
    date_filter = request.GET.get('date_filter', '')
    format_type = request.GET.get('format', 'csv')

    contracts = ClientContract.objects.select_related('client', 'haken_info__ttp_info').all()

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
    
    # 日付フィルタを適用
    if date_filter:
        today = date.today()
        if date_filter == 'today':
            # 本日が契約期間に含まれているもの
            contracts = contracts.filter(
                start_date__lte=today
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )
        elif date_filter == 'future':
            # 本日以降に契約終了があるもの（無期限契約も含む）
            contracts = contracts.filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )

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
def client_dispatch_ledger_pdf(request, pk):
    """クライアント契約の派遣元管理台帳PDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の派遣元管理台帳は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_motokanri_pdf(
        contract, request.user, issued_at
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "派遣元管理台帳のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_pdf(request, pk):
    """クライアント契約書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)
    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

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
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "見積書のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_haken_notification(request, pk):
    """クライアント契約の派遣先通知書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の派遣先通知書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_notification_pdf(
        contract, request.user, issued_at, watermark_text="DRAFT"
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "派遣通知書のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_dispatch_ledger(request, pk):
    """クライアント契約の派遣先管理台帳のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の派遣先管理台帳は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_sakikanri_pdf(
        contract, request.user, issued_at, watermark_text="DRAFT"
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "派遣先管理台帳のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)


@login_required
def get_contract_patterns_by_employment_type(request):
    """雇用形態に応じた契約書パターンを取得するAPI"""
    employment_type_id = request.GET.get('employment_type')
    
    if not employment_type_id:
        return JsonResponse({'patterns': []})
    
    from apps.master.models import ContractPattern, EmploymentType
    
    try:
        employment_type = EmploymentType.objects.get(pk=employment_type_id)
    except EmploymentType.DoesNotExist:
        return JsonResponse({'patterns': []})
    
    # スタッフ用で、指定された雇用形態の契約書パターンを取得
    patterns = ContractPattern.objects.filter(
        is_active=True,
        domain=Constants.DOMAIN.STAFF,  # スタッフ
        employment_type=employment_type
    ).values('id', 'name').order_by('display_order')
    
    # 雇用形態が指定されていない契約書パターンも含める
    patterns_without_employment = ContractPattern.objects.filter(
        is_active=True,
        domain=Constants.DOMAIN.STAFF,  # スタッフ
        employment_type__isnull=True
    ).values('id', 'name').order_by('display_order')
    
    # 両方を結合
    all_patterns = list(patterns) + list(patterns_without_employment)
    
    return JsonResponse({'patterns': all_patterns})


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
@permission_required('contract.view_clientcontract', raise_exception=True)
def view_client_contract_pdf(request, pk):
    """
    クライアント契約印刷履歴のPDFをブラウザで表示する
    """
    print_history = get_object_or_404(ClientContractPrint, pk=pk)
    
    if not print_history.pdf_file:
        raise Http404("PDFファイルが見つかりません")
    
    try:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{print_history.pdf_file.name}"'
        return response
    except Exception as e:
        raise Http404(f"PDFファイルの読み込みに失敗しました: {str(e)}")


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def download_client_contract_pdf(request, pk):
    """Downloads a previously generated client contract PDF."""
    print_history = get_object_or_404(ClientContractPrint, pk=pk)

    if not print_history.pdf_file:
        raise Http404("PDFファイルが見つかりません")
    
    try:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        filename = os.path.basename(print_history.pdf_file.name)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        raise Http404(f"PDFファイルの読み込みに失敗しました: {str(e)}")

@login_required
@permission_required('contract.view_contractassignment', raise_exception=True)
def staff_contract_expire_list(request):
    """スタッフ契約延長確認一覧（本日が割当期間内のアサインメント一覧）"""
    from datetime import date, timedelta
    from django.db.models import Q
    from calendar import monthrange
    
    today = date.today()
    search_query = request.GET.get('q', '')
    
    # 本日が割当開始日～割当終了日に入るContractAssignmentを取得
    assignments = ContractAssignment.objects.filter(
        assignment_start_date__lte=today,
        assignment_end_date__gte=today
    ).select_related(
        'client_contract__client',
        'staff_contract__staff',
        'client_contract__job_category',
        'staff_contract__employment_type',
        'assignment_confirm'
    ).order_by('assignment_end_date', 'client_contract__client__name', 'staff_contract__staff__name_last')
    
    # 検索機能
    if search_query:
        assignments = assignments.filter(
            Q(client_contract__client__name__icontains=search_query) |
            Q(staff_contract__staff__name_last__icontains=search_query) |
            Q(staff_contract__staff__name_first__icontains=search_query) |
            Q(client_contract__contract_name__icontains=search_query) |
            Q(staff_contract__contract_name__icontains=search_query) |
            Q(staff_email__icontains=search_query) |
            Q(client_corporate_number__icontains=search_query)
        )
    
    # ページネーション
    paginator = Paginator(assignments, 20)
    page = request.GET.get('page')
    assignments_page = paginator.get_page(page)
    
    # 警告日数を初期値マスタから取得
    from apps.master.models import DefaultValue
    try:
        default_value = DefaultValue.objects.get(key='ContractAssignment.alertdays')
        alert_days = int(default_value.value)
    except (DefaultValue.DoesNotExist, ValueError, TypeError):
        alert_days = 30  # デフォルト30日
    
    # 各アサインメントに追加情報を設定
    for assignment in assignments_page:
        # 割当終了日までの残り日数を計算
        if assignment.assignment_end_date:
            delta = assignment.assignment_end_date - today
            assignment.days_remaining = delta.days
            assignment.is_expiring_soon = delta.days <= alert_days  # 設定された日数以内は要注意
            assignment.is_expired = delta.days < 0
            
            # このスタッフに未来の契約があるかチェック
            future_assignments = ContractAssignment.objects.filter(
                staff_contract__staff=assignment.staff_contract.staff,
                assignment_start_date__gt=assignment.assignment_end_date
            )
            assignment.has_future_contract = future_assignments.exists()
        
        # 契約状況の表示名を取得
        from apps.system.settings.models import Dropdowns
        if assignment.client_contract.contract_status:
            assignment.client_contract_status_display = Dropdowns.get_display_name(
                'contract_status', assignment.client_contract.contract_status
            )
        
        if assignment.staff_contract.contract_status:
            assignment.staff_contract_status_display = Dropdowns.get_display_name(
                'contract_status', assignment.staff_contract.contract_status
            )
    
    # 契約期間イメージ用データを準備（全てのアサインメントを取得）
    all_assignments = ContractAssignment.objects.select_related(
        'client_contract__client',
        'staff_contract__staff',
        'client_contract__job_category',
        'staff_contract__employment_type',
        'assignment_confirm'
    ).order_by('assignment_start_date')
    
    contract_timeline_data = _prepare_contract_timeline_data(all_assignments, today, search_query)
    
    context = {
        'assignments': assignments_page,
        'search_query': search_query,
        'today': today,
        'total_count': assignments.count(),
        'contract_timeline': contract_timeline_data,
    }
    return render(request, 'contract/staff_contract_expire_list.html', context)


def _prepare_contract_timeline_data(all_assignments, today, search_query):
    """契約期間イメージ表示用のデータを準備する"""
    from datetime import date, timedelta
    from calendar import monthrange
    from django.db.models import Q
    from apps.common.constants import Constants
    
    # 今後12ヶ月の月リストを生成
    months = []
    current_date = today.replace(day=1)  # 今月の1日
    prev_year = None
    
    for i in range(12):
        # 前の月と年が異なる場合は年月、同じ場合は月のみ表示
        if prev_year is None or current_date.year != prev_year:
            display = f"{current_date.year}年{current_date.month}月"
        else:
            display = f"{current_date.month}月"
        
        months.append({
            'year': current_date.year,
            'month': current_date.month,
            'display': display,
            'date': current_date
        })
        
        prev_year = current_date.year
        
        # 次の月へ
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    # 検索条件でフィルタリング
    filtered_assignments = all_assignments
    if search_query:
        filtered_assignments = all_assignments.filter(
            Q(client_contract__client__name__icontains=search_query) |
            Q(staff_contract__staff__name_last__icontains=search_query) |
            Q(staff_contract__staff__name_first__icontains=search_query) |
            Q(client_contract__contract_name__icontains=search_query) |
            Q(staff_contract__contract_name__icontains=search_query) |
            Q(staff_email__icontains=search_query) |
            Q(client_corporate_number__icontains=search_query)
        )
    
    # スタッフごとの契約期間データを準備
    staff_contracts = {}
    
    # 表示対象のスタッフを特定（現在進行中の契約があるスタッフ）
    current_staff_ids = set()
    for assignment in filtered_assignments:
        if (assignment.assignment_start_date <= today <= assignment.assignment_end_date):
            current_staff_ids.add(assignment.staff_contract.staff.id)
    
    # 各スタッフのすべてのアサインメントを処理
    for staff_id in current_staff_ids:
        staff_assignments = [a for a in all_assignments if a.staff_contract.staff.id == staff_id]
        
        if staff_assignments:
            first_assignment = staff_assignments[0]
            staff_key = f"{first_assignment.staff_contract.staff.name_last} {first_assignment.staff_contract.staff.name_first}"
            
            staff_contracts[staff_key] = {
                'staff_name': staff_key,
                'staff_id': staff_id,
                'employment_type': first_assignment.staff_contract.employment_type,
                'months': [{'month': m['display'], 'status': 'none', 'client_name': '', 'assignment_id': None} for m in months]
            }
            
            # このスタッフの全アサインメントを各月にマッピング
            for assignment in staff_assignments:
                for i, month_info in enumerate(months):
                    month_start = month_info['date']
                    # 月末日を取得
                    last_day = monthrange(month_info['year'], month_info['month'])[1]
                    month_end = month_start.replace(day=last_day)
                    
                    # アサインメント期間と月の重複をチェック
                    assignment_start = assignment.assignment_start_date
                    assignment_end = assignment.assignment_end_date
                    
                    has_contract = (
                        assignment_start <= month_end and 
                        assignment_end >= month_start
                    )
                    
                    if has_contract:
                        # 契約状態を判定
                        if assignment_start > today:
                            status = 'future'  # 未来の契約（別のアサインメント）
                        elif assignment_start <= today <= assignment_end:
                            status = 'current'  # 現在進行中の契約
                        else:
                            continue  # 過去の契約は表示しない
                        
                        # 契約終了月かどうかをチェック
                        if assignment_end >= month_start and assignment_end <= month_end:
                            # この月で契約が終了する
                            # このスタッフの次のアサインメントがあるかチェック
                            has_future_assignment = any(
                                future_assignment.assignment_start_date > assignment_end
                                for future_assignment in staff_assignments
                            )
                            
                            if not has_future_assignment and status == 'current':
                                # 延長確認登録で「終了予定」が登録されているかチェック
                                has_termination_confirm = (
                                    hasattr(assignment, 'assignment_confirm') and 
                                    assignment.assignment_confirm and
                                    assignment.assignment_confirm.confirm_type == Constants.ASSIGNMENT_CONFIRM_TYPE.TERMINATE
                                )
                                
                                if has_termination_confirm:
                                    status = 'ending_confirmed'  # 契約終了（終了予定として確認済み）
                                else:
                                    status = 'ending'  # 契約終了（次のアサインメントなし）
                        
                        # 既存の契約がない場合、または優先度に基づいて更新
                        current_status = staff_contracts[staff_key]['months'][i]['status']
                        if (current_status == 'none' or 
                            (current_status == 'future' and status in ['current', 'ending', 'ending_confirmed']) or
                            (current_status == 'current' and status in ['ending', 'ending_confirmed'])):
                            
                            staff_contracts[staff_key]['months'][i] = {
                                'month': month_info['display'],
                                'status': status,
                                'client_name': assignment.client_contract.client.name,
                                'assignment_id': assignment.id,
                                'end_date': assignment.assignment_end_date if status in ['ending', 'ending_confirmed'] else None
                            }
    
    return {
        'months': [m['display'] for m in months],
        'staff_data': list(staff_contracts.values())
    }


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def assignment_employment_conditions_pdf(request, assignment_pk):
    """
    就業条件明示書PDF出力
    POSTリクエスト: 状況カードのスイッチから呼び出し（発行履歴に保存してリダイレクト）
    GETリクエスト: 印刷メニューから呼び出し（PDFを直接表示）
    """
    from .models import ContractAssignmentHakenPrint
    from django.core.files.base import ContentFile
    
    assignment = get_object_or_404(
        ContractAssignment.objects.select_related(
            'client_contract__client',
            'staff_contract__staff',
            'client_contract__haken_info__haken_office',
            'client_contract__haken_info__commander',
            'client_contract__haken_info__complaint_officer_client'
        ),
        pk=assignment_pk
    )
    
    # 派遣契約かどうかチェック
    if assignment.client_contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約は派遣契約ではないため、就業条件明示書を発行できません。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    # スタッフ契約の状態チェック（作成中または申請の場合のみ）
    if assignment.staff_contract.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
        messages.error(request, 'スタッフ契約が作成中または申請状態の場合のみ就業条件明示書を発行できます。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    try:
        # PDF生成
        from .utils import generate_employment_conditions_pdf
        pdf_content = generate_employment_conditions_pdf(
            assignment=assignment,
            user=request.user,
            issued_at=timezone.now(),
            watermark_text="DRAFT"
        )
        
        # ファイル名を生成
        filename = f"employment_conditions_draft_{assignment.pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # ログ記録（ドラフト版でも操作ログは残す）
        AppLog.objects.create(
            user=request.user,
            model_name='ContractAssignment',
            object_id=str(assignment.pk),
            action='print',
            object_repr=f'就業条件明示書（ドラフト）を出力しました'
        )
        
        # POSTリクエストの場合はメッセージを表示してリダイレクト
        if request.method == 'POST':
            messages.success(request, '就業条件明示書（ドラフト）を出力しました。')
            return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
        
        # GETリクエストの場合はPDFを直接表示
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        messages.error(request, f'就業条件明示書の生成中にエラーが発生しました: {str(e)}')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)

