from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.common.constants import Constants
from apps.master.models import ContractPattern, EmploymentType, JobCategory
from apps.staff.models import Staff

from .forms import StaffContractForm
from .models import ClientContract, ContractAssignment, StaffContract


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

        # 粗利率計算
        profit_margin_info = _calculate_profit_margin(client_contract, staff_contract)

        context = {
            'client_contract': client_contract,
            'staff_contract': staff_contract,
            'from_view': 'client',
            'show_daily_dispatch_warning': show_daily_dispatch_warning,
            'profit_margin_info': profit_margin_info,
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

    # 粗利率計算
    profit_margin_info = _calculate_profit_margin(client_contract, staff_contract)

    context = {
        'client_contract': client_contract,
        'staff_contract': staff_contract,
        'from_view': from_view,
        'from_create': True,  # 新規作成からの遷移であることを示すフラグ
        'show_daily_dispatch_warning': show_daily_dispatch_warning,
        'profit_margin_info': profit_margin_info,
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
