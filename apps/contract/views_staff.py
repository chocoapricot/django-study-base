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
from .utils import generate_contract_pdf_content, generate_quotation_pdf, generate_client_contract_number, generate_staff_contract_number, generate_teishokubi_notification_pdf, generate_haken_notification_pdf, generate_haken_motokanri_pdf
from .resources import ClientContractResource, StaffContractResource
from .models import ContractAssignment
from django.urls import reverse

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

    # 契約アサイン詳細からの遷移を判定
    from_assignment = request.GET.get('from') == 'assignment'
    assignment_pk = request.GET.get('assignment_pk', '')
    if assignment_pk:
        try:
            assignment_pk = int(assignment_pk)
        except (ValueError, TypeError):
            assignment_pk = None
            from_assignment = False

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

    # 発行履歴を取得（スタッフ契約書 + 契約アサインの就業条件明示書）
    from .models import ContractAssignmentHakenPrint
    
    # スタッフ契約書の発行履歴
    staff_contract_prints = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at', '-pk')
    
    # 契約アサインの就業条件明示書発行履歴
    assignment_haken_prints = ContractAssignmentHakenPrint.objects.filter(
        contract_assignment__staff_contract=contract,
        print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
    ).select_related('contract_assignment__client_contract__client').order_by('-printed_at', '-pk')
    
    # 両方の履歴を統合してソート
    all_issue_history = []
    
    # スタッフ契約書の履歴を追加
    for print_record in staff_contract_prints:
        all_issue_history.append({
            'type': 'staff_contract',
            'record': print_record,
            'printed_at': print_record.printed_at,
            'document_title': print_record.document_title,
            'contract_number': print_record.contract_number,
            'file_hash': print_record.file_hash,
            'printed_by': print_record.printed_by,
            'pk': print_record.pk,
        })
    
    # 契約アサインの就業条件明示書履歴を追加
    for print_record in assignment_haken_prints:
        all_issue_history.append({
            'type': 'assignment_haken',
            'record': print_record,
            'printed_at': print_record.printed_at,
            'document_title': print_record.document_title,
            'contract_number': print_record.contract_number,
            'file_hash': print_record.file_hash,
            'printed_by': print_record.printed_by,
            'pk': print_record.pk,
            'client_name': print_record.contract_assignment.client_contract.client.name,
        })
    
    # 発行日時でソート（新しい順）
    all_issue_history.sort(key=lambda x: x['printed_at'], reverse=True)
    
    issue_history_count = len(all_issue_history)
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
        'from_assignment': from_assignment,
        'assignment_pk': assignment_pk,
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

