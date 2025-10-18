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
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint, ClientContractHaken, ClientContractTtp, StaffContractTeishokubi, StaffContractTeishokubiDetail
from .forms import ClientContractForm, StaffContractForm, ClientContractHakenForm, ClientContractTtpForm, StaffContractTeishokubiDetailForm
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
from .utils import generate_contract_pdf_content, generate_quotation_pdf, generate_client_contract_number, generate_staff_contract_number, generate_teishokubi_notification_pdf, generate_dispatch_notification_pdf, generate_dispatch_ledger_pdf
from .resources import ClientContractResource, StaffContractResource
from .models import ContractAssignment
from django.urls import reverse

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
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_issue_history_list(request, pk):
    """スタッフ契約の発行履歴一覧"""
    contract = get_object_or_404(StaffContract, pk=pk)

    issue_history_query = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at', '-pk')

    paginator = Paginator(issue_history_query, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'contract': contract,
        'page_obj': page_obj,
    }
    return render(request, 'contract/staff_contract_issue_history_list.html', context)


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
    if haken_info:
        haken_logs = AppLog.objects.filter(
            model_name='ClientContractHaken',
            object_id=str(haken_info.pk),
            action__in=['create', 'update', 'delete']
        )

    all_change_logs = sorted(
        chain(contract_logs, haken_logs),
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


# スタッフ契約管理
@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_list(request):
    """スタッフ契約一覧"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    staff_filter = request.GET.get('staff', '')  # スタッフフィルタを追加
    employment_type_filter = request.GET.get('employment_type', '')
    has_international_filter = request.GET.get('has_international', '')
    has_disability_filter = request.GET.get('has_disability', '')
    
    # 日付フィルタの初期値設定：リセットボタンが押された場合は空、それ以外は「本日以降」
    reset_filter = request.GET.get('reset_filter', '')
    if reset_filter:
        date_filter = ''  # リセット時は「すべて」
    else:
        date_filter = request.GET.get('date_filter', 'future')  # 初期値は「本日以降」
    
    contracts = StaffContract.objects.select_related('staff', 'employment_type').annotate(
        client_contract_count=Count('client_contracts')
    )
    
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

    # 雇用形態フィルタを適用
    if employment_type_filter:
        contracts = contracts.filter(employment_type_id=employment_type_filter)

    # 外国籍での絞り込み
    if has_international_filter:
        contracts = contracts.filter(staff__international__isnull=False)

    # 障害者での絞り込み
    if has_disability_filter:
        contracts = contracts.filter(staff__disability__isnull=False)

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

    contracts = contracts.order_by('-start_date', 'staff__name_last', 'staff__name_first')

    # 契約状況のドロップダウンリストを取得
    contract_status_list = [{'value': d.value, 'name': d.name} for d in Dropdowns.objects.filter(category='contract_status', active=True).order_by('disp_seq')]
    from apps.master.models import EmploymentType
    employment_type_list = EmploymentType.objects.filter(is_active=True).order_by('display_order')
    
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
        # 障害者情報登録状況を判定
        staff.has_disability_info = hasattr(staff, 'disability')
    
    context = {
        'contracts': contracts_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'staff_filter': staff_filter,
        'filtered_staff': filtered_staff,
        'contract_status_list': contract_status_list,
        'employment_type_filter': employment_type_filter,
        'employment_type_list': employment_type_list,
        'date_filter': date_filter,
        'has_international_filter': has_international_filter,
        'has_disability_filter': has_disability_filter,
    }
    return render(request, 'contract/staff_contract_list.html', context)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_detail(request, pk):
    """スタッフ契約詳細"""
    contract = get_object_or_404(
        StaffContract.objects.prefetch_related(
            Prefetch(
                'contractassignment_set',
                queryset=ContractAssignment.objects.select_related('client_contract__client'),
                to_attr='assigned_assignments'
            )
        ),
        pk=pk
    )
    
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
    change_logs = all_change_logs[:5]  # 最新5件

    # 発行履歴を取得
    all_issue_history = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at', '-pk')
    issue_history_count = all_issue_history.count()
    issue_history_for_display = all_issue_history[:10]

    # 最低時給を取得（表示用なので時給単位に関係なく取得）
    minimum_wage = None
    minimum_wage_pref_name = None
    if contract.work_location:
        from apps.master.models import MinimumPay
        from apps.system.settings.models import Dropdowns
        
        prefectures = Dropdowns.objects.filter(category='pref', active=True)
        found_prefecture = None
        for pref_dropdown in prefectures:
            if pref_dropdown.name in contract.work_location:
                found_prefecture = pref_dropdown
                break
        
        if found_prefecture:
            minimum_wage_record = MinimumPay.objects.filter(
                is_active=True,
                pref=found_prefecture.value,
                start_date__lte=contract.start_date,
            ).order_by('-start_date').first()
            
            if minimum_wage_record:
                minimum_wage = minimum_wage_record.hourly_wage
                minimum_wage_pref_name = found_prefecture.name

    # TTPアサインメントの有無を確認
    has_ttp_assignment = False
    for assignment in contract.assigned_assignments:
        if (hasattr(assignment.client_contract, 'haken_info') and 
            assignment.client_contract.haken_info and 
            hasattr(assignment.client_contract.haken_info, 'ttp_info') and 
            assignment.client_contract.haken_info.ttp_info):
            has_ttp_assignment = True
            break

    context = {
        'contract': contract,
        'issue_history': all_issue_history,
        'issue_history_for_display': issue_history_for_display,
        'issue_history_count': issue_history_count,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
        'staff_filter': staff_filter,
        'from_staff_detail': from_staff_detail,
        'from_staff_detail_direct': from_staff_detail_direct,
        'minimum_wage': minimum_wage,
        'minimum_wage_pref_name': minimum_wage_pref_name,
        'has_ttp_assignment': has_ttp_assignment,
        'CONTRACT_STATUS': Constants.CONTRACT_STATUS,
    }
    return render(request, 'contract/staff_contract_detail.html', context)


@login_required
@permission_required('contract.add_staffcontract', raise_exception=True)
def staff_contract_create(request):
    """スタッフ契約作成"""
    copy_from_id = request.GET.get('copy_from')
    extend_from_id = request.GET.get('extend_from')
    client_contract_id = request.GET.get('client_contract')  # クライアント契約からの作成
    original_contract = None
    client_contract = None
    is_extend = False
    
    if copy_from_id:
        try:
            original_contract = get_object_or_404(StaffContract, pk=copy_from_id)
        except (ValueError, Http404):
            messages.error(request, "コピー元の契約が見つかりませんでした。")
            return redirect('contract:staff_contract_list')
    elif extend_from_id:
        try:
            original_contract = get_object_or_404(StaffContract, pk=extend_from_id)
            is_extend = True
        except (ValueError, Http404):
            messages.error(request, "延長元の契約が見つかりませんでした。")
            return redirect('contract:staff_contract_list')
    elif client_contract_id:
        try:
            client_contract = get_object_or_404(ClientContract, pk=client_contract_id)
        except (ValueError, Http404):
            messages.error(request, "クライアント契約が見つかりませんでした。")
            return redirect('contract:client_contract_list')

    staff = None
    if original_contract:
        staff = original_contract.staff

    if request.method == 'POST':
        form = StaffContractForm(request.POST, client_contract=client_contract)
        if form.is_valid():
            try:
                # クライアント契約からの作成の場合、確認画面に遷移（まだ保存しない）
                if client_contract_id:
                    # フォームデータをセッション用に変換（モデルインスタンスをIDに変換）
                    session_data = {}
                    for key, value in form.cleaned_data.items():
                        if hasattr(value, 'pk'):  # モデルインスタンスの場合
                            session_data[key] = value.pk
                        elif isinstance(value, (date, datetime)):  # 日付の場合
                            session_data[key] = value.isoformat()
                        elif hasattr(value, '__str__'):  # Decimal型などを文字列に変換
                            session_data[key] = str(value)
                        else:
                            session_data[key] = value
                    
                    request.session['pending_staff_contract'] = {
                        'client_contract_id': client_contract_id,
                        'form_data': session_data,
                        'from_view': 'client'
                    }
                    return redirect('contract:staff_assignment_confirm_from_create')
                else:
                    # 通常の新規作成の場合は従来通り保存
                    with transaction.atomic():
                        contract = form.save(commit=False)
                        contract.created_by = request.user
                        contract.updated_by = request.user
                        # 新規作成・コピー作成時はステータスを「作成中」に戻す
                        contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                        contract.contract_number = None  # 契約番号はクリア
                        
                        # 雇用形態が設定されていない場合、スタッフの現在の雇用形態を設定
                        if not contract.employment_type and contract.staff and contract.staff.employment_type:
                            contract.employment_type = contract.staff.employment_type
                        
                        contract.save()
                        messages.success(request, f'スタッフ契約「{contract.contract_name}」を作成しました。')
                    
                    return redirect('contract:staff_contract_detail', pk=contract.pk)
            except Exception as e:
                messages.error(request, f"保存中にエラーが発生しました: {e}")
        else:
            # フォームが無効な場合、選択されたスタッフ情報を取得
            staff_id = request.POST.get('staff')
            if staff_id:
                try:
                    staff = Staff.objects.get(pk=staff_id)
                except (Staff.DoesNotExist, ValueError):
                    staff = None
    else:  # GET
        initial_data = {}
        if original_contract:
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
        elif client_contract:
            # クライアント契約からの作成の場合、情報をコピー
            initial_data['start_date'] = client_contract.start_date
            initial_data['end_date'] = client_contract.end_date
            initial_data['business_content'] = client_contract.business_content
            if client_contract.job_category:
                initial_data['job_category'] = client_contract.job_category.pk
            
            # 派遣契約の場合は就業場所もコピー
            if hasattr(client_contract, 'haken_info') and client_contract.haken_info:
                initial_data['work_location'] = client_contract.haken_info.work_location
            
            # 契約名はデフォルト値を使用
            try:
                default_value = DefaultValue.objects.get(pk='StaffContract.contract_name')
                initial_data['contract_name'] = default_value.value
            except DefaultValue.DoesNotExist:
                initial_data['contract_name'] = f"{client_contract.contract_name} - スタッフ契約"
        else:
            # コピーでない新規作成の場合、マスタからデフォルト値を取得
            try:
                default_value = DefaultValue.objects.get(pk='StaffContract.contract_name')
                initial_data['contract_name'] = default_value.value
            except DefaultValue.DoesNotExist:
                pass  # マスタにキーが存在しない場合は何もしない

        form = StaffContractForm(initial=initial_data, client_contract=client_contract)

    context = {
        'form': form,
        'title': 'スタッフ契約作成',
        'staff': staff,
        'client_contract': client_contract,
        'original_contract': original_contract,
    }
    return render(request, 'contract/staff_contract_form.html', context)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_update(request, pk):
    """スタッフ契約更新"""
    contract = get_object_or_404(StaffContract, pk=pk)
    
    if contract.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
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

    if contract.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
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


@login_required
@permission_required('contract.add_staffcontract', raise_exception=True)
def staff_contract_extend(request, pk):
    """スタッフ契約期間延長"""
    original_contract = get_object_or_404(StaffContract, pk=pk)
    
    # 終了日が設定されていない契約は延長できない
    if not original_contract.end_date:
        messages.error(request, '終了日が設定されていない契約は期間延長できません。')
        return redirect('contract:staff_contract_detail', pk=pk)
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if not start_date:
            messages.error(request, '契約開始日を入力してください。')
        else:
            try:
                with transaction.atomic():
                    # 元の契約をコピーして新しい契約を作成
                    new_contract = StaffContract()
                    
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
                    if end_date:
                        new_contract.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                    else:
                        new_contract.end_date = None
                    
                    new_contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                    new_contract.contract_number = None
                    new_contract.created_by = request.user
                    new_contract.updated_by = request.user
                    
                    new_contract.save()
                    
                    messages.success(request, f'スタッフ契約「{new_contract.contract_name}」の期間延長契約を作成しました。')
                    return redirect('contract:staff_contract_detail', pk=new_contract.pk)
                    
            except ValueError:
                messages.error(request, '日付の形式が正しくありません。')
            except Exception as e:
                messages.error(request, f'保存中にエラーが発生しました: {e}')
    
    # 契約開始日のデフォルト値（元契約の終了日の翌日）
    from datetime import timedelta
    default_start_date = original_contract.end_date + timedelta(days=1)
    
    context = {
        'original_contract': original_contract,
        'default_start_date': default_start_date,
        'title': 'スタッフ契約期間延長',
    }
    return render(request, 'contract/staff_contract_extend.html', context)


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


@login_required
def haken_master_select(request):
    """派遣マスター選択画面"""
    search_query = request.GET.get('q', '')
    master_type = request.GET.get('type', '')  # 'business_content' or 'responsibility_degree'
    
    # マスタータイプに応じてデータを取得（有効なもののみ）
    if master_type == 'business_content':
        from apps.master.models import BusinessContent
        items = BusinessContent.objects.filter(is_active=True)
        modal_title = '業務内容を選択'
    elif master_type == 'responsibility_degree':
        from apps.master.models import HakenResponsibilityDegree
        items = HakenResponsibilityDegree.objects.filter(is_active=True)
        modal_title = '責任の程度を選択'
    else:
        items = []
        modal_title = 'マスター選択'
    
    if search_query:
        items = items.filter(content__icontains=search_query)
    
    # 表示順で並び替え（モデルのMeta.orderingを使用）
    items = items.order_by('display_order')
    
    # ページネーション
    paginator = Paginator(items, 20)
    page = request.GET.get('page')
    items_page = paginator.get_page(page)
    
    context = {
        'page_obj': items_page,
        'search_query': search_query,
        'master_type': master_type,
        'modal_title': modal_title,
    }

    return render(request, 'contract/_haken_master_select_modal.html', context)


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


    # 部署名を取得してスタッフオブジェクトに付与
    department_codes = [staff.department_code for staff in staff_page if staff.department_code]
    department_map = {}
    if department_codes:
        today = timezone.now().date()

        valid_departments = CompanyDepartment.objects.filter(
            department_code__in=set(department_codes)
        ).filter(
            Q(valid_from__isnull=True) | Q(valid_from__lte=today)
        ).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=today)
        )

        department_map = {dep.department_code: dep.name for dep in valid_departments}

    for staff in staff_page:
        staff.department_name = department_map.get(staff.department_code, staff.department_code)

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
    if haken_info:
        haken_logs = AppLog.objects.filter(
            model_name='ClientContractHaken',
            object_id=str(haken_info.pk),
            action__in=['create', 'update', 'delete']
        )

    all_logs = sorted(
        chain(contract_logs, haken_logs),
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
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_change_history_list(request, pk):
    """スタッフ契約変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    
    contract = get_object_or_404(StaffContract, pk=pk)
    
    # 該当契約の変更履歴を取得
    all_logs = AppLog.objects.filter(
        model_name='StaffContract',
        object_id=str(pk),
        action__in=['create', 'update', 'delete', 'print']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(all_logs, 20)
    page = request.GET.get('page')
    change_logs = paginator.get_page(page)
    
    context = {
        'object': contract,
        'contract': contract,
        'change_logs': change_logs,
        'page_title': 'スタッフ契約 変更履歴一覧',
        'back_url_name': 'contract:staff_contract_detail',
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
            # 「承認する」アクションは「申請中」からのみ可能
            if contract.contract_status == Constants.CONTRACT_STATUS.PENDING:
                try:
                    # TTPを想定する場合、クライアント契約の start_date/end_date を使って期間が6か月超でないかチェック
                    if contract.start_date and contract.end_date:
                        dstart = contract.start_date
                        dend = contract.end_date
                        months = (dend.year - dstart.year) * 12 + (dend.month - dstart.month)
                        if dend.day < dstart.day:
                            months -= 1
                        if months > 6:
                            messages.error(request, '労働者派遣法（第40条の6および第40条の7）により紹介予定派遣の派遣期間は6ヶ月までです')
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
                        pdf_content_dispatch, pdf_filename_dispatch, document_title_dispatch = generate_dispatch_notification_pdf(contract, request.user, issued_at)
                        if not pdf_content_dispatch:
                            raise Exception("派遣通知書のPDF生成に失敗しました。")

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
                            action='dispatch_notification_issue',
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
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_approve(request, pk):
    """スタッフ契約の承認ステータスを更新する"""
    contract = get_object_or_404(StaffContract, pk=pk)
    if request.method == 'POST':
        is_approved = request.POST.get('is_approved')
        if is_approved:
            if contract.contract_status == Constants.CONTRACT_STATUS.PENDING:
                from django.core.exceptions import ValidationError
                try:
                    # 最低賃金チェック
                    contract.validate_minimum_wage()

                    contract.contract_number = generate_staff_contract_number(contract)
                    contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
                    contract.approved_at = timezone.now()
                    contract.approved_by = request.user
                    contract.save()
                    messages.success(request, f'契約「{contract.contract_name}」を承認済にしました。契約番号: {contract.contract_number}')
                except ValueError as e:
                    messages.error(request, f'契約番号の採番に失敗しました。理由: {e}')
                except ValidationError as e:
                    messages.error(request, f'承認できませんでした。{e.message}')
                    return redirect('contract:staff_contract_detail', pk=contract.pk)
            else:
                messages.error(request, 'このステータスからは承認できません。')
        else:
            if int(contract.contract_status) >= int(Constants.CONTRACT_STATUS.APPROVED):
                # 承認解除時も過去の発行履歴は削除しない
                contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                contract.contract_number = None
                contract.approved_at = None
                contract.approved_by = None
                # 発行日時/発行者はクリアするが、print_history レコードとPDFは保持する
                contract.issued_at = None
                contract.issued_by = None
                # （スタッフ契約に見積フィールドは通常無いが、対称性のため）
                if hasattr(contract, 'quotation_issued_at'):
                    contract.quotation_issued_at = None
                if hasattr(contract, 'quotation_issued_by'):
                    contract.quotation_issued_by = None
                contract.confirmed_at = None
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を作成中に戻しました。（発行履歴は保持されます）')
            else:
                messages.error(request, 'この契約の承認は解除できません。')

    return redirect('contract:staff_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_issue(request, pk):
    """スタッフ契約を発行済にする"""
    contract = get_object_or_404(StaffContract, pk=pk)
    if request.method == 'POST':
        is_issued = 'is_issued' in request.POST
        if is_issued:
            if contract.contract_status == Constants.CONTRACT_STATUS.APPROVED:
                pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)
                if pdf_content:
                    new_print = StaffContractPrint(
                        staff_contract=contract,
                        printed_by=request.user,
                        document_title=document_title,
                        contract_number=contract.contract_number if hasattr(contract, 'contract_number') else None
                    )
                    new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

                    AppLog.objects.create(
                        user=request.user,
                        action='print',
                        model_name='StaffContract',
                        object_id=str(contract.pk),
                        object_repr=f'契約書PDF出力: {contract.contract_name}'
                    )
                    contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
                    contract.issued_at = timezone.now()
                    contract.issued_by = request.user
                    contract.save()
                    messages.success(request, f'契約「{contract.contract_name}」の契約書を発行しました。')
                else:
                    messages.error(request, "契約書の発行に失敗しました。")
        else:
            if contract.contract_status == Constants.CONTRACT_STATUS.ISSUED:
                contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
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
                contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
                contract.confirmed_at = timezone.now()
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を確認しました。')
            else:
                messages.error(request, '確認可能な同意文言が見つかりませんでした。')

        elif action == 'unconfirm':
            contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
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
    contracts_query = StaffContract.objects.filter(
        staff=staff,
        corporate_number__in=approved_corporate_numbers,
        contract_status__in=[Constants.CONTRACT_STATUS.ISSUED, Constants.CONTRACT_STATUS.CONFIRMED]
    ).select_related('staff').order_by('-start_date')

    # ページネーション
    paginator = Paginator(contracts_query, 20) # 1ページあたり20件
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 同意状況とPDFの情報を追加
    contracts_with_status = []
    for contract in page_obj:
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
        'page_obj': page_obj,
        'title': 'スタッフ契約確認',
        'CONTRACT_STATUS': Constants.CONTRACT_STATUS,
    }
    return render(request, 'contract/staff_contract_confirm_list.html', context)


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

        contracts_with_status.append({
            'contract': contract,
            'latest_contract_pdf': latest_contract_pdf,
            'quotation_pdf': quotation_pdf,
            'teishokubi_notification_pdf': teishokubi_notification_pdf,
            'dispatch_notification_pdf': dispatch_notification_pdf,
        })

    context = {
        'contracts_with_status': contracts_with_status,
        'page_obj': page_obj,
        'title': 'クライアント契約確認',
    }
    return render(request, 'contract/client_contract_confirm_list.html', context)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_pdf(request, pk):
    """スタッフ契約書のPDFを生成して返す"""
    contract = get_object_or_404(StaffContract, pk=pk)

    # 承認済みの場合は発行済みに更新
    if contract.contract_status == Constants.CONTRACT_STATUS.APPROVED:
        contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
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
    pdf_content, pdf_filename, document_title = generate_dispatch_ledger_pdf(
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
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_teishokubi_notification(request, pk):
    """クライアント契約の抵触日通知書を発行する"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if int(contract.contract_status) < int(Constants.CONTRACT_STATUS.APPROVED) or contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の抵触日通知書は共有できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # 派遣情報および派遣先事業所の抵触日の存在チェック
    haken_info = getattr(contract, 'haken_info', None)
    if not haken_info or not haken_info.haken_office or not haken_info.haken_office.haken_jigyosho_teishokubi:
        messages.error(request, '派遣事業所の抵触日が設定されていません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_teishokubi_notification_pdf(contract, request.user, issued_at)

    if pdf_content:
        new_print = ClientContractPrint(
            client_contract=contract,
            printed_by=request.user,
            printed_at=issued_at,
            print_type=ClientContractPrint.PrintType.TEISHOKUBI_NOTIFICATION,
            document_title=document_title,
            contract_number=contract.contract_number
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        # 抵触日通知書の共有日時/共有者を契約に記録
        contract.teishokubi_notification_issued_at = issued_at
        contract.teishokubi_notification_issued_by = request.user
        contract.save()

        AppLog.objects.create(
            user=request.user,
            action='teishokubi_notification_issue',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'抵触日通知書PDF出力: {contract.contract_name}'
        )
        messages.success(request, f'契約「{contract.contract_name}」の抵触日通知書を共有しました。')
    else:
        messages.error(request, "抵触日通知書のPDFの生成に失敗しました。")

    return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_teishokubi_notification_pdf(request, pk):
    """クライアント契約の抵触日通知書のPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の抵触日通知書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # 派遣情報および派遣先事業所の抵触日の存在チェック
    haken_info = getattr(contract, 'haken_info', None)
    if not haken_info or not haken_info.haken_office or not haken_info.haken_office.haken_jigyosho_teishokubi:
        messages.error(request, '派遣事業所の抵触日が設定されていません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_teishokubi_notification_pdf(
        contract, request.user, issued_at
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "抵触日通知書のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_dispatch_notification(request, pk):
    """クライアント契約の派遣通知書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の派遣通知書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_dispatch_notification_pdf(
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
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_export(request):
    """スタッフ契約データのエクスポート（CSV/Excel）"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    staff_filter = request.GET.get('staff', '')
    employment_type_filter = request.GET.get('employment_type', '')
    date_filter = request.GET.get('date_filter', '')
    has_international_filter = request.GET.get('has_international', '')
    has_disability_filter = request.GET.get('has_disability', '')
    format_type = request.GET.get('format', 'csv')

    contracts = StaffContract.objects.select_related('staff', 'employment_type').all()

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
    if employment_type_filter:
        contracts = contracts.filter(employment_type_id=employment_type_filter)
    if has_international_filter:
        contracts = contracts.filter(staff__international__isnull=False)
    if has_disability_filter:
        contracts = contracts.filter(staff__disability__isnull=False)
    
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


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_assignment_view(request, pk):
    """クライアント契約へのスタッフ契約割当画面"""
    client_contract = get_object_or_404(ClientContract, pk=pk)

    if client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, 'この契約は作成中でないため、割当できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # 既に割り当て済みのスタッフ契約IDを取得
    assigned_staff_contract_ids = client_contract.staff_contracts.values_list('id', flat=True)

    # 期間が重複し、まだ割り当てられていないスタッフ契約を検索
    staff_contracts = StaffContract.objects.select_related('staff', 'employment_type').filter(
        Q(end_date__gte=client_contract.start_date) | Q(end_date__isnull=True),
        start_date__lte=client_contract.end_date if client_contract.end_date else date.max
    ).exclude(id__in=assigned_staff_contract_ids)

    context = {
        'client_contract': client_contract,
        'assignable_contracts': staff_contracts,
    }
    return render(request, 'contract/staff_assignment_list.html', context)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_assignment_view(request, pk):
    """スタッフ契約へのクライアント契約割当画面"""
    staff_contract = get_object_or_404(StaffContract, pk=pk)

    if staff_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, 'この契約は作成中でないため、割当できません。')
        return redirect('contract:staff_contract_detail', pk=pk)

    # 既に割り当て済みのクライアント契約IDを取得
    assigned_client_contract_ids = staff_contract.client_contracts.values_list('id', flat=True)

    # 期間が重複し、まだ割り当てられていないクライアント契約を検索
    client_contracts = ClientContract.objects.select_related('client', 'haken_info__ttp_info').filter(
        Q(end_date__gte=staff_contract.start_date) | Q(end_date__isnull=True),
        start_date__lte=staff_contract.end_date if staff_contract.end_date else date.max
    ).exclude(id__in=assigned_client_contract_ids)

    context = {
        'staff_contract': staff_contract,
        'assignable_contracts': client_contracts,
    }
    return render(request, 'contract/client_assignment_list.html', context)


@login_required
def client_assignment_confirm(request):
    """クライアント割当の確認画面を表示するビュー（スタッフ契約からクライアント契約を割り当てる場合）"""
    if request.method == 'POST':
        client_contract_id = request.POST.get('client_contract_id')
        staff_contract_id = request.POST.get('staff_contract_id')

        client_contract = get_object_or_404(ClientContract, pk=client_contract_id)
        staff_contract = get_object_or_404(StaffContract, pk=staff_contract_id)

        # ステータスチェック
        if client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT or \
           staff_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
            messages.error(request, '作成中の契約間でのみ割当が可能です。')
            return redirect('contract:staff_contract_detail', pk=staff_contract_id)

        # 日雇派遣の警告メッセージ判定
        show_daily_dispatch_warning = False
        if (client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and
            client_contract.duration and client_contract.duration <= 30 and
            hasattr(client_contract, 'haken_info') and client_contract.haken_info and 
            client_contract.haken_info.limit_indefinite_or_senior == Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED):
            
            # 職種が「派遣政令業務」未設定の場合
            job_category_not_specified = (not client_contract.job_category or 
                                        not client_contract.job_category.jobs_seirei)
            
            # スタッフが60歳未満かつ有期雇用の場合
            staff_under_60_and_fixed_term = False
            if staff_contract.staff and staff_contract.staff.birth_date:
                # 割当開始日時点での年齢を計算
                assignment_start_date = max(client_contract.start_date, staff_contract.start_date)
                age_at_assignment = assignment_start_date.year - staff_contract.staff.birth_date.year - \
                    ((assignment_start_date.month, assignment_start_date.day) < 
                     (staff_contract.staff.birth_date.month, staff_contract.staff.birth_date.day))
                staff_under_60_and_fixed_term = (age_at_assignment < 60 and 
                                                (staff_contract.employment_type and staff_contract.employment_type.is_fixed_term))
            else:
                # 生年月日が不明な場合は60歳未満として扱う
                staff_under_60_and_fixed_term = (staff_contract.employment_type and staff_contract.employment_type.is_fixed_term)
            
            # すべての条件が満たされた場合に警告を表示
            if job_category_not_specified and staff_under_60_and_fixed_term:
                show_daily_dispatch_warning = True

        context = {
            'client_contract': client_contract,
            'staff_contract': staff_contract,
            'from_view': 'staff',
            'show_daily_dispatch_warning': show_daily_dispatch_warning,
        }

        return render(request, 'contract/client_assignment_confirm.html', context)

    # POST以外はトップページにリダイレクト
    return redirect('contract:contract_index')


@login_required
def staff_assignment_confirm(request):
    """スタッフ割当の確認画面を表示するビュー（クライアント契約からスタッフ契約を割り当てる場合）"""
    if request.method == 'POST':
        client_contract_id = request.POST.get('client_contract_id')
        staff_contract_id = request.POST.get('staff_contract_id')

        client_contract = get_object_or_404(ClientContract, pk=client_contract_id)
        staff_contract = get_object_or_404(StaffContract, pk=staff_contract_id)

        # ステータスチェック
        if client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT or \
           staff_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
            messages.error(request, '作成中の契約間でのみ割当が可能です。')
            return redirect('contract:client_contract_detail', pk=client_contract_id)

        # 日雇派遣の警告メッセージ判定
        show_daily_dispatch_warning = False
        if (client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and
            client_contract.duration and client_contract.duration <= 30 and
            hasattr(client_contract, 'haken_info') and client_contract.haken_info and 
            client_contract.haken_info.limit_indefinite_or_senior == Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED):
            
            # 職種が「派遣政令業務」未設定の場合
            job_category_not_specified = (not client_contract.job_category or 
                                        not client_contract.job_category.jobs_seirei)
            
            # スタッフが60歳未満かつ有期雇用の場合
            staff_under_60_and_fixed_term = False
            if staff_contract.staff and staff_contract.staff.birth_date:
                # 割当開始日時点での年齢を計算
                assignment_start_date = max(client_contract.start_date, staff_contract.start_date)
                age_at_assignment = assignment_start_date.year - staff_contract.staff.birth_date.year - \
                    ((assignment_start_date.month, assignment_start_date.day) < 
                     (staff_contract.staff.birth_date.month, staff_contract.staff.birth_date.day))
                staff_under_60_and_fixed_term = (age_at_assignment < 60 and 
                                                (staff_contract.employment_type and staff_contract.employment_type.is_fixed_term))
            else:
                # 生年月日が不明な場合は60歳未満として扱う
                staff_under_60_and_fixed_term = (staff_contract.employment_type and staff_contract.employment_type.is_fixed_term)
            
            # すべての条件が満たされた場合に警告を表示
            if job_category_not_specified and staff_under_60_and_fixed_term:
                show_daily_dispatch_warning = True

        context = {
            'client_contract': client_contract,
            'staff_contract': staff_contract,
            'from_view': 'client',
            'show_daily_dispatch_warning': show_daily_dispatch_warning,
        }

        return render(request, 'contract/staff_assignment_confirm.html', context)

    # POST以外はトップページにリダイレクト
    return redirect('contract:contract_index')


@login_required
def staff_assignment_confirm_from_create(request):
    """新規スタッフ契約作成後のアサイン確認画面"""
    # セッションから保留中のスタッフ契約情報を取得
    pending_staff_contract = request.session.get('pending_staff_contract')
    if not pending_staff_contract:
        messages.error(request, 'スタッフ契約情報が見つかりません。')
        return redirect('contract:contract_index')

    client_contract_id = pending_staff_contract.get('client_contract_id')
    form_data = pending_staff_contract.get('form_data')
    from_view = pending_staff_contract.get('from_view', 'client')

    try:
        client_contract = get_object_or_404(ClientContract, pk=client_contract_id)
    except:
        messages.error(request, 'クライアント契約が見つかりません。')
        # セッションをクリア
        if 'pending_staff_contract' in request.session:
            del request.session['pending_staff_contract']
        return redirect('contract:contract_index')

    # ステータスチェック
    if client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, '作成中のクライアント契約でのみ割当が可能です。')
        # セッションをクリア
        if 'pending_staff_contract' in request.session:
            del request.session['pending_staff_contract']
        return redirect('contract:client_contract_detail', pk=client_contract_id)

    # セッションデータからフォームデータを復元
    restored_form_data = {}
    for key, value in form_data.items():
        if key == 'staff' and value:
            try:
                restored_form_data[key] = Staff.objects.get(pk=value)
            except Staff.DoesNotExist:
                messages.error(request, 'スタッフが見つかりません。')
                if 'pending_staff_contract' in request.session:
                    del request.session['pending_staff_contract']
                return redirect('contract:contract_index')
        elif key == 'employment_type' and value and value != 'None':
            try:
                from apps.master.models import EmploymentType
                restored_form_data[key] = EmploymentType.objects.get(pk=value)
            except EmploymentType.DoesNotExist:
                restored_form_data[key] = None
        elif key == 'job_category' and value and value != 'None':
            try:
                from apps.master.models import JobCategory
                restored_form_data[key] = JobCategory.objects.get(pk=value)
            except JobCategory.DoesNotExist:
                restored_form_data[key] = None
        elif key == 'contract_pattern' and value and value != 'None':
            try:
                from apps.master.models import ContractPattern
                restored_form_data[key] = ContractPattern.objects.get(pk=value)
            except ContractPattern.DoesNotExist:
                restored_form_data[key] = None
        elif key in ['start_date', 'end_date'] and value:
            from datetime import datetime
            if isinstance(value, str):
                restored_form_data[key] = datetime.fromisoformat(value).date()
            else:
                restored_form_data[key] = value
        else:
            restored_form_data[key] = value

    # フォームデータから仮のスタッフ契約オブジェクトを作成（保存はしない）
    from .forms import StaffContractForm
    form = StaffContractForm(restored_form_data)
    if form.is_valid():
        staff_contract = form.save(commit=False)
        # 必要な追加設定
        staff_contract.created_by = request.user
        staff_contract.updated_by = request.user
        staff_contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
        staff_contract.contract_number = None
        
        # 雇用形態が設定されていない場合、スタッフの現在の雇用形態を設定
        if not staff_contract.employment_type and staff_contract.staff and staff_contract.staff.employment_type:
            staff_contract.employment_type = staff_contract.staff.employment_type
    else:
        messages.error(request, 'スタッフ契約データに問題があります。')
        if 'pending_staff_contract' in request.session:
            del request.session['pending_staff_contract']
        return redirect('contract:contract_index')

    # 日雇派遣の警告メッセージ判定
    show_daily_dispatch_warning = False
    if (client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and
        client_contract.duration and client_contract.duration <= 30 and
        hasattr(client_contract, 'haken_info') and client_contract.haken_info and 
        client_contract.haken_info.limit_indefinite_or_senior == Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED):
        
        # 職種が「派遣政令業務」未設定の場合
        job_category_not_specified = (not client_contract.job_category or 
                                    not client_contract.job_category.jobs_seirei)
        
        # スタッフが60歳未満かつ有期雇用の場合
        staff_under_60_and_fixed_term = False
        if staff_contract.staff and staff_contract.staff.birth_date:
            # 割当開始日時点での年齢を計算
            assignment_start_date = max(client_contract.start_date, staff_contract.start_date)
            age_at_assignment = assignment_start_date.year - staff_contract.staff.birth_date.year - \
                ((assignment_start_date.month, assignment_start_date.day) < 
                 (staff_contract.staff.birth_date.month, staff_contract.staff.birth_date.day))
            staff_under_60_and_fixed_term = (age_at_assignment < 60 and 
                                            (staff_contract.employment_type and staff_contract.employment_type.is_fixed_term))
        else:
            # 生年月日が不明な場合は60歳未満として扱う
            staff_under_60_and_fixed_term = (staff_contract.employment_type and staff_contract.employment_type.is_fixed_term)
        
        # すべての条件が満たされた場合に警告を表示
        if job_category_not_specified and staff_under_60_and_fixed_term:
            show_daily_dispatch_warning = True

    context = {
        'client_contract': client_contract,
        'staff_contract': staff_contract,
        'from_view': from_view,
        'from_create': True,  # 新規作成からの遷移であることを示すフラグ
        'show_daily_dispatch_warning': show_daily_dispatch_warning,
    }

    return render(request, 'contract/staff_assignment_confirm.html', context)



@login_required
def create_contract_assignment_view(request):
    """契約アサインを作成するビュー"""
    if request.method == 'POST':
        client_contract_id = request.POST.get('client_contract_id')
        staff_contract_id = request.POST.get('staff_contract_id')
        from_view = request.POST.get('from')
        from_create = request.POST.get('from_create') == 'true'  # 新規作成からの遷移かどうか

        client_contract = get_object_or_404(ClientContract, pk=client_contract_id)
        
        # 新規作成の場合はスタッフ契約をまだ取得しない
        if not from_create:
            staff_contract = get_object_or_404(StaffContract, pk=staff_contract_id)

        # 新規作成からの場合の処理
        if from_create:
            # セッションから保留中のスタッフ契約情報を取得
            pending_staff_contract = request.session.get('pending_staff_contract')
            if not pending_staff_contract:
                messages.error(request, 'スタッフ契約情報が見つかりません。')
                return redirect('contract:contract_index')
            
            form_data = pending_staff_contract.get('form_data')
            
            # セッションデータからフォームデータを復元
            restored_form_data = {}
            for key, value in form_data.items():
                if key == 'staff' and value:
                    try:
                        restored_form_data[key] = Staff.objects.get(pk=value)
                    except Staff.DoesNotExist:
                        messages.error(request, 'スタッフが見つかりません。')
                        return redirect('contract:contract_index')
                elif key == 'employment_type' and value and value != 'None':
                    try:
                        from apps.master.models import EmploymentType
                        restored_form_data[key] = EmploymentType.objects.get(pk=value)
                    except EmploymentType.DoesNotExist:
                        restored_form_data[key] = None
                elif key == 'job_category' and value and value != 'None':
                    try:
                        from apps.master.models import JobCategory
                        restored_form_data[key] = JobCategory.objects.get(pk=value)
                    except JobCategory.DoesNotExist:
                        restored_form_data[key] = None
                elif key == 'contract_pattern' and value and value != 'None':
                    try:
                        from apps.master.models import ContractPattern
                        restored_form_data[key] = ContractPattern.objects.get(pk=value)
                    except ContractPattern.DoesNotExist:
                        restored_form_data[key] = None
                elif key in ['start_date', 'end_date'] and value:
                    from datetime import datetime
                    if isinstance(value, str):
                        restored_form_data[key] = datetime.fromisoformat(value).date()
                    else:
                        restored_form_data[key] = value
                else:
                    restored_form_data[key] = value

            # スタッフ契約を作成
            from .forms import StaffContractForm
            form = StaffContractForm(restored_form_data)
            if form.is_valid():
                staff_contract = form.save(commit=False)
                staff_contract.created_by = request.user
                staff_contract.updated_by = request.user
                staff_contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
                staff_contract.contract_number = None
                
                # 雇用形態が設定されていない場合、スタッフの現在の雇用形態を設定
                if not staff_contract.employment_type and staff_contract.staff and staff_contract.staff.employment_type:
                    staff_contract.employment_type = staff_contract.staff.employment_type
                
                staff_contract.save()
                
                # 作成されたスタッフ契約のIDを更新
                staff_contract_id = staff_contract.pk
                staff_contract = get_object_or_404(StaffContract, pk=staff_contract_id)
            else:
                messages.error(request, 'スタッフ契約の作成に失敗しました。')
                return redirect('contract:contract_index')
            
            # セッションをクリア
            del request.session['pending_staff_contract']

        # ステータスチェック
        if client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT or \
           staff_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
            messages.error(request, '作成中の契約間でのみ割当が可能です。')
            if from_view == 'client':
                return redirect('contract:client_contract_detail', pk=client_contract_id)
            else:
                return redirect('contract:staff_contract_detail', pk=staff_contract_id)

        from django.core.exceptions import ValidationError
        try:
            # 既に存在するかチェック
            if ContractAssignment.objects.filter(client_contract=client_contract, staff_contract=staff_contract).exists():
                messages.info(request, 'この割当は既に存在します。')
            else:
                with transaction.atomic():
                    assignment = ContractAssignment(
                        client_contract=client_contract,
                        staff_contract=staff_contract,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    # バリデーションを実行
                    assignment.full_clean()
                    assignment.save()
                    success_message = '契約の割当が完了しました。'
                    sync_messages = []
                    # 業務内容の同期処理
                    # Note: HTMLのロジック情報にもこの旨を追記しておくこと
                    if not client_contract.business_content and staff_contract.business_content:
                        client_contract.business_content = staff_contract.business_content
                        client_contract.save()
                        sync_messages.append('クライアント契約の業務内容をスタッフ契約の業務内容で更新しました。')
                    elif client_contract.business_content and not staff_contract.business_content:
                        staff_contract.business_content = client_contract.business_content
                        staff_contract.save()
                        sync_messages.append('スタッフ契約の業務内容をクライアント契約の業務内容で更新しました。')

                    # 就業場所の同期処理
                    client_haken_info = getattr(client_contract, 'haken_info', None)
                    if client_haken_info:
                        if not client_haken_info.work_location and staff_contract.work_location:
                            client_haken_info.work_location = staff_contract.work_location
                            client_haken_info.save()
                            sync_messages.append('クライアント契約の派遣の就業場所をスタッフ契約の就業場所で更新しました。')
                        elif client_haken_info.work_location and not staff_contract.work_location:
                            staff_contract.work_location = client_haken_info.work_location
                            staff_contract.save()
                            sync_messages.append('スタッフ契約の就業場所をクライアント契約の派遣の就業場所で更新しました。')

                    if sync_messages:
                        success_message = f'{success_message}（{" ".join(sync_messages)}）'
                    messages.success(request, success_message)

        except ValidationError as e:
            # messages.error(request, f'割当に失敗しました。理由：{e.message_dict}')
            # ToDo: a better way to flatten the error messages
            error_messages = []
            for field, errors in e.message_dict.items():
                error_messages.extend(errors)
            messages.error(request, f'割当に失敗しました。理由：{" ".join(error_messages)}')

        except Exception as e:
            messages.error(request, f'割当処理中に予期せぬエラーが発生しました: {e}')

        # 元の画面にリダイレクト
        if from_view == 'client':
            return redirect('contract:client_contract_detail', pk=client_contract_id)
        elif from_view == 'staff':
            return redirect('contract:staff_contract_detail', pk=staff_contract_id)

    return redirect('contract:contract_index')


@login_required
@require_POST
def clear_assignment_session(request):
    """アサインセッションをクリアしてリダイレクト"""
    # セッションから保留中のスタッフ契約情報をクリア
    if 'pending_staff_contract' in request.session:
        del request.session['pending_staff_contract']
    
    # リダイレクト先を取得
    redirect_to = request.POST.get('redirect_to')
    if redirect_to:
        return redirect(redirect_to)
    
    return redirect('contract:contract_index')





@login_required
@require_POST
def delete_contract_assignment(request, assignment_pk):
    """契約アサインを削除するビュー"""
    assignment = get_object_or_404(
        ContractAssignment.objects.select_related('client_contract', 'staff_contract'),
        pk=assignment_pk
    )
    client_contract = assignment.client_contract
    staff_contract = assignment.staff_contract

    # どの詳細画面に戻るかを判断するためのクエリパラメータ
    redirect_to = request.GET.get('from', 'client')

    # クライアント契約が「作成中」でない場合は削除させない
    if client_contract.contract_status != Constants.CONTRACT_STATUS.DRAFT:
        messages.error(request, 'このアサインは解除できません。クライアント契約が「作成中」ではありません。')
        if redirect_to == 'staff':
            return redirect('contract:staff_contract_detail', pk=staff_contract.pk)
        return redirect('contract:client_contract_detail', pk=client_contract.pk)

    try:
        assignment.delete()
        messages.success(request, '契約アサインを解除しました。')
    except Exception as e:
        messages.error(request, f'解除処理中にエラーが発生しました: {e}')

    # 元の画面にリダイレクト
    if redirect_to == 'staff':
        return redirect('contract:staff_contract_detail', pk=staff_contract.pk)

    return redirect('contract:client_contract_detail', pk=client_contract.pk)

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