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
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint, ClientContractHaken, ClientContractTtp, ClientContractHakenExempt, StaffContractTeishokubi, StaffContractTeishokubiDetail
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
from .utils import generate_contract_pdf_content, generate_quotation_pdf, generate_client_contract_number, generate_staff_contract_number, generate_teishokubi_notification_pdf, generate_haken_notification_pdf, generate_dispatch_ledger_pdf
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
        from apps.master.models import PhraseTemplate
        from apps.common.constants import Constants
        items = PhraseTemplate.objects.filter(
            is_active=True, 
            title__key=Constants.PHRASE_TEMPLATE_TITLE.CONTRACT_BUSINESS_CONTENT,
            title__is_active=True
        )
        modal_title = '業務内容を選択'
    elif master_type == 'responsibility_degree':
        from apps.system.settings.models import Dropdowns
        items = Dropdowns.objects.filter(category='HAKEN_RESPONSIBILITY_DEGREE', active=True)
        modal_title = '責任の程度を選択'
    else:
        items = []
        modal_title = 'マスター選択'

    if search_query:
        if master_type == 'responsibility_degree':
            items = items.filter(name__icontains=search_query)
        else:
            items = items.filter(content__icontains=search_query)

    # 表示順で並び替え（モデルのMeta.orderingを使用）
    if master_type == 'responsibility_degree':
        items = items.order_by('disp_seq')
    else:
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
def client_staff_assignment_detail_list(request, pk):
    """クライアント契約のスタッフアサイン詳細一覧"""
    contract = get_object_or_404(
        ClientContract.objects.select_related(
            'client', 'job_category', 'contract_pattern', 'payment_site'
        ).prefetch_related(
            Prefetch(
                'contractassignment_set',
                queryset=ContractAssignment.objects.select_related(
                    'staff_contract__staff',
                    'staff_contract__employment_type'
                ).order_by('staff_contract__start_date'),
                to_attr='assigned_assignments'
            )
        ),
        pk=pk
    )

    # 期間の重なりを計算するための処理
    assignments_with_overlap = []
    staff_periods = []  # 統合表示用のスタッフ期間データ
    
    for assignment in contract.assigned_assignments:
        staff_contract = assignment.staff_contract
        
        # クライアント契約とスタッフ契約の期間重なりを計算
        client_start = contract.start_date
        client_end = contract.end_date
        staff_start = staff_contract.start_date
        staff_end = staff_contract.end_date
        
        # 重なり期間の開始日と終了日を計算
        overlap_start = max(client_start, staff_start) if client_start and staff_start else None
        
        if client_end and staff_end:
            overlap_end = min(client_end, staff_end)
        elif client_end:
            overlap_end = client_end
        elif staff_end:
            overlap_end = staff_end
        else:
            overlap_end = None
        
        # 重なりが有効かチェック
        has_overlap = overlap_start and (not overlap_end or overlap_start <= overlap_end)
        
        assignments_with_overlap.append({
            'assignment': assignment,
            'staff_contract': staff_contract,
            'overlap_start': overlap_start,
            'overlap_end': overlap_end,
            'has_overlap': has_overlap,
        })
        
        # 統合表示用のスタッフ期間データを追加
        staff_periods.append({
            'staff_name': f"{staff_contract.staff.name_last} {staff_contract.staff.name_first}",
            'staff_id': staff_contract.staff.id,
            'start_date': staff_start,
            'end_date': staff_end,
            'has_overlap': has_overlap,
            'overlap_start': overlap_start,
            'overlap_end': overlap_end,
            'employment_type': staff_contract.employment_type,
            'has_international': staff_contract.staff.has_international,
            'has_disability': staff_contract.staff.has_disability,
        })
    
    # 統合期間表示用のデータを計算
    period_visual_data = calculate_integrated_period_visual_data(contract, staff_periods)

    context = {
        'contract': contract,
        'assignments_with_overlap': assignments_with_overlap,
        'staff_periods': staff_periods,
        'period_visual_data': period_visual_data,
    }
    return render(request, 'contract/client_staff_assignment_detail_list.html', context)