@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_issue_history_list(request, pk):
    """スタッフ契約の発行履歴一覧（スタッフ契約書 + 契約アサインの就業条件明示書）"""
    from .models import ContractAssignmentHakenPrint
    
    contract = get_object_or_404(StaffContract, pk=pk)

    # スタッフ契約書の発行履歴
    staff_contract_prints = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at', '-pk')
    
    # 契約アサインの就業条件明示書発行履歴
    assignment_haken_prints = ContractAssignmentHakenPrint.objects.filter(
        contract_assignment__staff_contract=contract,
        print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
    ).select_related('contract_assignment__client_contract__client').order_by('-printed_at', '-pk')
    
    # 両方の履歴を統合してソート
    all_issue_history = []
    
    # スタッフ契約書の履歴を追加
    for print_record in staff_contract_prints:
        all_issue_history.append({
            'type': 'staff_contract',
            'record': print_record,
            'printed_at': print_record.printed_at,
            'document_title': print_record.document_title,
            'contract_number': print_record.contract_number,
            'file_hash': print_record.file_hash,
            'printed_by': print_record.printed_by,
            'pk': print_record.pk,
        })
    
    # 契約アサインの就業条件明示書履歴を追加
    for print_record in assignment_haken_prints:
        all_issue_history.append({
            'type': 'assignment_haken',
            'record': print_record,
            'printed_at': print_record.printed_at,
            'document_title': print_record.document_title,
            'contract_number': print_record.contract_number,
            'file_hash': print_record.file_hash,
            'printed_by': print_record.printed_by,
            'pk': print_record.pk,
            'client_name': print_record.contract_assignment.client_contract.client.name,
        })
    
    # 発行日時でソート（新しい順）
    all_issue_history.sort(key=lambda x: x['printed_at'], reverse=True)
    
    # ページネーション
    paginator = Paginator(all_issue_history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'contract': contract,
        'page_obj': page_obj,
    }
    return render(request, 'contract/staff_contract_issue_history_list.html', context)

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
                
                # 関連する契約アサインの就業条件明示書発行・確認状態をリセット
                # （発行履歴は保持する）
                contract.contractassignment_set.update(
                    issued_at=None,
                    confirmed_at=None
                )
                
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
                    
                    # 関連する契約アサインの就業条件明示書確認状態もリセット（再発行時）
                    contract.contractassignment_set.update(
                        employment_conditions_confirmed_at=None
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
                # 関連する契約アサインの就業条件明示書確認状態もリセット（未発行時）
                contract.contractassignment_set.update(
                    employment_conditions_confirmed_at=None
                )
                
                contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
                contract.issued_at = None
                contract.issued_by = None
                
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を承認済に戻しました。')
    return redirect('contract:staff_contract_detail', pk=contract.pk)

@login_required
def staff_contract_confirm_list(request):
    """スタッフ契約確認一覧（スタッフ契約書 + 就業条件明示書）"""
    from apps.connect.models import ConnectStaff
    from apps.company.models import Company
    from .models import ContractAssignmentHakenPrint
    
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm_staff_contract':
            contract_id = request.POST.get('contract_id')
            contract = get_object_or_404(StaffContract, pk=contract_id)
            
            # スタッフ同意文言の処理
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
                # スタッフ契約のステータスを更新
                contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
                contract.confirmed_at = timezone.now()
                contract.save()
                messages.success(request, f'スタッフ契約書「{contract.contract_name}」を確認しました。')
            else:
                messages.error(request, '確認可能な同意文言が見つかりませんでした。')
                
        elif action == 'confirm_employment_conditions':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(ContractAssignment, pk=assignment_id)
            
            # 就業条件明示書の確認
            assignment.confirmed_at = timezone.now()
            assignment.save()
            messages.success(request, f'就業条件明示書を確認しました。')

        return redirect('contract:staff_contract_confirm_list')

    try:
        staff = Staff.objects.get(email=user.email)
    except Staff.DoesNotExist:
        staff = None

    if not staff:
        context = {
            'confirm_items': [],
            'title': 'スタッフ契約確認',
        }
        return render(request, 'contract/staff_contract_confirm_list.html', context)

    # 会社の法人番号を取得
    company = Company.objects.first()
    if not company or not company.corporate_number:
        context = {
            'confirm_items': [],
            'title': 'スタッフ契約確認',
        }
        return render(request, 'contract/staff_contract_confirm_list.html', context)

    # 承認済みの接続スタッフを確認
    connect_staff = ConnectStaff.objects.filter(
        corporate_number=company.corporate_number,
        email=user.email,
        status='approved'
    ).first()

    if not connect_staff:
        context = {
            'confirm_items': [],
            'title': 'スタッフ契約確認',
        }
        return render(request, 'contract/staff_contract_confirm_list.html', context)

    confirm_items = []
    
    # 1. スタッフ契約書の確認対象を取得
    staff_contracts = StaffContract.objects.filter(
        staff=staff,
        corporate_number=company.corporate_number,
        contract_status__in=[Constants.CONTRACT_STATUS.ISSUED, Constants.CONTRACT_STATUS.CONFIRMED]
    ).order_by('-start_date')
    
    for contract in staff_contracts:
        latest_pdf = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at').first()
        confirm_items.append({
            'type': 'staff_contract',
            'contract': contract,
            'assignment': None,
            'latest_pdf': latest_pdf,
            'confirmed_at': contract.confirmed_at,
            'is_confirmed': contract.contract_status == Constants.CONTRACT_STATUS.CONFIRMED,
            'sort_date': latest_pdf.printed_at if latest_pdf else contract.created_at,
        })
    
    # 2. 就業条件明示書の確認対象を取得
    assignments = ContractAssignment.objects.filter(
        staff_contract__staff=staff,
        staff_contract__contract_status__in=[Constants.CONTRACT_STATUS.ISSUED, Constants.CONTRACT_STATUS.CONFIRMED],  # スタッフ契約が発行済みまたは確認済み
        client_contract__client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH
    ).select_related(
        'client_contract__client',
        'staff_contract'
    ).order_by('-assigned_at')
    
    for assignment in assignments:
        # スタッフ契約の法人番号が自社と一致するかチェック
        if assignment.staff_contract.corporate_number != company.corporate_number:
            continue
            
        # 就業条件明示書が発行済みかチェック（issued_atがあるかで判定）
        if assignment.issued_at:
            # 最新の発行履歴を取得
            latest_haken_print = ContractAssignmentHakenPrint.objects.filter(
                contract_assignment=assignment,
                print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
            ).order_by('-printed_at').first()
            confirm_items.append({
                'type': 'employment_conditions',
                'contract': assignment.staff_contract,
                'assignment': assignment,
                'latest_pdf': latest_haken_print,
                'confirmed_at': assignment.confirmed_at,
                'is_confirmed': assignment.confirmed_at is not None,
                'sort_date': assignment.issued_at,  # 発行日時でソート
            })
    
    # 発行日時でソート（新しい順）
    confirm_items.sort(key=lambda x: x['sort_date'], reverse=True)
    
    # ページネーション
    paginator = Paginator(confirm_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'confirm_items': page_obj,
        'page_obj': page_obj,
        'title': 'スタッフ契約確認',
        'CONTRACT_STATUS': Constants.CONTRACT_STATUS,
    }
    return render(request, 'contract/staff_contract_confirm_list.html', context)

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
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_draft_pdf(request, pk):
    """スタッフ契約書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(StaffContract, pk=pk)
    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:staff_contract_detail', pk=pk)


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

        # 現在派遣中の契約一覧を取得（未来分も含む、重複期間を除去）
        current_assignments = ContractAssignment.objects.filter(
            staff_contract__staff__email=item.staff_email,
            client_contract__client__corporate_number=item.client_corporate_number,
            client_contract__haken_info__haken_unit__name=item.organization_name,
            client_contract__client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            client_contract__end_date__gte=date.today()  # 終了日が今日以降（未来分も含む）
        ).select_related('client_contract')

        if current_assignments:
            item.is_currently_dispatched = True
            # 重複する契約期間を除去するため、ユニークな期間のセットを作成
            unique_periods = set()
            for assignment in current_assignments:
                period_tuple = (assignment.client_contract.start_date, assignment.client_contract.end_date)
                unique_periods.add(period_tuple)
            
            # ユニークな期間を開始日順でソートして最大5件まで表示
            sorted_periods = sorted(list(unique_periods))[:5]
            item.current_contract_list = []
            for start_date, end_date in sorted_periods:
                item.current_contract_list.append({
                    'contract_start': start_date,
                    'contract_end': end_date,
                })
            item.current_staff_count = len(item.current_contract_list)
        else:
            item.is_currently_dispatched = False
            item.current_contract_list = []
            item.current_staff_count = 0

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

    # チャート用のダミーデータを作成（既存のテンプレートを使用するため）
    if teishokubi_details:
        from datetime import timedelta
        
        # 詳細の開始日の最古と終了日の最新を取得
        earliest_start = min(detail.assignment_start_date for detail in teishokubi_details)
        latest_end = max(detail.assignment_end_date for detail in teishokubi_details)
        
        # 表示期間を計算（詳細の最古開始日から最新終了日まで）
        display_start_date = earliest_start
        display_end_date = latest_end
        
        # ダミーのクライアント契約データ（派遣開始日から最新終了日まで）
        dummy_client_contract = type('obj', (object,), {
            'start_date': teishokubi.dispatch_start_date,
            'end_date': latest_end,
            'client': type('obj', (object,), {'name': '個人抵触日対象'})(),
            'contract_name': '個人抵触日対象'
        })()
        
        # 個人抵触日詳細をスタッフ契約として表示するためのデータ
        teishokubi_staff_contracts = []
        for i, detail in enumerate(teishokubi_details, 1):
            label = f"期間{i}"
            if detail.is_manual:
                label += " (手動)"
            elif detail.is_calculated:
                label += " (算出対象)"
            else:
                label += " (対象外)"
                
            staff_contract = type('obj', (object,), {
                'start_date': detail.assignment_start_date,
                'end_date': detail.assignment_end_date,
                'staff': type('obj', (object,), {
                    'name_last': label,
                    'name_first': ''
                })(),
                'contract_name': label
            })()
            teishokubi_staff_contracts.append(staff_contract)
    else:
        display_start_date = None
        display_end_date = None
        dummy_client_contract = None
        teishokubi_staff_contracts = []

    context = {
        'teishokubi': teishokubi,
        'teishokubi_details': teishokubi_details,
        'staff': staff,
        'client': client,
        'change_logs': change_logs,
        # チャート用のデータ
        'client_contract': dummy_client_contract,
        'existing_assignments': [type('obj', (object,), {'staff_contract': sc})() for sc in teishokubi_staff_contracts],
        'chart_type': 'assignment_confirm',
        # 表示期間
        'display_start_date': display_start_date,
        'display_end_date': display_end_date,
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

@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def view_staff_contract_pdf(request, pk):
    """
    スタッフ契約印刷履歴のPDFをブラウザで表示する
    """
    print_history = get_object_or_404(StaffContractPrint, pk=pk)
    
    if not print_history.pdf_file:
        raise Http404("PDFファイルが見つかりません")
    
    try:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{print_history.pdf_file.name}"'
        return response
    except Exception as e:
        raise Http404(f"PDFファイルの読み込みに失敗しました: {str(e)}")


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def download_staff_contract_pdf(request, pk):
    """Downloads a previously generated staff contract PDF."""
    print_history = get_object_or_404(StaffContractPrint, pk=pk)

    if not print_history.pdf_file:
        raise Http404("PDFファイルが見つかりません")
    
    try:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        filename = os.path.basename(print_history.pdf_file.name)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        raise Http404(f"PDFファイルの読み込みに失敗しました: {str(e)}")