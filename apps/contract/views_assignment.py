from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.common.constants import Constants
from apps.master.models import ContractPattern, EmploymentType, JobCategory
from apps.staff.models import Staff

from .forms import StaffContractForm, ContractAssignmentConfirmForm, ContractAssignmentHakenForm
from .models import ClientContract, ContractAssignment, StaffContract, ContractAssignmentConfirm, ContractAssignmentHaken


def _calculate_profit_margin(client_contract, staff_contract):
    """
    粗利率を計算する関数
    
    Args:
        client_contract: クライアント契約
        staff_contract: スタッフ契約
        
    Returns:
        dict: 粗利率情報（can_calculate, profit_margin, show_warning）
    """
    # 単位の対応関係を定義（bill_unit -> pay_unit）
    unit_mapping = {
        Constants.BILL_UNIT.HOURLY_RATE: Constants.PAY_UNIT.HOURLY,    # 時間単価 -> 時給
        Constants.BILL_UNIT.DAILY_RATE: Constants.PAY_UNIT.DAILY,      # 日額 -> 日給
        Constants.BILL_UNIT.MONTHLY_RATE: Constants.PAY_UNIT.MONTHLY,  # 月額 -> 月給
    }
    
    # 計算可能かチェック
    can_calculate = (
        client_contract.bill_unit and 
        staff_contract.pay_unit and
        client_contract.contract_amount is not None and
        staff_contract.contract_amount is not None and
        client_contract.bill_unit in unit_mapping and
        unit_mapping[client_contract.bill_unit] == staff_contract.pay_unit
    )
    
    if not can_calculate:
        return {
            'can_calculate': False,
            'profit_margin': None,
            'show_warning': False,
            'client_amount': client_contract.contract_amount,
            'staff_amount': staff_contract.contract_amount,
            'client_unit': client_contract.bill_unit,
            'staff_unit': staff_contract.pay_unit,
        }
    
    # 粗利率計算: (クライアント金額 - スタッフ金額) / クライアント金額 * 100
    client_amount = float(client_contract.contract_amount)
    staff_amount = float(staff_contract.contract_amount)
    
    if client_amount == 0:
        profit_margin = 0
    else:
        profit_margin = ((client_amount - staff_amount) / client_amount) * 100
    
    # 警告表示判定（0%以下の場合）
    show_warning = profit_margin <= 0
    
    return {
        'can_calculate': True,
        'profit_margin': round(profit_margin, 2),
        'show_warning': show_warning,
        'client_amount': client_amount,
        'staff_amount': staff_amount,
        'client_unit': client_contract.bill_unit,
        'staff_unit': staff_contract.pay_unit,
    }


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
    return render(request, 'contract/client_staff_assignment_list.html', context)


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
    return render(request, 'contract/staff_client_assignment_list.html', context)


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

        # 粗利率計算
        profit_margin_info = _calculate_profit_margin(client_contract, staff_contract)

        # 既存の割当済みスタッフ契約を取得（スタッフ名＞開始日でソート）
        existing_assignments = ContractAssignment.objects.filter(
            client_contract=client_contract
        ).select_related('staff_contract__staff', 'staff_contract__employment_type').order_by(
            'staff_contract__staff__name_last', 
            'staff_contract__staff__name_first', 
            'staff_contract__start_date'
        )

        context = {
            'client_contract': client_contract,
            'staff_contract': staff_contract,
            'from_view': 'staff',
            'show_daily_dispatch_warning': show_daily_dispatch_warning,
            'profit_margin_info': profit_margin_info,
            'existing_assignments': existing_assignments,
        }

        return render(request, 'contract/staff_client_assignment_confirm.html', context)

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

        # 粗利率計算
        profit_margin_info = _calculate_profit_margin(client_contract, staff_contract)

        # 既存の割当済みスタッフ契約を取得（スタッフ名＞開始日でソート）
        existing_assignments = ContractAssignment.objects.filter(
            client_contract=client_contract
        ).select_related('staff_contract__staff', 'staff_contract__employment_type').order_by(
            'staff_contract__staff__name_last', 
            'staff_contract__staff__name_first', 
            'staff_contract__start_date'
        )

        context = {
            'client_contract': client_contract,
            'staff_contract': staff_contract,
            'from_view': 'client',
            'show_daily_dispatch_warning': show_daily_dispatch_warning,
            'profit_margin_info': profit_margin_info,
            'existing_assignments': existing_assignments,
        }

        return render(request, 'contract/client_staff_assignment_confirm.html', context)

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

    # 粗利率計算
    profit_margin_info = _calculate_profit_margin(client_contract, staff_contract)

    # 既存の割当済みスタッフ契約を取得（スタッフ名＞開始日でソート）
    existing_assignments = ContractAssignment.objects.filter(
        client_contract=client_contract
    ).select_related('staff_contract__staff', 'staff_contract__employment_type').order_by(
        'staff_contract__staff__name_last', 
        'staff_contract__staff__name_first', 
        'staff_contract__start_date'
    )

    context = {
        'client_contract': client_contract,
        'staff_contract': staff_contract,
        'from_view': from_view,
        'from_create': True,  # 新規作成からの遷移であることを示すフラグ
        'show_daily_dispatch_warning': show_daily_dispatch_warning,
        'profit_margin_info': profit_margin_info,
        'existing_assignments': existing_assignments,
    }

    return render(request, 'contract/client_staff_assignment_confirm.html', context)



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
        elif redirect_to == 'expire_list':
            return redirect('contract:staff_contract_expire_list')
        return redirect('contract:client_contract_detail', pk=client_contract.pk)

    try:
        assignment.delete()
        messages.success(request, '契約アサインを解除しました。')
    except Exception as e:
        messages.error(request, f'解除処理中にエラーが発生しました: {e}')

    # 元の画面にリダイレクト
    if redirect_to == 'staff':
        return redirect('contract:staff_contract_detail', pk=staff_contract.pk)
    elif redirect_to == 'expire_list':
        return redirect('contract:staff_contract_expire_list')

    return redirect('contract:client_contract_detail', pk=client_contract.pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def contract_assignment_detail(request, assignment_pk):
    """
    契約アサイン情報の詳細画面
    クライアント契約とスタッフ契約の両方から参照される共通画面
    """
    from apps.system.logs.models import AppLog
    
    assignment = get_object_or_404(
        ContractAssignment.objects.select_related(
            'client_contract__client',
            'staff_contract__staff',
            'staff_contract__employment_type',
            'client_contract__job_category',
            'staff_contract__job_category'
        ).prefetch_related(
            'client_contract__haken_info__haken_office',
            'client_contract__haken_info__haken_exempt_info'
        ),
        pk=assignment_pk
    )
    
    # 遷移元を判定（URLパラメータを優先、次にリファラーから）
    from_param = request.GET.get('from')
    from_expire_list = from_param == 'expire_list'
    from_client = from_param == 'client'
    from_staff = from_param == 'staff'
    
    # URLパラメータがない場合はリファラーから判定
    if not from_param:
        referer = request.META.get('HTTP_REFERER', '')
        from_client = '/contract/client/' in referer
        from_staff = '/contract/staff/' in referer
    
    # 変更履歴を取得（アサイン作成・削除のログ）
    change_logs = AppLog.objects.filter(
        model_name='ContractAssignment',
        object_id=str(assignment.pk)
    ).select_related('user').order_by('-timestamp')[:10]
    
    # 期間表示用のデータを計算（クライアント契約をベースに前後5日表示）
    from datetime import timedelta
    client_start = assignment.client_contract.start_date
    client_end = assignment.client_contract.end_date
    
    # クライアント契約をベースに表示期間を決定
    if client_start:
        display_start_date = client_start - timedelta(days=5)
        if client_end:
            display_end_date = client_end + timedelta(days=5)
        else:
            # クライアント契約が無期限の場合は開始日から1年後を表示終了とする
            display_end_date = client_start + timedelta(days=365)
    else:
        display_start_date = None
        display_end_date = None
    
    # 派遣情報を取得
    haken_info = getattr(assignment.client_contract, 'haken_info', None)
    
    # 派遣契約かどうかを判定
    is_dispatch_contract = assignment.client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH
    
    # 就業条件明示書の発行状態と履歴を確認
    employment_conditions_issued = False
    employment_conditions_issued_at = None
    employment_conditions_issued_by = None
    haken_print_history = []
    haken_print_history_count = 0
    
    if is_dispatch_contract:
        from .models import ContractAssignmentHakenPrint
        # 発行履歴を取得（最新5件）
        haken_print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        ).select_related('printed_by').order_by('-printed_at')[:5]
        
        # 発行履歴の総数を取得
        haken_print_history_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        ).count()
        
        # 発行状態の判定
        # スタッフ契約がDRAFTまたはPENDINGの場合は常に未発行
        if assignment.staff_contract.contract_status in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
            employment_conditions_issued = False
        else:
            # それ以外の場合は、同じ契約番号の発行履歴があるかで判定
            current_contract_number = assignment.staff_contract.contract_number
            if current_contract_number:
                same_contract_history = ContractAssignmentHakenPrint.objects.filter(
                    contract_assignment=assignment,
                    print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
                    contract_number=current_contract_number
                ).select_related('printed_by').order_by('-printed_at').first()
                
                if same_contract_history:
                    employment_conditions_issued = True
                    employment_conditions_issued_at = same_contract_history.printed_at
                    employment_conditions_issued_by = same_contract_history.printed_by
    
    context = {
        'assignment': assignment,
        'client_contract': assignment.client_contract,
        'staff_contract': assignment.staff_contract,
        'haken_info': haken_info,
        'is_dispatch_contract': is_dispatch_contract,
        'employment_conditions_issued': employment_conditions_issued,
        'employment_conditions_issued_at': employment_conditions_issued_at,
        'employment_conditions_issued_by': employment_conditions_issued_by,
        'employment_conditions_confirmed': assignment.confirmed_at is not None,
        'employment_conditions_confirmed_at': assignment.confirmed_at,
        'haken_print_history': haken_print_history,
        'haken_print_history_count': haken_print_history_count,
        'from_client': from_client,
        'from_staff': from_staff,
        'from_expire_list': from_expire_list,
        'change_logs': change_logs,
        'display_start_date': display_start_date,
        'display_end_date': display_end_date,
        'Constants': Constants,
    }
    
    return render(request, 'contract/contract_assignment_detail.html', context)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def contract_assignment_confirm_view(request, assignment_pk):
    """契約アサイン延長確認の詳細・作成・編集画面"""
    assignment = get_object_or_404(
        ContractAssignment.objects.select_related(
            'client_contract__client',
            'staff_contract__staff'
        ),
        pk=assignment_pk
    )
    
    # 既存の確認情報を取得（存在しない場合はNone）
    try:
        confirm = assignment.assignment_confirm
    except ContractAssignmentConfirm.DoesNotExist:
        confirm = None
    
    if request.method == 'POST':
        if confirm:
            # 編集の場合
            form = ContractAssignmentConfirmForm(request.POST, instance=confirm)
        else:
            # 新規作成の場合
            form = ContractAssignmentConfirmForm(request.POST)
        
        if form.is_valid():
            confirm_instance = form.save(commit=False)
            if not confirm:
                # 新規作成の場合のみ契約アサインを設定
                confirm_instance.contract_assignment = assignment
            confirm_instance.updated_by = request.user
            if not confirm:
                confirm_instance.created_by = request.user
            confirm_instance.save()
            
            action = '更新' if confirm else '登録'
            messages.success(request, f'延長確認情報を{action}しました。')
            
            # 遷移元パラメータを保持してリダイレクト
            from_param = request.GET.get('from')
            if from_param:
                return redirect(f"{reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': assignment_pk})}?from={from_param}")
            else:
                return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    else:
        if confirm:
            # 編集の場合
            form = ContractAssignmentConfirmForm(instance=confirm)
        else:
            # 新規作成の場合
            form = ContractAssignmentConfirmForm()
    
    # 遷移元を判定
    from_param = request.GET.get('from')
    
    context = {
        'assignment': assignment,
        'confirm': confirm,
        'form': form,
        'is_edit': confirm is not None,
        'from_param': from_param,
        'Constants': Constants,
    }
    
    return render(request, 'contract/contract_assignment_confirm_form.html', context)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def contract_assignment_confirm_delete(request, assignment_pk):
    """契約アサイン延長確認の削除"""
    assignment = get_object_or_404(ContractAssignment, pk=assignment_pk)
    
    try:
        confirm = assignment.assignment_confirm
    except ContractAssignmentConfirm.DoesNotExist:
        messages.error(request, '削除対象の延長確認情報が見つかりません。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    if request.method == 'POST':
        confirm.delete()
        messages.success(request, '延長確認情報を削除しました。')
        
        # 遷移元パラメータを保持してリダイレクト
        from_param = request.GET.get('from')
        if from_param:
            return redirect(f"{reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': assignment_pk})}?from={from_param}")
        else:
            return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    # 遷移元を判定
    from_param = request.GET.get('from')
    
    context = {
        'assignment': assignment,
        'confirm': confirm,
        'from_param': from_param,
    }
    
    return render(request, 'contract/contract_assignment_confirm_delete.html', context)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def contract_assignment_haken_view(request, assignment_pk):
    """契約アサイン派遣雇用安定措置の詳細・作成・編集画面"""
    assignment = get_object_or_404(
        ContractAssignment.objects.select_related(
            'client_contract__client',
            'staff_contract__staff'
        ),
        pk=assignment_pk
    )
    
    # 派遣契約かどうかをチェック
    if assignment.client_contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この機能は派遣契約のみ利用できます。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    # 既存の派遣雇用安定措置情報を取得（存在しない場合はNone）
    try:
        haken_info = assignment.haken_info
    except ContractAssignmentHaken.DoesNotExist:
        haken_info = None
    
    if request.method == 'POST':
        if haken_info:
            # 編集の場合
            form = ContractAssignmentHakenForm(request.POST, instance=haken_info)
        else:
            # 新規作成の場合
            form = ContractAssignmentHakenForm(request.POST)
        
        if form.is_valid():
            haken_instance = form.save(commit=False)
            if not haken_info:
                # 新規作成の場合のみ契約アサインを設定
                haken_instance.contract_assignment = assignment
            haken_instance.updated_by = request.user
            if not haken_info:
                haken_instance.created_by = request.user
            haken_instance.save()
            
            action = '更新' if haken_info else '登録'
            messages.success(request, f'派遣雇用安定措置情報を{action}しました。')
            
            # 遷移元パラメータを保持してリダイレクト
            from_param = request.GET.get('from')
            if from_param:
                return redirect(f"{reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': assignment_pk})}?from={from_param}")
            else:
                return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    else:
        if haken_info:
            # 編集の場合
            form = ContractAssignmentHakenForm(instance=haken_info)
        else:
            # 新規作成の場合
            form = ContractAssignmentHakenForm()
    
    # 遷移元を判定
    from_param = request.GET.get('from')
    
    context = {
        'assignment': assignment,
        'haken_info': haken_info,
        'form': form,
        'is_edit': haken_info is not None,
        'from_param': from_param,
        'Constants': Constants,
    }
    
    return render(request, 'contract/contract_assignment_haken_form.html', context)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def contract_assignment_haken_delete(request, assignment_pk):
    """契約アサイン派遣雇用安定措置の削除"""
    assignment = get_object_or_404(ContractAssignment, pk=assignment_pk)
    
    try:
        haken_info = assignment.haken_info
    except ContractAssignmentHaken.DoesNotExist:
        messages.error(request, '削除対象の派遣雇用安定措置情報が見つかりません。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    if request.method == 'POST':
        haken_info.delete()
        messages.success(request, '派遣雇用安定措置情報を削除しました。')
        
        # 遷移元パラメータを保持してリダイレクト
        from_param = request.GET.get('from')
        if from_param:
            return redirect(f"{reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': assignment_pk})}?from={from_param}")
        else:
            return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    # 遷移元を判定
    from_param = request.GET.get('from')
    
    context = {
        'assignment': assignment,
        'haken_info': haken_info,
        'from_param': from_param,
    }
    
    return render(request, 'contract/contract_assignment_haken_delete.html', context)
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def assignment_employment_conditions_issue(request, assignment_pk):
    """
    就業条件明示書の正式発行（状況カードのスイッチから呼び出し）
    """
    if request.method != 'POST':
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
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
    
    # スタッフ契約の状態チェック
    if assignment.staff_contract.contract_status in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
        messages.error(request, 'スタッフ契約が作成中または申請状態の場合は就業条件明示書を発行できません。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    try:
        from .models import ContractAssignmentHakenPrint
        
        # 同じ契約番号の発行履歴があるかチェック
        current_contract_number = assignment.staff_contract.contract_number
        if current_contract_number:
            existing_record = ContractAssignmentHakenPrint.objects.filter(
                contract_assignment=assignment,
                print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
                contract_number=current_contract_number
            ).first()
            
            if existing_record:
                messages.warning(request, f'契約番号「{current_contract_number}」の就業条件明示書は既に発行済みです。')
                return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
        from django.core.files.base import ContentFile
        
        # PDF生成（ウォーターマークなし）
        from .utils import generate_employment_conditions_pdf
        pdf_content = generate_employment_conditions_pdf(
            assignment=assignment,
            user=request.user,
            issued_at=timezone.now(),
            watermark_text=None
        )
        
        # 発行履歴を保存
        print_record = ContractAssignmentHakenPrint.objects.create(
            contract_assignment=assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=request.user,
            document_title=f"就業条件明示書",
            contract_number=assignment.staff_contract.contract_number
        )
        
        # PDFファイルを保存
        filename = f"employment_conditions_{assignment.pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        print_record.pdf_file.save(
            filename,
            ContentFile(pdf_content),
            save=True
        )
        
        # ログ記録
        from apps.system.logs.models import AppLog
        AppLog.objects.create(
            user=request.user,
            model_name='ContractAssignment',
            object_id=str(assignment.pk),
            action='issue',
            object_repr=f'就業条件明示書を発行しました'
        )
        
        # 就業条件明示書の発行日時を設定し、確認状態をリセット（再発行時）
        assignment.issued_at = timezone.now()
        assignment.confirmed_at = None
        assignment.save()
        
        messages.success(request, '就業条件明示書を発行しました。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
        
    except Exception as e:
        messages.error(request, f'就業条件明示書の発行中にエラーが発生しました: {str(e)}')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def view_assignment_haken_print_pdf(request, pk):
    """
    契約アサイン派遣印刷履歴のPDFをブラウザで表示する
    """
    from .models import ContractAssignmentHakenPrint
    from django.http import HttpResponse, Http404
    
    print_history = get_object_or_404(ContractAssignmentHakenPrint, pk=pk)
    
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
def download_assignment_haken_print_pdf(request, pk):
    """
    契約アサイン派遣印刷履歴のPDFをダウンロードする
    """
    from .models import ContractAssignmentHakenPrint
    from django.http import HttpResponse, Http404
    import os
    
    print_history = get_object_or_404(ContractAssignmentHakenPrint, pk=pk)
    
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
@permission_required('contract.view_clientcontract', raise_exception=True)
def assignment_haken_print_history_list(request, assignment_pk):
    """
    契約アサイン派遣印刷履歴の一覧画面
    """
    from django.core.paginator import Paginator
    from .models import ContractAssignmentHakenPrint
    
    assignment = get_object_or_404(ContractAssignment, pk=assignment_pk)
    
    # 発行履歴を取得
    haken_print_history = ContractAssignmentHakenPrint.objects.filter(
        contract_assignment=assignment
    ).select_related('printed_by').order_by('-printed_at')
    
    # ページネーション
    paginator = Paginator(haken_print_history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assignment': assignment,
        'haken_print_history': page_obj,
        'back_url': reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': assignment_pk}),
    }
    
    return render(request, 'contract/assignment_haken_print_history_list.html', context)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def assignment_employment_conditions_unissue(request, assignment_pk):
    """
    就業条件明示書の発行解除（発行済み → 承認済みに戻す）
    """
    if request.method != 'POST':
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    assignment = get_object_or_404(ContractAssignment, pk=assignment_pk)
    
    # 派遣契約かどうかチェック
    if assignment.client_contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約は派遣契約ではないため、処理できません。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    # スタッフ契約が発行済みかチェック
    if assignment.staff_contract.contract_status != Constants.CONTRACT_STATUS.ISSUED:
        messages.error(request, 'スタッフ契約が発行済み状態でない場合は処理できません。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    try:
        # スタッフ契約を承認済み状態に戻す
        assignment.staff_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        assignment.staff_contract.issued_at = None
        assignment.staff_contract.issued_by = None
        assignment.staff_contract.save()
        
        # 契約アサインの発行・確認状態もリセット
        assignment.issued_at = None
        assignment.confirmed_at = None
        assignment.save()
        
        # ログ記録
        from apps.system.logs.models import AppLog
        AppLog.objects.create(
            user=request.user,
            model_name='ContractAssignment',
            object_id=str(assignment.pk),
            action='unissue',
            object_repr=f'就業条件明示書の発行を解除しました'
        )
        
        messages.success(request, '就業条件明示書の発行を解除しました。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
        
    except Exception as e:
        messages.error(request, f'発行解除中にエラーが発生しました: {str(e)}')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_assignment_employment_conditions_issue(request, contract_pk, assignment_pk):
    """
    スタッフ契約の状況カードから就業条件明示書を発行する
    """
    staff_contract = get_object_or_404(StaffContract, pk=contract_pk)
    assignment = get_object_or_404(
        ContractAssignment.objects.select_related(
            'client_contract__client',
            'staff_contract__staff',
            'client_contract__haken_info__haken_office',
            'client_contract__haken_info__commander',
            'client_contract__haken_info__complaint_officer_client'
        ),
        pk=assignment_pk,
        staff_contract=staff_contract
    )
    
    # 有期雇用かどうかチェック
    if not staff_contract.employment_type or not staff_contract.employment_type.is_fixed_term:
        messages.error(request, 'この機能は有期雇用のスタッフ契約のみ利用できます。')
        return redirect('contract:staff_contract_detail', pk=contract_pk)
    
    # 派遣契約かどうかチェック
    if assignment.client_contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約は派遣契約ではないため、就業条件明示書を発行できません。')
        return redirect('contract:staff_contract_detail', pk=contract_pk)
    
    # スタッフ契約の状態チェック（発行済みのみ）
    if staff_contract.contract_status != Constants.CONTRACT_STATUS.ISSUED:
        messages.error(request, 'スタッフ契約が発行済み状態でない場合は就業条件明示書を発行できません。')
        return redirect('contract:staff_contract_detail', pk=contract_pk)
    
    try:
        from .models import ContractAssignmentHakenPrint
        
        # 同じ契約番号の発行履歴があるかチェック
        current_contract_number = staff_contract.contract_number
        if current_contract_number:
            existing_record = ContractAssignmentHakenPrint.objects.filter(
                contract_assignment=assignment,
                print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
                contract_number=current_contract_number
            ).first()
            
            if existing_record:
                messages.warning(request, f'契約番号「{current_contract_number}」の就業条件明示書は既に発行済みです。')
                return redirect('contract:staff_contract_detail', pk=contract_pk)
        
        from django.core.files.base import ContentFile
        
        # PDF生成（ウォーターマークなし）
        from .utils import generate_employment_conditions_pdf
        pdf_content = generate_employment_conditions_pdf(
            assignment=assignment,
            user=request.user,
            issued_at=timezone.now(),
            watermark_text=None
        )
        
        # 発行履歴を保存
        print_record = ContractAssignmentHakenPrint.objects.create(
            contract_assignment=assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=request.user,
            document_title=f"就業条件明示書",
            contract_number=staff_contract.contract_number
        )
        
        # PDFファイルを保存
        filename = f"employment_conditions_{assignment.pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        print_record.pdf_file.save(
            filename,
            ContentFile(pdf_content),
            save=True
        )
        
        # ログ記録
        from apps.system.logs.models import AppLog
        AppLog.objects.create(
            user=request.user,
            model_name='ContractAssignment',
            object_id=str(assignment.pk),
            action='issue',
            object_repr=f'就業条件明示書を発行しました（スタッフ契約から）'
        )
        
        # 就業条件明示書の発行日時を設定し、確認状態をリセット（再発行時）
        assignment.issued_at = timezone.now()
        assignment.confirmed_at = None
        assignment.save()
        
        messages.success(request, f'「{assignment.client_contract.client.name}」の就業条件明示書を発行しました。')
        return redirect('contract:staff_contract_detail', pk=contract_pk)
        
    except Exception as e:
        messages.error(request, f'就業条件明示書の発行中にエラーが発生しました: {str(e)}')
        return redirect('contract:staff_contract_detail', pk=contract_pk)