def calculate_integrated_period_visual_data(contract, staff_periods):
    """統合期間表示用のデータを計算（クライアント契約期間を基準とし、前後の延長部分も表示）"""
    from datetime import date, timedelta
    
    client_start = contract.start_date
    client_end = contract.end_date
    
    if not client_start:
        return {}
    
    # 表示期間はクライアント契約期間を基準とする
    display_start = client_start
    if client_end:
        display_end = client_end
        total_days = (display_end - display_start).days + 1
    else:
        # 無期限の場合は開始日から1年後を表示終了とする
        display_end = client_start + timedelta(days=365)
        total_days = 365
    
    if total_days <= 0:
        total_days = 1  # ゼロ除算を防ぐ
    
    # クライアント契約は15%～85%の範囲に表示（前後に余白を作る）
    client_data = {
        'start_pos': 15,
        'width': 70,
        'start_date': client_start,
        'end_date': client_end,
    }
    
    # 各スタッフの期間データを計算
    staff_data = []
    for i, staff_period in enumerate(staff_periods):
        staff_start = staff_period['start_date']
        staff_end = staff_period['end_date']
        
        if not staff_start:
            continue
        
        # スタッフ契約の前後延長を判定
        extends_before = staff_start < display_start
        extends_after = staff_end and client_end and staff_end > display_end
        extends_after_infinite = not staff_end and client_end  # スタッフが無期限でクライアントに期限がある場合
        
        # 基本的な位置計算（クライアント契約期間内の部分）
        # クライアント契約期間内でのスタッフ契約の開始位置
        if extends_before:
            # 前に延びている場合、クライアント契約開始から計算
            inner_start_pos = 15  # クライアント契約の開始位置
        else:
            # 通常の場合
            days_from_client_start = (staff_start - display_start).days
            inner_start_pos = 15 + (days_from_client_start / total_days * 70)
        
        # クライアント契約期間内でのスタッフ契約の終了位置
        if staff_end:
            if extends_after:
                # 後ろに延びている場合、クライアント契約終了まで
                inner_end_pos = 85  # クライアント契約の終了位置
            else:
                # 通常の場合
                if staff_end <= display_end:
                    days_from_client_start = (staff_end - display_start).days
                    inner_end_pos = 15 + (days_from_client_start / total_days * 70)
                else:
                    inner_end_pos = 85
        else:
            # スタッフ契約が無期限
            inner_end_pos = 85
        
        # 実際の表示位置を計算
        if extends_before:
            visual_start_pos = 5  # 前方延長表示
            visual_width = inner_end_pos - visual_start_pos
            if extends_after or extends_after_infinite:
                visual_width = 90  # 後方にも延長
        else:
            visual_start_pos = inner_start_pos
            if extends_after or extends_after_infinite:
                visual_width = 90 - visual_start_pos  # 後方延長
            else:
                visual_width = inner_end_pos - inner_start_pos
        
        # 境界値チェック
        visual_start_pos = max(0, min(95, visual_start_pos))
        visual_width = max(2, min(100 - visual_start_pos, visual_width))
        
        # 表示用の期間を計算
        display_start_date = staff_start if extends_before else max(staff_start, display_start)
        if staff_end:
            display_end_date = staff_end if (extends_after or extends_after_infinite) else min(staff_end, display_end)
        else:
            display_end_date = None
        
        staff_data.append({
            'staff_name': staff_period['staff_name'],
            'staff_id': staff_period['staff_id'],
            'start_pos': visual_start_pos,
            'width': visual_width,
            'start_date': display_start_date,
            'end_date': display_end_date,
            'original_start': staff_start,
            'original_end': staff_end,
            'extends_before': extends_before,
            'extends_after': extends_after or extends_after_infinite,
            'has_overlap': staff_period['has_overlap'],
            'employment_type': staff_period['employment_type'],
            'has_international': staff_period['has_international'],
            'has_disability': staff_period['has_disability'],
            'row_index': i,
        })
    
    return {
        'client_data': client_data,
        'staff_data': staff_data,
        'display_start': display_start,
        'display_end': display_end,
        'total_days': total_days,
    }


def calculate_period_visual_data(client_start, client_end, staff_start, staff_end):
    """期間の視覚的表示用データを計算"""
    from datetime import date, timedelta
    
    # 表示期間の範囲を決定（最も早い開始日から最も遅い終了日まで）
    all_dates = [d for d in [client_start, client_end, staff_start, staff_end] if d]
    if not all_dates:
        return {
            'client_start_pos': 0, 'client_width': 0,
            'staff_start_pos': 0, 'staff_width': 0,
            'overlap_start_pos': 0, 'overlap_width': 0,
        }
    
    min_date = min(all_dates)
    max_date = max(all_dates)
    
    # 表示期間を少し拡張（最低でも6ヶ月の表示幅を確保）
    display_start = min_date - timedelta(days=30)
    if max_date:
        display_end = max_date + timedelta(days=30)
    else:
        # 無期限契約がある場合は、開始日から1年後を表示終了とする
        display_end = min_date + timedelta(days=365)
    
    # 最低表示期間を確保
    if (display_end - display_start).days < 180:  # 6ヶ月未満の場合
        display_end = display_start + timedelta(days=180)
    
    # 全体の期間（日数）
    total_days = (display_end - display_start).days
    if total_days <= 0:
        total_days = 1  # ゼロ除算を防ぐ
    
    # クライアント契約の位置とサイズ
    client_start_pos = 0
    client_width = 0
    if client_start:
        client_start_pos = ((client_start - display_start).days / total_days * 100)
        if client_end:
            client_width = ((client_end - client_start).days / total_days * 100)
        else:
            # 無期限の場合は表示終了まで
            client_width = ((display_end - client_start).days / total_days * 100)
    
    # スタッフ契約の位置とサイズ
    staff_start_pos = 0
    staff_width = 0
    if staff_start:
        staff_start_pos = ((staff_start - display_start).days / total_days * 100)
        if staff_end:
            staff_width = ((staff_end - staff_start).days / total_days * 100)
        else:
            # 無期限の場合は表示終了まで
            staff_width = ((display_end - staff_start).days / total_days * 100)
    
    # 重なり部分の計算
    overlap_start_pos = 0
    overlap_width = 0
    if client_start and staff_start:
        overlap_start = max(client_start, staff_start)
        
        if client_end and staff_end:
            overlap_end = min(client_end, staff_end)
        elif client_end:
            overlap_end = client_end
        elif staff_end:
            overlap_end = staff_end
        else:
            overlap_end = None  # 両方とも無期限
        
        if not overlap_end or overlap_start <= overlap_end:
            overlap_start_pos = ((overlap_start - display_start).days / total_days * 100)
            if overlap_end:
                overlap_width = ((overlap_end - overlap_start).days / total_days * 100)
            else:
                # 重なり部分が無期限の場合
                overlap_width = ((display_end - overlap_start).days / total_days * 100)
    
    return {
        'client_start_pos': max(0, min(100, client_start_pos)),
        'client_width': max(0, min(100, client_width)),
        'staff_start_pos': max(0, min(100, staff_start_pos)),
        'staff_width': max(0, min(100, staff_width)),
        'overlap_start_pos': max(0, min(100, overlap_start_pos)),
        'overlap_width': max(0, min(100, overlap_width)),
        'display_start': display_start,
        'display_end': display_end,
    }