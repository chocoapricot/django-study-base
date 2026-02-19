import calendar
import jpholiday
from datetime import date, datetime, time as dt_time, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from .models import StaffTimesheet, StaffTimecard
from .models import ClientTimesheet, ClientTimecard
from .models import StaffTimerecord, StaffTimerecordApproval
from .forms import StaffTimesheetForm, StaffTimecardForm
from .forms import ClientTimesheetForm, ClientTimecardForm
from .utils import is_timerecord_locked
from apps.profile.decorators import check_staff_agreement
from django.db.models import Q
from apps.common.middleware import get_current_tenant_id
from apps.common.constants import Constants
from apps.contract.models import ClientContract, ContractAssignment
from apps.staff.utils import get_annotated_staff_queryset, annotate_staff_connection_info


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimesheet', raise_exception=True)
def timesheet_list(request):
    """月次勤怠一覧"""
    timesheets = StaffTimesheet.objects.select_related(
        'staff', 'staff__international', 'staff__disability', 'staff_contract'
    ).all()
    context = {
        'timesheets': timesheets,
    }
    return render(request, 'kintai/timesheet_list.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimesheet', raise_exception=True)
def contract_search(request):
    """契約検索"""
    from datetime import date, datetime

    from apps.contract.models import StaffContract
    from apps.staff.utils import get_annotated_staff_queryset, annotate_staff_connection_info
    
    # 年月の取得（デフォルトは当月）
    today = timezone.localdate()
    target_month_str = request.GET.get('target_month')
    
    if target_month_str:
        try:
            year, month = map(int, target_month_str.split('-'))
            target_date = date(year, month, 1)
        except ValueError:
            year = today.year
            month = today.month
            target_date = date(year, month, 1)
    else:
        year = today.year
        month = today.month
        target_date = date(year, month, 1)

    # 月末日を計算

    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    # 検索対象の契約を取得
    # 契約期間が指定月と重なるものを抽出
    # start_date <= month_end AND (end_date >= month_start OR end_date IS NULL)

    # スタッフの注釈を事前に取得
    annotated_staffs = get_annotated_staff_queryset(request.user).select_related('international', 'disability')

    contracts = StaffContract.objects.select_related('staff').filter(
        staff__in=annotated_staffs,
        start_date__lte=month_end
    ).filter(
        Q(end_date__gte=target_date) | Q(end_date__isnull=True)
    ).order_by('staff__employee_no')

    # 各スタッフのオブジェクトを注釈済みのもので置き換える、または注釈情報を付与する
    # contract_searchではQuerySetの結果をループするので、その中でスタッフ情報を取得
    staff_map = {s.pk: s for s in annotated_staffs.filter(pk__in=[c.staff_id for c in contracts])}
    for contract in contracts:
        if contract.staff_id in staff_map:
            contract.staff = staff_map[contract.staff_id]

    # 接続情報の付与
    staff_list_for_connection = [contract.staff for contract in contracts]
    annotate_staff_connection_info(staff_list_for_connection)

    # フィルタリング条件の取得
    input_status = request.GET.get('input_status')

    # 各契約に対して、指定月の勤怠が存在するかチェック
    contract_list = []
    for contract in contracts:
        timesheet = StaffTimesheet.objects.filter(
            staff_contract=contract,
            target_month=target_date
        ).first()
        
        input_days = 0
        if timesheet:
            input_days = timesheet.timecards.count()

        # 契約期間と対象月の重なる日数を計算（カレンダー日）
        # start_date <= month_end AND (end_date >= month_start OR end_date IS NULL)
        # 重なり開始日 = max(month_start, start_date)
        # 重なり終了日 = min(month_end, end_date) if end_date else month_end
        
        c_start = contract.start_date
        c_end = contract.end_date
        
        overlap_start = max(target_date, c_start) if c_start else target_date
        overlap_end = min(month_end, c_end) if c_end else month_end
        
        # 日数計算（inclusive）
        if overlap_start <= overlap_end:
            required_days = (overlap_end - overlap_start).days + 1
        else:
            required_days = 0

        # ステータス判定
        status = 'not_input' # 未入力
        if input_days > 0:
            if input_days >= required_days:
                status = 'inputted' # 入力済
            else:
                status = 'inputting' # 入力中
        
        # フィルタリング
        if input_status:
            if input_status == 'not_input' and status != 'not_input':
                continue
            if input_status == 'inputting' and status != 'inputting':
                continue
            if input_status == 'inputted' and status != 'inputted':
                continue

        contract_list.append({
            'contract': contract,
            'timesheet': timesheet,
            'input_days': input_days,
            'required_days': required_days, # デバッグ表示用などに持たせておく
        })

    from django.core.paginator import Paginator
    paginator = Paginator(contract_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'contract_list': page_obj,
        'page_obj': page_obj,
        'year': year,
        'month': month,
        'target_date': target_date,
        'input_status': input_status,
    }
    return render(request, 'kintai/contract_search.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimesheet', raise_exception=True)
def staff_search(request):
    """スタッフ検索"""
    from datetime import date

    from apps.contract.models import StaffContract
    from apps.staff.models import Staff
    from apps.staff.utils import get_annotated_staff_queryset, annotate_staff_connection_info
    
    # 年月の取得（デフォルトは当月）
    today = timezone.localdate()
    target_month_str = request.GET.get('target_month')
    
    if target_month_str:
        try:
            year, month = map(int, target_month_str.split('-'))
            target_date = date(year, month, 1)
        except ValueError:
            year = today.year
            month = today.month
            target_date = date(year, month, 1)
    else:
        year = today.year
        month = today.month
        target_date = date(year, month, 1)

    # 月末日を計算

    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    # 指定月に有効な契約を持つスタッフを取得
    # 契約期間が指定月と重なるスタッフを抽出
    staff_with_contracts = get_annotated_staff_queryset(request.user).select_related(
        'international', 'disability'
    ).filter(
        contracts__start_date__lte=month_end
    ).filter(
        Q(contracts__end_date__gte=target_date) | Q(contracts__end_date__isnull=True)
    ).distinct().order_by('employee_no')

    # 接続情報の付与
    annotate_staff_connection_info(staff_with_contracts)

    # 各スタッフの情報を集計
    staff_list = []
    for staff in staff_with_contracts:
        # このスタッフの指定月に有効な契約を取得
        contracts = StaffContract.objects.filter(
            staff_id=staff.id,
            start_date__lte=month_end
        ).filter(
            Q(end_date__gte=target_date) | Q(end_date__isnull=True)
        )
        
        contract_count = contracts.count()
        
        # このスタッフの指定月の日次勤怠を取得（全契約分）
        timecards = StaffTimecard.objects.filter(
            staff_contract__staff_id=staff.id,
            work_date__year=year,
            work_date__month=month
        )
        
        input_days = timecards.values('work_date').distinct().count()
        
        staff_list.append({
            'staff': staff,
            'contract_count': contract_count,
            'input_days': input_days,
        })

    from django.core.paginator import Paginator
    paginator = Paginator(staff_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'staff_list': page_obj,
        'page_obj': page_obj,
        'year': year,
        'month': month,
        'target_date': target_date,
    }
    return render(request, 'kintai/staff_search.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimecard', raise_exception=True)
def staff_timecard_calendar(request, staff_pk, target_month):
    """スタッフ別日次勤怠カレンダー入力"""
    from datetime import date, time as dt_time

    import jpholiday
    from apps.contract.models import StaffContract
    from apps.staff.models import Staff

    from django.core.exceptions import ValidationError
    
    staff = get_object_or_404(Staff.objects.select_related('international', 'disability'), pk=staff_pk)
    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        return redirect('kintai:staff_search')

    # 月末日を計算
    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    # このスタッフの指定月に有効な契約を取得
    contracts = StaffContract.objects.filter(
        staff_id=staff.id,
        start_date__lte=month_end
    ).filter(
        Q(end_date__gte=target_date) | Q(end_date__isnull=True)
    ).select_related('employment_type', 'worktime_pattern')

    if request.method == 'POST':

        # フォームデータから日次勤怠を一括保存
        updated_timesheets = set()  # 更新された月次勤怠を記録
        
        for day in range(1, last_day + 1):
            work_date = date(year, month, day)
            
            # フォームデータを取得
            contract_id = request.POST.get(f'contract_{day}')
            work_type = request.POST.get(f'work_type_{day}')
            work_time_pattern_work_id = request.POST.get(f'work_time_pattern_work_{day}')
            start_time_str = request.POST.get(f'start_time_{day}')
            start_time_next_day = request.POST.get(f'start_time_next_day_{day}') == 'on'
            end_time_str = request.POST.get(f'end_time_{day}')
            end_time_next_day = request.POST.get(f'end_time_next_day_{day}') == 'on'
            break_minutes = request.POST.get(f'break_minutes_{day}', 0)
            paid_leave_days = request.POST.get(f'paid_leave_days_{day}', 0)
            
            # 勤務区分が入力されていない場合はスキップ
            if not work_type:
                # 勤務区分が空の場合、既存のデータがあれば削除する
                # このスタッフのこの日のデータを全て削除（契約に関わらず）
                deleted_timecards = StaffTimecard.objects.filter(
                    staff_contract__staff_id=staff.id,
                    work_date=work_date
                )
                # 削除前に影響を受ける月次勤怠を記録
                for tc in deleted_timecards:
                    if tc.timesheet:
                        updated_timesheets.add(tc.timesheet)
                deleted_timecards.delete()
                continue
            
            # 勤務区分が入力されている場合は契約が必須
            if not contract_id:
                messages.error(request, f'{work_date.day}日: 勤務区分を入力する場合はスタッフ契約を選択してください。')
                continue

            # 契約を取得
            try:
                contract = StaffContract.objects.get(pk=contract_id, staff_id=staff.id)
            except StaffContract.DoesNotExist:
                messages.error(request, f'{work_date.day}日: 選択されたスタッフ契約が見つかりません。')
                continue

            # 契約期間外の日付は処理しない
            if contract.start_date and work_date < contract.start_date:
                messages.error(request, f'{work_date.day}日: 契約開始日({contract.start_date.strftime("%Y/%m/%d")})より前の日付です。')
                continue
            if contract.end_date and work_date > contract.end_date:
                messages.error(request, f'{work_date.day}日: 契約終了日({contract.end_date.strftime("%Y/%m/%d")})より後の日付です。')
                continue
            
            # 時刻の変換
            start_time = None
            end_time = None
            if start_time_str:
                try:
                    hour, minute = map(int, start_time_str.split(':'))
                    start_time = dt_time(hour, minute)
                except:
                    pass
            if end_time_str:
                try:
                    hour, minute = map(int, end_time_str.split(':'))
                    end_time = dt_time(hour, minute)
                except:
                    pass
            
            # 既存のデータを取得または新規作成
            timecard = StaffTimecard.objects.filter(
                staff_contract=contract,
                work_date=work_date
            ).first()
            
            if not timecard:
                timecard = StaffTimecard(
                    staff_contract=contract,
                    work_date=work_date,
                    work_type=work_type
                )
            
            # データを更新
            timecard.work_type = work_type
            
            # work_time_pattern_workを設定
            if work_time_pattern_work_id:
                try:
                    from apps.master.models import WorkTimePatternWork
                    timecard.work_time_pattern_work = WorkTimePatternWork.objects.get(pk=work_time_pattern_work_id)
                except WorkTimePatternWork.DoesNotExist:
                    timecard.work_time_pattern_work = None
            else:
                timecard.work_time_pattern_work = None
            
            timecard.start_time = start_time
            timecard.start_time_next_day = start_time_next_day
            timecard.end_time = end_time
            timecard.end_time_next_day = end_time_next_day
            timecard.break_minutes = int(break_minutes) if break_minutes else 0
            timecard.paid_leave_days = float(paid_leave_days) if paid_leave_days else 0
            
            try:
                timecard.full_clean()
                timecard.save(skip_timesheet_update=True)  # 集計更新をスキップ
                # 保存後に影響を受ける月次勤怠を記録
                if timecard.timesheet:
                    updated_timesheets.add(timecard.timesheet)
            except ValidationError as e:
                # エラーメッセージを作成
                error_messages = []
                for field, errors in e.message_dict.items():
                    for error in errors:
                        error_messages.append(f"{work_date.day}日: {error}")
                messages.error(request, " / ".join(error_messages))
        
        # すべての保存が完了した後、影響を受けた月次勤怠の集計を一度だけ更新
        for timesheet in updated_timesheets:
            timesheet.calculate_totals()
        
        if not messages.get_messages(request):
            messages.success(request, '日次勤怠を一括保存しました。')
        return redirect('kintai:staff_timecard_calendar', staff_pk=staff_pk, target_month=target_month)
    
    # カレンダーデータを作成
    # 既存の日次勤怠データを取得
    timecards_dict = {}
    for timecard in StaffTimecard.objects.filter(
        staff_contract__staff_id=staff.id,
        work_date__year=year,
        work_date__month=month
    ).select_related('staff_contract'):
        timecards_dict[timecard.work_date.day] = timecard
    
    # カレンダーデータを作成
    calendar_data = []
    for day in range(1, last_day + 1):
        work_date = date(year, month, day)
        weekday = work_date.weekday()
        is_holiday = jpholiday.is_holiday(work_date)
        try:
            holiday_name = jpholiday.is_holiday_name(work_date)
        except Exception:
            holiday_name = None
        
        timecard = timecards_dict.get(day)
        
        # この日に有効な契約を取得
        valid_contracts = []
        for contract in contracts:
            if contract.start_date and work_date < contract.start_date:
                continue
            if contract.end_date and work_date > contract.end_date:
                continue
            valid_contracts.append(contract)

        calendar_data.append({
            'day': day,
            'date': work_date,
            'holiday_name': holiday_name,
            'weekday': weekday,
            'weekday_name': ['月', '火', '水', '木', '金', '土', '日'][weekday],
            'is_weekend': weekday >= 5,
            'is_holiday': is_holiday,
            'timecard': timecard,
            'valid_contracts': valid_contracts,
        })
    
    # デフォルト値を取得（最初の契約から）
    default_values = {'start_time': '09:00', 'end_time': '18:00', 'break_minutes': '60'}
    if contracts.exists():
        default_values = _get_contract_work_time(contracts.first())
    
    # 各契約の就業時間パターンデータを取得
    import json
    contracts_work_times = {}
    for contract in contracts:
        contracts_work_times[contract.pk] = _get_work_times_data(contract)

    context = {
        'staff': staff,
        'calendar_data': calendar_data,
        'year': year,
        'month': month,
        'target_date': target_date,
        'default_start_time': default_values['start_time'],
        'default_end_time': default_values['end_time'],
        'default_break_minutes': default_values['break_minutes'],
        'contracts_work_times_json': json.dumps(contracts_work_times),
    }
    return render(request, 'kintai/staff_timecard_calendar.html', context)

import json
from apps.contract.models import StaffContract

@login_required
@check_staff_agreement
@permission_required('kintai.add_stafftimesheet', raise_exception=True)
def timesheet_create(request):
    """月次勤怠作成"""
    if request.method == 'POST':
        form = StaffTimesheetForm(request.POST)
        if form.is_valid():
            timesheet = form.save()
            messages.success(request, '月次勤怠を作成しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    else:
        today = timezone.localdate()
        initial_data = {
            'target_month': today.strftime('%Y-%m'), # YYYY-MM 形式
        }
        form = StaffTimesheetForm(initial=initial_data)
    
    # JavaScriptで日付範囲を制御するために契約情報をJSONで渡す
    contracts = StaffContract.objects.filter(start_date__isnull=False)
    contract_data = {
        c.pk: {
            'start': c.start_date.strftime('%Y-%m') if c.start_date else None,
            'end': c.end_date.strftime('%Y-%m') if c.end_date else None,
        } for c in contracts
    }
    
    context = {
        'form': form,
        'contract_data_json': json.dumps(contract_data),
    }
    return render(request, 'kintai/timesheet_form.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimesheet', raise_exception=True)
def timesheet_detail(request, pk):
    """月次勤怠詳細"""
    import jpholiday
    
    timesheet = get_object_or_404(StaffTimesheet.objects.unfiltered().select_related(
        'staff', 'staff__international', 'staff__disability', 'staff_contract'
    ), pk=pk)
    timecards = timesheet.timecards.all().order_by('work_date')
    
    # 各timecardに曜日情報と祝日情報を追加
    for timecard in timecards:
        timecard.weekday = timecard.work_date.weekday()
        timecard.is_national_holiday = jpholiday.is_holiday(timecard.work_date)
        # 祝日名が取得できる場合は追加（jpholiday のバージョン依存）
        try:
            timecard.holiday_name = jpholiday.is_holiday_name(timecard.work_date)
        except Exception:
            # 関数がない場合や他エラーは無視して None のまま
            timecard.holiday_name = None
    
    context = {
        'timesheet': timesheet,
        'timecards': timecards,
    }
    return render(request, 'kintai/timesheet_detail.html', context)





@login_required
@check_staff_agreement
@permission_required('kintai.delete_stafftimesheet', raise_exception=True)
def timesheet_delete(request, pk):
    """月次勤怠削除"""
    # select_relatedでテンプレート表示用に関連オブジェクトを事前ロード
    timesheet = get_object_or_404(
        StaffTimesheet.objects.select_related('staff', 'staff_contract'),
        pk=pk
    )
    
    if request.method == 'POST':
        target_month = timesheet.target_month.strftime('%Y-%m')
        timesheet.delete()
        messages.success(request, '月次勤怠を削除しました。')
        return redirect(f"{reverse('kintai:contract_search')}?target_month={target_month}")
    
    context = {
        'timesheet': timesheet,
    }
    return render(request, 'kintai/timesheet_delete.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimesheet', raise_exception=True)
def timesheet_preview(request, contract_pk, target_month):
    """月次勤怠プレビュー（未作成状態）"""
    from datetime import datetime, date
    from apps.contract.models import StaffContract
    
    contract = get_object_or_404(StaffContract.objects.select_related(
        'staff', 'staff__international', 'staff__disability'
    ), pk=contract_pk)
    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        return redirect('kintai:contract_search')

    # 既に存在する場合は詳細画面へリダイレクト
    exists_timesheet = StaffTimesheet.objects.filter(
        staff_contract=contract,
        target_month=target_date
    ).first()
    if exists_timesheet:
        return redirect('kintai:timesheet_detail', pk=exists_timesheet.pk)

    # 仮想的なTimesheetオブジェクトを作成（DBには保存しない）
    timesheet = StaffTimesheet(
        staff_contract=contract,
        staff_id=contract.staff_id,
        target_month=target_date,
        status='00' # 未作成
    )
    # 集計値をハイフン表示するためにNoneを設定（テンプレート側で制御）
    timesheet.total_work_days = None
    timesheet.total_work_hours = None
    timesheet.total_overtime_hours = None
    timesheet.total_late_night_overtime_hours = None
    timesheet.total_holiday_work_hours = None
    timesheet.total_absence_days = None
    timesheet.total_paid_leave_days = None
    
    context = {
        'timesheet': timesheet,
        'timecards': [],
        'is_preview': True, # プレビューモードフラグ
        'contract': contract,
        'target_date': target_date,
    }
    return render(request, 'kintai/timesheet_detail.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.add_stafftimecard', raise_exception=True)
def timecard_create(request, timesheet_pk):
    """日次勤怠作成"""
    timesheet = get_object_or_404(StaffTimesheet.objects.unfiltered(), pk=timesheet_pk)
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet_pk)


    if request.method == 'POST':
        # pass timesheet to the form so form-level validation can check contract period
        form = StaffTimecardForm(request.POST, timesheet=timesheet)
        if form.is_valid():
            timecard = form.save(commit=False)
            timecard.timesheet = timesheet
            timecard.staff_contract = timesheet.staff_contract
            timecard.save()
            messages.success(request, '日次勤怠を作成しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet_pk)
    else:
        form = StaffTimecardForm(timesheet=timesheet)
    
    # 就業時間パターンから勤務時間一覧を取得
    work_times_data = _get_work_times_data(timesheet.staff_contract)
    
    # JSONに変換してテンプレートに渡す
    import json
    work_times_data_json = json.dumps(work_times_data)
    
    context = {
        'form': form,
        'timesheet': timesheet,
        'work_times_data_json': work_times_data_json,
    }
    return render(request, 'kintai/timecard_form.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.add_stafftimecard', raise_exception=True)
def timecard_create_initial(request, contract_pk, target_month):
    """初回日次勤怠作成（同時に月次勤怠も作成）"""
    from datetime import date
    from apps.contract.models import StaffContract
    
    contract = get_object_or_404(StaffContract, pk=contract_pk)
    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        return redirect('kintai:contract_search')

    # 既に存在する場合は通常作成へリダイレクト（念のため）
    exists_timesheet = StaffTimesheet.objects.filter(
        staff_contract=contract,
        target_month=target_date
    ).first()
    if exists_timesheet:
        return redirect('kintai:timecard_create', timesheet_pk=exists_timesheet.pk)

    # 仮想Timesheetを作成してフォームに渡す（バリデーション用）
    virtual_timesheet = StaffTimesheet(
        staff_contract=contract,
        staff_id=contract.staff_id,
        target_month=target_date
    )


    if request.method == 'POST':
        form = StaffTimecardForm(request.POST, timesheet=virtual_timesheet)
        if form.is_valid():
            # 月次勤怠を保存
            timesheet = virtual_timesheet
            timesheet.save()
            
            # 日次勤怠を保存
            timecard = form.save(commit=False)
            timecard.timesheet = timesheet
            timecard.staff_contract = timesheet.staff_contract
            timecard.save()
            
            messages.success(request, '月次勤怠と日次勤怠を作成しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    else:
        form = StaffTimecardForm(timesheet=virtual_timesheet)

    # 就業時間パターンから勤務時間一覧を取得
    work_times_data = _get_work_times_data(contract)
    
    # JSONに変換してテンプレートに渡す
    import json
    work_times_data_json = json.dumps(work_times_data)

    context = {
        'form': form,
        'timesheet': virtual_timesheet,
        'is_preview': True,
        'work_times_data_json': work_times_data_json,
    }
    return render(request, 'kintai/timecard_form.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimecard', raise_exception=True)
def timecard_edit(request, pk):
    """日次勤怠編集"""
    timecard = get_object_or_404(StaffTimecard.objects.unfiltered(), pk=pk)
    timesheet = timecard.timesheet
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet.pk)

    
    if request.method == 'POST':
        form = StaffTimecardForm(request.POST, instance=timecard, timesheet=timesheet)
        if form.is_valid():
            form.save()
            messages.success(request, '日次勤怠を更新しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    else:
        form = StaffTimecardForm(instance=timecard, timesheet=timesheet)
    
    # 就業時間パターンから勤務時間一覧を取得
    work_times_data = _get_work_times_data(timesheet.staff_contract)
    
    # JSONに変換してテンプレートに渡す
    import json
    work_times_data_json = json.dumps(work_times_data)
    
    context = {
        'form': form,
        'timecard': timecard,
        'timesheet': timesheet,
        'work_times_data_json': work_times_data_json,
    }
    return render(request, 'kintai/timecard_form.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.delete_stafftimecard', raise_exception=True)
def timecard_delete(request, pk):
    """日次勤怠削除"""
    timecard = get_object_or_404(StaffTimecard.objects.unfiltered(), pk=pk)
    timesheet = timecard.timesheet
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet.pk)

    
    if request.method == 'POST':
        timecard.delete()
        # 月次勤怠の集計を更新
        timesheet.calculate_totals()
        messages.success(request, '日次勤怠を削除しました。')
        return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    
    context = {
        'timecard': timecard,
    }
    return render(request, 'kintai/timecard_delete.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimecard', raise_exception=True)
def timecard_calendar(request, timesheet_pk):
    """日次勤怠カレンダー入力"""
    from datetime import date, timedelta

    import jpholiday
    from django.core.exceptions import ValidationError
    
    timesheet = get_object_or_404(StaffTimesheet.objects.unfiltered(), pk=timesheet_pk)
    
    # スタッフの場合、確認済みの契約のみ編集可能
    if not request.user.is_staff:
        if timesheet.staff_contract and timesheet.staff_contract.contract_status != Constants.CONTRACT_STATUS.CONFIRMED:
            messages.error(request, '確認済みの契約ではないため、このタイムカードは編集できません。')
            return redirect('kintai:staff_timecard_register')

    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet_pk)
    
    if request.method == 'POST':
        # フォームデータから日次勤怠を一括保存
        year = timesheet.target_month.year
        month = timesheet.target_month.month
        
        # 月の日数を取得
        _, last_day = calendar.monthrange(year, month)
        
        for day in range(1, last_day + 1):
            work_date = date(year, month, day)
            
            # フォームデータを取得
            work_type = request.POST.get(f'work_type_{day}')
            work_time_pattern_work_id = request.POST.get(f'work_time_pattern_work_{day}')
            start_time_str = request.POST.get(f'start_time_{day}')
            start_time_next_day = request.POST.get(f'start_time_next_day_{day}') == 'on'
            end_time_str = request.POST.get(f'end_time_{day}')
            end_time_next_day = request.POST.get(f'end_time_next_day_{day}') == 'on'
            break_minutes = request.POST.get(f'break_minutes_{day}', 0)
            paid_leave_days = request.POST.get(f'paid_leave_days_{day}', 0)
            
            if not work_type:
                # 勤務区分が空の場合、既存のデータがあれば削除する
                deleted_count, _ = StaffTimecard.objects.filter(
                    timesheet=timesheet,
                    work_date=work_date
                ).delete()
                continue

            # スタッフ契約の範囲外の日付は処理しない（カレンダー上にも表示しないため）
            sc = getattr(timesheet, 'staff_contract', None)
            if sc:
                sc_start = sc.start_date
                sc_end = sc.end_date
                if sc_start and work_date < sc_start:
                    continue
                if sc_end and work_date > sc_end:
                    continue
            
            # 時刻の変換
            from datetime import time as dt_time
            start_time = None
            end_time = None
            if start_time_str:
                try:
                    hour, minute = map(int, start_time_str.split(':'))
                    start_time = dt_time(hour, minute)
                except:
                    pass
            if end_time_str:
                try:
                    hour, minute = map(int, end_time_str.split(':'))
                    end_time = dt_time(hour, minute)
                except:
                    pass
            
            # 既存のデータを取得または新規作成
            timecard = StaffTimecard.objects.filter(
                timesheet=timesheet,
                work_date=work_date
            ).first()
            
            if not timecard:
                timecard = StaffTimecard(
                    timesheet=timesheet,
                    staff_contract=timesheet.staff_contract,
                    work_date=work_date,
                    work_type=work_type
                )
            
            # データを更新
            timecard.work_type = work_type
            
            # work_time_pattern_workを設定
            if work_time_pattern_work_id:
                try:
                    from apps.master.models import WorkTimePatternWork
                    timecard.work_time_pattern_work = WorkTimePatternWork.objects.get(pk=work_time_pattern_work_id)
                except WorkTimePatternWork.DoesNotExist:
                    timecard.work_time_pattern_work = None
            else:
                timecard.work_time_pattern_work = None
            
            timecard.start_time = start_time
            timecard.start_time_next_day = start_time_next_day
            timecard.end_time = end_time
            timecard.end_time_next_day = end_time_next_day
            timecard.break_minutes = int(break_minutes) if break_minutes else 0
            timecard.paid_leave_days = float(paid_leave_days) if paid_leave_days else 0
            
            try:
                timecard.full_clean()
                timecard.save(skip_timesheet_update=True)  # 集計更新をスキップ
            except ValidationError as e:
                # エラーメッセージを作成
                error_messages = []
                for field, errors in e.message_dict.items():
                    for error in errors:
                        error_messages.append(f"{work_date.day}日: {error}")
                messages.error(request, " / ".join(error_messages))
        
        # すべての保存が完了した後、月次勤怠の集計を一度だけ更新
        timesheet.calculate_totals()
        
        if not messages.get_messages(request):
            messages.success(request, '日次勤怠を一括保存しました。')
        return redirect('kintai:timesheet_detail', pk=timesheet_pk)
    
    # カレンダーデータを作成
    year = timesheet.target_month.year
    month = timesheet.target_month.month
    _, last_day = calendar.monthrange(year, month)
    
    # 既存の日次勤怠データを取得
    timecards_dict = {}
    for timecard in timesheet.timecards.all():
        timecards_dict[timecard.work_date.day] = timecard
    
    # カレンダーデータを作成
    calendar_data = []
    for day in range(1, last_day + 1):
        work_date = date(year, month, day)
        weekday = work_date.weekday()  # 0=月曜, 6=日曜
        is_holiday = jpholiday.is_holiday(work_date)
        try:
            holiday_name = jpholiday.is_holiday_name(work_date)
        except Exception:
            holiday_name = None
        
        timecard = timecards_dict.get(day)
        # スタッフ契約の範囲外の日付は表示しない
        sc = getattr(timesheet, 'staff_contract', None)
        if sc:
            sc_start = sc.start_date
            sc_end = sc.end_date
            if sc_start and work_date < sc_start:
                continue
            if sc_end and work_date > sc_end:
                continue

        calendar_data.append({
            'day': day,
            'date': work_date,
            'holiday_name': holiday_name,
            'weekday': weekday,
            'weekday_name': ['月', '火', '水', '木', '金', '土', '日'][weekday],
            'is_weekend': weekday >= 5,
            'is_holiday': is_holiday,
            'timecard': timecard,
        })
    
    # 契約情報のデフォルト値を取得
    default_values = _get_contract_work_time(timesheet.staff_contract)
    
    # 就業時間パターンから勤務時間一覧を取得
    work_times_data = _get_work_times_data(timesheet.staff_contract)

    context = {
        'timesheet': timesheet,
        'calendar_data': calendar_data,
        'default_start_time': default_values['start_time'],
        'default_end_time': default_values['end_time'],
        'default_break_minutes': default_values['break_minutes'],
        'work_times_data': work_times_data,
    }
    return render(request, 'kintai/timecard_calendar.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.add_stafftimecard', raise_exception=True)
def timecard_calendar_initial(request, contract_pk, target_month):
    """初回日次勤怠カレンダー入力（同時に月次勤怠も作成）"""
    from datetime import date, timedelta

    import jpholiday
    from apps.contract.models import StaffContract
    
    contract = get_object_or_404(StaffContract, pk=contract_pk)

    # スタッフの場合、確認済みの契約のみ登録可能
    if not request.user.is_staff:
        if contract.contract_status != Constants.CONTRACT_STATUS.CONFIRMED:
            # 既存のtimesheetがあるかチェック
            try:
                year, month = map(int, target_month.split('-'))
                target_date = date(year, month, 1)
                exists_timesheet = StaffTimesheet.objects.filter(
                    staff_contract=contract,
                    target_month=target_date
                ).first()
                
                messages.error(request, '確認済みの契約ではないため、このタイムカードは登録できません。契約の確認が完了してからご利用ください。')
                
                if exists_timesheet:
                    # 既存のtimesheet詳細画面に戻る
                    return redirect('kintai:timesheet_detail', pk=exists_timesheet.pk)
                else:
                    # timesheetがない場合はプレビュー画面に戻る
                    return redirect('kintai:timesheet_preview', contract_pk=contract_pk, target_month=target_month)
            except ValueError:
                messages.error(request, '確認済みの契約ではないため、このタイムカードは登録できません。契約の確認が完了してからご利用ください。')
                return redirect('/')
    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        return redirect('kintai:contract_search')

    # 既に存在する場合は通常カレンダー入力へリダイレクト
    exists_timesheet = StaffTimesheet.objects.filter(
        staff_contract=contract,
        target_month=target_date
    ).first()
    if exists_timesheet:
        return redirect('kintai:timecard_calendar', timesheet_pk=exists_timesheet.pk)

    # 仮想Timesheetを作成
    virtual_timesheet = StaffTimesheet(
        staff_contract=contract,
        staff_id=contract.staff_id,
        target_month=target_date
    )


    if request.method == 'POST':
        # 月次勤怠を保存
        timesheet = virtual_timesheet
        timesheet.save()
        
        # フォームデータから日次勤怠を一括保存
        _, last_day = calendar.monthrange(year, month)
        
        for day in range(1, last_day + 1):
            work_date = date(year, month, day)
            
            # フォームデータを取得
            work_type = request.POST.get(f'work_type_{day}')
            work_time_pattern_work_id = request.POST.get(f'work_time_pattern_work_{day}')
            start_time_str = request.POST.get(f'start_time_{day}')
            start_time_next_day = request.POST.get(f'start_time_next_day_{day}') == 'on'
            end_time_str = request.POST.get(f'end_time_{day}')
            end_time_next_day = request.POST.get(f'end_time_next_day_{day}') == 'on'
            break_minutes = request.POST.get(f'break_minutes_{day}', 0)
            paid_leave_days = request.POST.get(f'paid_leave_days_{day}', 0)
            
            if not work_type:
                # 勤務区分が空の場合、既存のデータがあれば削除する
                StaffTimecard.objects.filter(
                    timesheet=timesheet,
                    work_date=work_date
                ).delete()
                continue

            # スタッフ契約の範囲外の日付は処理しない
            sc = contract
            if sc:
                sc_start = sc.start_date
                sc_end = sc.end_date
                if sc_start and work_date < sc_start:
                    continue
                if sc_end and work_date > sc_end:
                    continue
            
            # 時刻の変換
            from datetime import time as dt_time
            start_time = None
            end_time = None
            if start_time_str:
                try:
                    hour, minute = map(int, start_time_str.split(':'))
                    start_time = dt_time(hour, minute)
                except:
                    pass
            if end_time_str:
                try:
                    hour, minute = map(int, end_time_str.split(':'))
                    end_time = dt_time(hour, minute)
                except:
                    pass
            
            # 新規作成
            timecard = StaffTimecard(
                timesheet=timesheet,
                staff_contract=contract,
                work_date=work_date,
                work_type=work_type,
                start_time=start_time,
                start_time_next_day=start_time_next_day,
                end_time=end_time,
                end_time_next_day=end_time_next_day,
                break_minutes=int(break_minutes) if break_minutes else 0,
                paid_leave_days=float(paid_leave_days) if paid_leave_days else 0
            )
            
            # work_time_pattern_workを設定
            if work_time_pattern_work_id:
                try:
                    from apps.master.models import WorkTimePatternWork
                    timecard.work_time_pattern_work = WorkTimePatternWork.objects.get(pk=work_time_pattern_work_id)
                except WorkTimePatternWork.DoesNotExist:
                    timecard.work_time_pattern_work = None
            
            try:
                timecard.full_clean()
                timecard.save(skip_timesheet_update=True)  # 集計更新をスキップ
            except ValidationError as e:
                # エラーメッセージを作成
                error_messages = []
                for field, errors in e.message_dict.items():
                    for error in errors:
                        error_messages.append(f"{work_date.day}日: {error}")
                messages.error(request, " / ".join(error_messages))
        
        # すべての保存が完了した後、月次勤怠の集計を一度だけ更新
        timesheet.calculate_totals()
        
        messages.success(request, '月次勤怠と日次勤怠を作成しました。')
        return redirect('kintai:timesheet_detail', pk=timesheet.pk)

    # カレンダーデータを作成
    _, last_day = calendar.monthrange(year, month)
    
    calendar_data = []
    for day in range(1, last_day + 1):
        work_date = date(year, month, day)
        weekday = work_date.weekday()
        is_holiday = jpholiday.is_holiday(work_date)
        try:
            holiday_name = jpholiday.is_holiday_name(work_date)
        except Exception:
            holiday_name = None
        
        # スタッフ契約の範囲外の日付は表示しない
        sc = contract
        if sc:
            sc_start = sc.start_date
            sc_end = sc.end_date
            if sc_start and work_date < sc_start:
                continue
            if sc_end and work_date > sc_end:
                continue

        calendar_data.append({
            'day': day,
            'date': work_date,
            'holiday_name': holiday_name,
            'weekday': weekday,
            'is_holiday': is_holiday,
            'timecard': None, # 初回なのでtimecardは無し
        })
    
    # 契約情報のデフォルト値を取得
    default_values = _get_contract_work_time(contract)
    
    # 就業時間パターンから勤務時間一覧を取得
    work_times_data = _get_work_times_data(contract)

    context = {
        'timesheet': virtual_timesheet,
        'calendar_data': calendar_data,
        'default_start_time': default_values['start_time'],
        'default_end_time': default_values['end_time'],
        'default_break_minutes': default_values['break_minutes'],
        'work_times_data': work_times_data,
    }
    return render(request, 'kintai/timecard_calendar.html', context)


def _get_contract_work_time(contract):
    """
    契約情報からデフォルトの就業時間（開始、終了、休憩）を取得するヘルパー関数
    """
    default_values = {
        'start_time': '09:00',
        'end_time': '18:00',
        'break_minutes': '60',
    }
    
    if not contract or not contract.worktime_pattern:
        return default_values

    # 就業時間パターンから最初の勤務時間を取得
    # 表示順が一番早いものを採用
    work_time = contract.worktime_pattern.work_times.filter(
        time_name__is_active=True
    ).order_by('display_order').first()

    if work_time:
        default_values['start_time'] = work_time.start_time.strftime('%H:%M')
        default_values['end_time'] = work_time.end_time.strftime('%H:%M')
        
        # 休憩時間の合計を計算
        total_break_minutes = 0
        for break_time in work_time.break_times.all():
            # datetime.time オブジェクト同士の差分計算はできないため、datetime.datetime に変換
            from datetime import datetime, timedelta
            dummy_date = datetime(2000, 1, 1)
            start_dt = datetime.combine(dummy_date, break_time.start_time)
            end_dt = datetime.combine(dummy_date, break_time.end_time)
            
            # 日を跨ぐ場合の考慮（簡易的）
            if break_time.end_time_next_day:
                end_dt += timedelta(days=1)
            elif end_dt < start_dt:
                # フラグがなくても終了時刻が開始時刻より前の場合は翌日とみなす
                 end_dt += timedelta(days=1)

            diff = end_dt - start_dt
            total_break_minutes += int(diff.total_seconds() / 60)
        
        default_values['break_minutes'] = str(total_break_minutes)
            
    return default_values


def _get_work_times_data(contract):
    """
    契約の就業時間パターンから勤務時間一覧を取得し、JavaScript用のデータを返す
    """
    work_times_data = []
    
    if not contract or not contract.worktime_pattern:
        return work_times_data
    
    # 就業時間パターンから勤務時間一覧を取得
    work_times = contract.worktime_pattern.work_times.filter(
        time_name__is_active=True
    ).order_by('display_order').prefetch_related('break_times')
    
    for work_time in work_times:
        # 休憩時間の合計を計算
        total_break_minutes = 0
        for break_time in work_time.break_times.all():
            from datetime import datetime, timedelta
            dummy_date = datetime(2000, 1, 1)
            start_dt = datetime.combine(dummy_date, break_time.start_time)
            end_dt = datetime.combine(dummy_date, break_time.end_time)
            
            # 日を跨ぐ場合の考慮
            if break_time.end_time_next_day:
                end_dt += timedelta(days=1)
            elif end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            diff = end_dt - start_dt
            total_break_minutes += int(diff.total_seconds() / 60)
        
        work_times_data.append({
            'id': work_time.id,
            'name': work_time.time_name.content if work_time.time_name else '未設定',
            'start_time': work_time.start_time.strftime('%H:%M'),
            'end_time': work_time.end_time.strftime('%H:%M'),
            'start_time_next_day': work_time.start_time_next_day,
            'end_time_next_day': work_time.end_time_next_day,
            'break_minutes': total_break_minutes,
        })
    
    return work_times_data


# 勤怠CSV取込機能
@login_required
@permission_required('kintai.add_stafftimecard', raise_exception=True)
def timecard_import(request):
    """勤怠CSV取込ページを表示"""
    from apps.master.forms import CSVImportForm
    form = CSVImportForm()
    context = {
        'form': form,
        'title': '勤怠CSV取込',
    }
    return render(request, 'kintai/kintai_import.html', context)


@login_required
@permission_required('kintai.add_stafftimecard', raise_exception=True)
def timecard_import_upload(request):
    """CSVファイルをアップロードしてタスクIDを返す"""
    from django.views.decorators.http import require_POST
    from django.http import JsonResponse
    from apps.master.forms import CSVImportForm
    from django.core.cache import cache
    from datetime import datetime, timezone
    import uuid
    import os
    from django.conf import settings
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POSTメソッドが必要です。'}, status=405)
    
    form = CSVImportForm(request.POST, request.FILES)
    if form.is_valid():
        csv_file = request.FILES['csv_file']
        
        # 一時保存ディレクトリを作成
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        
        # ユニークなファイル名を生成
        task_id = str(uuid.uuid4())
        temp_file_path = os.path.join(temp_dir, f'{task_id}.csv')
        
        # ファイルを一時保存
        with open(temp_file_path, 'wb+') as f:
            for chunk in csv_file.chunks():
                f.write(chunk)
        
        # キャッシュにタスク情報を保存
        cache.set(
            f'import_task_{task_id}',
            {
                'file_path': temp_file_path,
                'status': 'uploaded',
                'progress': 0,
                'total': 0,
                'errors': [],
                'start_time': datetime.now(timezone.utc).isoformat(),
                'elapsed_time_seconds': 0,
                'estimated_time_remaining_seconds': 0,
            },
            timeout=3600,
        )
        
        return JsonResponse({'task_id': task_id})
    
    return JsonResponse({'error': 'CSVファイルのアップロードに失敗しました。'}, status=400)


@login_required
@permission_required('kintai.add_stafftimecard', raise_exception=True)
def timecard_import_process(request, task_id):
    """CSVファイルのインポート処理を実行"""
    from django.views.decorators.http import require_POST
    from django.http import JsonResponse
    from django.core.cache import cache
    from django.db import transaction
    from datetime import datetime, timezone, time as dt_time
    from apps.staff.models import Staff
    from apps.contract.models import StaffContract
    import csv
    import os
    
    from django.core.exceptions import ValidationError
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POSTメソッドが必要です。'}, status=405)
    
    task_info = cache.get(f'import_task_{task_id}')
    if not task_info or task_info['status'] != 'uploaded':
        return JsonResponse({'error': '無効なタスクIDです。'}, status=400)
    
    file_path = task_info['file_path']
    task_start_time = datetime.fromisoformat(task_info['start_time'])
    
    try:
        with open(file_path, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # ヘッダー行をスキップ
            if rows and rows[0][0] == '社員番号':
                rows = rows[1:]
            
            total_rows = len(rows)
        
        task_info['total'] = total_rows
        cache.set(f'import_task_{task_id}', task_info, timeout=3600)
        
        imported_count = 0
        errors = []
        updated_timesheets = set()  # 更新された月次勤怠を記録
        
        for i, row in enumerate(rows):
            progress = i + 1
            try:
                # 空行をスキップ
                if not row or not any(row):
                    continue
                
                with transaction.atomic():
                    # CSVデータを取得
                    employee_no = row[0].strip() if len(row) > 0 else ''
                    contract_number = row[1].strip() if len(row) > 1 else ''
                    work_date_str = row[2].strip() if len(row) > 2 else ''
                    work_type = row[3].strip() if len(row) > 3 else ''
                    # work_time_name = row[4].strip() if len(row) > 4 else ''  # 未使用
                    start_time_str = row[5].strip() if len(row) > 5 else ''
                    start_time_next_day = row[6].strip() if len(row) > 6 else '0'
                    end_time_str = row[7].strip() if len(row) > 7 else ''
                    end_time_next_day = row[8].strip() if len(row) > 8 else '0'
                    break_minutes_str = row[9].strip() if len(row) > 9 else '0'
                    paid_leave_days_str = row[10].strip() if len(row) > 10 else '0'
                    memo = row[11].strip() if len(row) > 11 else ''
                    
                    # 必須項目のチェック
                    if not employee_no:
                        errors.append(f'{progress}行目: 社員番号が入力されていません。')
                        continue
                    if not contract_number:
                        errors.append(f'{progress}行目: 契約番号が入力されていません。')
                        continue
                    if not work_date_str:
                        errors.append(f'{progress}行目: 勤務日が入力されていません。')
                        continue
                    if not work_type:
                        errors.append(f'{progress}行目: 勤務区分が入力されていません。')
                        continue
                    
                    # スタッフを検索
                    try:
                        staff = Staff.objects.get(employee_no=employee_no)
                    except Staff.DoesNotExist:
                        errors.append(f'{progress}行目: 社員番号 {employee_no} が見つかりません。')
                        continue
                    
                    # スタッフ契約を検索
                    try:
                        staff_contract = StaffContract.objects.get(
                            contract_number=contract_number,
                            staff_id=staff.id
                        )
                    except StaffContract.DoesNotExist:
                        errors.append(f'{progress}行目: 契約番号 {contract_number} が見つかりません。')
                        continue
                    
                    # 勤務日をパース
                    try:
                        from datetime import datetime as dt
                        work_date = dt.strptime(work_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        errors.append(f'{progress}行目: 勤務日の形式が不正です（YYYY-MM-DD形式で入力してください）。')
                        continue
                    
                    # 契約期間内かチェック
                    if staff_contract.start_date and work_date < staff_contract.start_date:
                        errors.append(f'{progress}行目: 勤務日が契約開始日より前です。')
                        continue
                    if staff_contract.end_date and work_date > staff_contract.end_date:
                        errors.append(f'{progress}行目: 勤務日が契約終了日より後です。')
                        continue
                    
                    # 時刻をパース
                    parsed_start_time = None
                    parsed_end_time = None
                    if start_time_str:
                        try:
                            hour, minute = map(int, start_time_str.split(':'))
                            parsed_start_time = dt_time(hour, minute)
                        except:
                            errors.append(f'{progress}行目: 開始時刻の形式が不正です（HH:MM形式で入力してください）。')
                            continue
                    if end_time_str:
                        try:
                            hour, minute = map(int, end_time_str.split(':'))
                            parsed_end_time = dt_time(hour, minute)
                        except:
                            errors.append(f'{progress}行目: 終了時刻の形式が不正です（HH:MM形式で入力してください）。')
                            continue
                    
                    # 出勤の場合は時刻が必須
                    if work_type == '10':  # 出勤
                        if not parsed_start_time or not parsed_end_time:
                            errors.append(f'{progress}行目: 出勤の場合は開始時刻と終了時刻が必須です。')
                            continue
                    
                    # 休憩時間と有給休暇日数をパース
                    try:
                        break_minutes = int(break_minutes_str) if break_minutes_str else 0
                    except ValueError:
                        break_minutes = 0
                    
                    try:
                        paid_leave_days = float(paid_leave_days_str) if paid_leave_days_str else 0
                    except ValueError:
                        paid_leave_days = 0
                    
                    # 翌日フラグを変換
                    start_next_day = start_time_next_day == '1'
                    end_next_day = end_time_next_day == '1'
                    
                    # 月次勤怠を取得または作成
                    target_month = work_date.replace(day=1)
                    timesheet, created = StaffTimesheet.objects.get_or_create(
                        staff_contract=staff_contract,
                        target_month=target_month,
                        defaults={'staff': staff}
                    )
                    
                    # 日次勤怠を作成・更新
                    timecard, created = StaffTimecard.objects.update_or_create(
                        timesheet=timesheet,
                        work_date=work_date,
                        defaults={
                            'staff_contract': staff_contract,
                            'work_type': work_type,
                            'start_time': parsed_start_time,
                            'start_time_next_day': start_next_day,
                            'end_time': parsed_end_time,
                            'end_time_next_day': end_next_day,
                            'break_minutes': break_minutes,
                            'paid_leave_days': paid_leave_days,
                            'memo': memo,
                        }
                    )
                    
                    # ここで full_clean() を呼び出す
                    try:
                        timecard.full_clean()
                        timecard.save(skip_timesheet_update=True) # full_clean() が通過した場合のみ保存
                    except ValidationError as e:
                        error_messages = []
                        for field, field_errors in e.message_dict.items():
                            for error in field_errors:
                                error_messages.append(f'{progress}行目 {field}: {error}')
                        errors.extend(error_messages)
                        # トランザクションをロールバックするために例外を再発生させる
                        raise
                    
                    # 更新された月次勤怠を記録
                    updated_timesheets.add(timesheet)
                    imported_count += 1
            
            except Exception as e:
                # ValidationError は既にerrorsリストに追加済み
                if not isinstance(e, ValidationError):
                    errors.append(f'{progress}行目: {str(e)}')
            
            # 進捗と時間を更新
            now = datetime.now(timezone.utc)
            elapsed_time = now - task_start_time
            
            if progress > 0 and total_rows > progress:
                estimated_time_remaining = (elapsed_time / progress) * (total_rows - progress)
                task_info['estimated_time_remaining_seconds'] = int(estimated_time_remaining.total_seconds())
            else:
                task_info['estimated_time_remaining_seconds'] = 0
            
            task_info['progress'] = progress
            task_info['elapsed_time_seconds'] = int(elapsed_time.total_seconds())
            cache.set(f'import_task_{task_id}', task_info, timeout=3600)
        
        # すべての保存が完了した後、影響を受けた月次勤怠の集計を一度だけ更新
        for timesheet in updated_timesheets:
            timesheet.refresh_from_db() # 最新の状態にリロード
            timesheet.calculate_totals()
        
        task_info['status'] = 'completed'
        task_info['errors'] = errors
        task_info['imported_count'] = imported_count
        cache.set(f'import_task_{task_id}', task_info, timeout=3600)
        
        return JsonResponse({
            'status': 'completed',
            'imported_count': imported_count,
            'errors': errors
        })
    
    except Exception as e:
        task_info['status'] = 'failed'
        
        # ValidationError の場合は400 Bad Requestを返す
        if isinstance(e, ValidationError):
            error_message = f'バリデーションエラー: {e.message}' if hasattr(e, 'message') else str(e)
            task_info['errors'] = [error_message]
            cache.set(f'import_task_{task_id}', task_info, timeout=3600)
            return JsonResponse({'error': error_message, 'errors': task_info['errors']}, status=400)
        else:
            task_info['errors'] = [f'処理中に予期せぬエラーが発生しました: {str(e)}']
            cache.set(f'import_task_{task_id}', task_info, timeout=3600)
            return JsonResponse({'error': str(e)}, status=500)
    finally:
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)


@login_required
@permission_required('kintai.add_stafftimecard', raise_exception=True)
def timecard_import_progress(request, task_id):
    """インポートの進捗状況を返す"""
    from django.http import JsonResponse
    from django.core.cache import cache
    
    task_info = cache.get(f'import_task_{task_id}')
    if not task_info:
        return JsonResponse({'error': '無効なタスクIDです。'}, status=404)
    
    return JsonResponse(task_info)




@login_required
@check_staff_agreement
def staff_timecard_register(request):
    """スタッフ向けタイムカード登録 - 契約選択画面"""
    from datetime import date

    from apps.contract.models import StaffContract
    from apps.staff.models import Staff
    
    # ログインユーザーに紐づくスタッフを取得
    try:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'スタッフ情報が見つかりません。管理者にお問い合わせください。')
        return redirect('/')
    
    # 年月の取得（デフォルトは当月）
    today = date.today()
    target_month_str = request.GET.get('target_month')
    
    if target_month_str:
        try:
            year, month = map(int, target_month_str.split('-'))
            target_date = date(year, month, 1)
        except ValueError:
            year = today.year
            month = today.month
            target_date = date(year, month, 1)
    else:
        year = today.year
        month = today.month
        target_date = date(year, month, 1)
    
    # 月末日を計算

    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)
    
    # 指定月に有効な契約を取得
    contracts = StaffContract.objects.filter(
        staff_id=staff.id,
        contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
        start_date__lte=month_end
    ).filter(
        Q(end_date__gte=target_date) | Q(end_date__isnull=True)
    ).order_by('-start_date')
    
    # 各契約の勤怠状況を確認
    contract_list = []
    for contract in contracts:
        timesheet = StaffTimesheet.objects.filter(
            staff_contract=contract,
            target_month=target_date
        ).first()
        
        input_days = 0
        if timesheet:
            input_days = timesheet.timecards.count()
        
        # 契約期間と対象月の重なる日数を計算
        c_start = contract.start_date
        c_end = contract.end_date
        
        overlap_start = max(target_date, c_start) if c_start else target_date
        overlap_end = min(month_end, c_end) if c_end else month_end
        
        if overlap_start <= overlap_end:
            required_days = (overlap_end - overlap_start).days + 1
        else:
            required_days = 0
        
        # ステータス判定
        status = 'not_input'  # 未入力
        if input_days > 0:
            if input_days >= required_days:
                status = 'inputted'  # 入力済
            else:
                status = 'inputting'  # 入力中
        
        contract_list.append({
            'contract': contract,
            'timesheet': timesheet,
            'input_days': input_days,
            'required_days': required_days,
            'status': status,
        })
    
    context = {
        'staff': staff,
        'contract_list': contract_list,
        'year': year,
        'month': month,
        'target_date': target_date,
    }
    return render(request, 'kintai/staff_timecard_register.html', context)


@login_required
@check_staff_agreement
def staff_timecard_register_detail(request, contract_pk, target_month):
    """スタッフ向けタイムカード登録 - 詳細入力画面"""
    from datetime import date, datetime
    from apps.contract.models import StaffContract
    from apps.staff.models import Staff
    
    # ログインユーザーに紐づくスタッフを取得
    try:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'スタッフ情報が見つかりません。管理者にお問い合わせください。')
        return redirect('/')
    
    # 契約を取得（自分の契約かつ確認済みのみ）
    contract = get_object_or_404(StaffContract, pk=contract_pk, staff_id=staff.id, contract_status=Constants.CONTRACT_STATUS.CONFIRMED)
    
    # 対象年月をパース
    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        messages.error(request, '無効な年月形式です。')
        return redirect('kintai:staff_timecard_register')
    

    # 月次勤怠を取得または作成
    timesheet, created = StaffTimesheet.objects.get_or_create(
        staff_contract=contract,
        target_month=target_date,
        defaults={
            'staff': staff,
        }
    )
    
    if created:
        messages.success(request, f'{year}年{month}月の月次勤怠を作成しました。')
    
    # カレンダー入力画面にリダイレクト
    return redirect('kintai:timecard_calendar', timesheet_pk=timesheet.pk)
from .models import ClientTimesheet, ClientTimecard
from .forms import ClientTimesheetForm, ClientTimecardForm
from apps.contract.models import ClientContract, ContractAssignment

@login_required
@permission_required('kintai.view_clienttimesheet', raise_exception=True)
def client_contract_search(request):
    """クライアント契約検索"""


    today = timezone.localdate()
    target_month_str = request.GET.get('target_month')

    if target_month_str:
        try:
            year, month = map(int, target_month_str.split('-'))
            target_date = date(year, month, 1)
        except ValueError:
            year, month = today.year, today.month
            target_date = date(year, month, 1)
    else:
        year, month = today.year, today.month
        target_date = date(year, month, 1)


    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    tenant_id = get_current_tenant_id()
    # 指定月に有効なアサインメント（契約とスタッフの紐づけ）を取得
    assignments = ContractAssignment.objects.select_related(
        'client_contract', 'client_contract__client', 'client_contract__payment_site', 'staff_contract', 'staff_contract__staff'
    ).filter(
        tenant_id=tenant_id
    ).filter(
        # アサイン割当期間が指定月と重なっているものを抽出
        Q(assignment_start_date__lte=month_end) & 
        (Q(assignment_end_date__gte=target_date) | Q(assignment_end_date__isnull=True))
    ).order_by('client_contract__client__name', 'staff_contract__staff__employee_no')

    # スタッフの注釈を事前に取得
    staff_ids = [a.staff_contract.staff_id for a in assignments]
    annotated_staffs = get_annotated_staff_queryset(request.user).filter(id__in=staff_ids).select_related('international', 'disability')
    staff_map = {s.id: s for s in annotated_staffs}

    assignment_list = []
    staff_to_annotate = []
    for assignment in assignments:
        # 注釈付きスタッフに差し替え
        staff = staff_map.get(assignment.staff_contract.staff_id)
        if staff:
            assignment.staff_contract.staff = staff
        else:
            staff = assignment.staff_contract.staff

        if staff not in staff_to_annotate:
            staff_to_annotate.append(staff)

        timesheet = ClientTimesheet.objects.filter(
            tenant_id=tenant_id,
            client_contract=assignment.client_contract,
            staff=staff,
            target_month=target_date
        ).first()

        input_days = 0
        if timesheet:
            input_days = timesheet.timecards.count()

        assignment_list.append({
            'assignment': assignment,
            'timesheet': timesheet,
            'input_days': input_days,
            'staff': staff,
        })

    # 接続情報の付与
    if staff_to_annotate:
        annotate_staff_connection_info(staff_to_annotate)

    from django.core.paginator import Paginator
    paginator = Paginator(assignment_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'assignment_list': page_obj,
        'page_obj': page_obj,
        'year': year,
        'month': month,
        'target_date': target_date,
    }
    return render(request, 'kintai/client_contract_search.html', context)

@login_required
@permission_required('kintai.add_clienttimesheet', raise_exception=True)
def client_timesheet_create(request):
    """クライアント月次勤怠作成"""
    if request.method == 'POST':
        form = ClientTimesheetForm(request.POST)
        if form.is_valid():
            timesheet = form.save()
            messages.success(request, 'クライアント月次勤怠を作成しました。')
            return redirect('kintai:client_timesheet_detail', pk=timesheet.pk)
    else:
        assignment_id = request.GET.get('assignment')
        target_month = request.GET.get('target_month')
        initial = {}
        if assignment_id:
            assignment = get_object_or_404(ContractAssignment, pk=assignment_id)
            initial['client_contract'] = assignment.client_contract
            initial['staff'] = assignment.staff_contract.staff
        if target_month:
            initial['target_month'] = target_month
        form = ClientTimesheetForm(initial=initial)

    context = {'form': form}
    return render(request, 'kintai/client_timesheet_form.html', context)

@login_required
@permission_required('kintai.view_clienttimesheet', raise_exception=True)
def client_timesheet_detail(request, pk):
    """クライアント月次勤怠詳細"""
    tenant_id = get_current_tenant_id()
    timesheet = get_object_or_404(ClientTimesheet.objects.select_related(
        'client_contract', 'client', 'staff'
    ), pk=pk, tenant_id=tenant_id)
    timecards = timesheet.timecards.all().order_by('work_date')

    for tc in timecards:
        tc.weekday = tc.work_date.weekday()
        tc.weekday_name = ['月', '火', '水', '木', '金', '土', '日'][tc.weekday]
        tc.is_national_holiday = jpholiday.is_holiday(tc.work_date)
        try:
            tc.holiday_name = jpholiday.is_holiday_name(tc.work_date)
        except:
            tc.holiday_name = None

    context = {
        'timesheet': timesheet,
        'timecards': timecards,
    }
    return render(request, 'kintai/client_timesheet_detail.html', context)

@login_required
@permission_required('kintai.add_clienttimecard', raise_exception=True)
def client_timecard_calendar_initial(request, assignment_pk, target_month):
    """クライアント日次勤怠カレンダー入力（初回作成）"""
    tenant_id = get_current_tenant_id()
    assignment = get_object_or_404(ContractAssignment, pk=assignment_pk, tenant_id=tenant_id)
    
    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        return redirect('kintai:client_contract_search')
    
    # 既に存在する場合は通常カレンダーへ
    exists_timesheet = ClientTimesheet.objects.filter(
        tenant_id=tenant_id,
        client_contract=assignment.client_contract,
        staff=assignment.staff_contract.staff,
        target_month=target_date
    ).first()
    if exists_timesheet:
        return redirect('kintai:client_timecard_calendar', pk=exists_timesheet.pk)

    # 仮想Timesheet
    virtual_timesheet = ClientTimesheet(
        tenant_id=tenant_id,
        client_contract=assignment.client_contract,
        client=assignment.client_contract.client,
        staff=assignment.staff_contract.staff,
        target_month=target_date,
        status='10'
    )

    if request.method == 'POST':
        # 月次勤怠を保存
        virtual_timesheet.save()
        timesheet = virtual_timesheet
        
        # フォームデータから日次勤怠を一括保存
        from datetime import time as dt_time
        _, last_day = calendar.monthrange(year, month)

        for day in range(1, last_day + 1):
            work_type = request.POST.get(f'work_type_{day}')

            if not work_type:
                continue

            start_time_str = request.POST.get(f'start_time_{day}')
            end_time_str = request.POST.get(f'end_time_{day}')

            start_time = None
            if start_time_str:
                h, m = map(int, start_time_str.split(':'))
                start_time = dt_time(h, m)

            end_time = None
            if end_time_str:
                h, m = map(int, end_time_str.split(':'))
                end_time = dt_time(h, m)

            timecard = ClientTimecard(
                timesheet=timesheet,
                work_date=date(year, month, day),
                client_contract=timesheet.client_contract,
                staff=timesheet.staff,
                tenant_id=tenant_id,
                work_type=work_type,
                start_time=start_time,
                end_time=end_time,
                start_time_next_day=request.POST.get(f'start_time_next_day_{day}') == 'on',
                end_time_next_day=request.POST.get(f'end_time_next_day_{day}') == 'on',
                break_minutes=int(request.POST.get(f'break_minutes_{day}', 0) or 0)
            )
            timecard.save(skip_timesheet_update=True)

        timesheet.calculate_totals()
        messages.success(request, '月次勤怠と日次勤怠を作成しました。')
        return redirect('kintai:client_timesheet_detail', pk=timesheet.pk)

    # GET時のカレンダーデータ
    _, last_day = calendar.monthrange(year, month)
    calendar_data = []
    for day in range(1, last_day + 1):
        work_date = date(year, month, day)
        is_holiday = jpholiday.is_holiday(work_date)
        try:
            holiday_name = jpholiday.is_holiday_name(work_date) if is_holiday else None
        except Exception:
            holiday_name = None

        calendar_data.append({
            'day': day,
            'date': work_date,
            'weekday': work_date.weekday(),
            'weekday_name': ['月', '火', '水', '木', '金', '土', '日'][work_date.weekday()],
            'is_weekend': work_date.weekday() >= 5,
            'is_holiday': is_holiday,
            'holiday_name': holiday_name,
            'timecard': None,
        })

    default_values = _get_contract_work_time(assignment.client_contract)
    
    contracts_work_times = {}
    if assignment.client_contract:
        contracts_work_times[assignment.client_contract.pk] = _get_work_times_data(assignment.client_contract)

    context = {
        'timesheet': virtual_timesheet,
        'calendar_data': calendar_data,
        'default_start_time': default_values['start_time'],
        'default_end_time': default_values['end_time'],
        'default_break_minutes': default_values['break_minutes'],
        'contracts_work_times_json': json.dumps(contracts_work_times),
        'is_initial': True,
        'assignment': assignment,
    }
    return render(request, 'kintai/client_timecard_calendar.html', context)


@login_required
@permission_required('kintai.change_clienttimecard', raise_exception=True)
def client_timecard_calendar(request, pk):
    """クライアント日次勤怠カレンダー入力"""
    tenant_id = get_current_tenant_id()
    timesheet = get_object_or_404(ClientTimesheet, pk=pk, tenant_id=tenant_id)

    if request.method == 'POST':
        year = timesheet.target_month.year
        month = timesheet.target_month.month
        _, last_day = calendar.monthrange(year, month)

        for day in range(1, last_day + 1):
            work_date = date(year, month, day)
            work_type = request.POST.get(f'work_type_{day}')

            if not work_type:
                ClientTimecard.objects.filter(tenant_id=tenant_id, timesheet=timesheet, work_date=work_date).delete()
                continue

            start_time_str = request.POST.get(f'start_time_{day}')
            end_time_str = request.POST.get(f'end_time_{day}')

            start_time = None
            if start_time_str:
                h, m = map(int, start_time_str.split(':'))
                start_time = dt_time(h, m)

            end_time = None
            if end_time_str:
                h, m = map(int, end_time_str.split(':'))
                end_time = dt_time(h, m)

            timecard, _ = ClientTimecard.objects.get_or_create(
                timesheet=timesheet,
                work_date=work_date,
                defaults={
                    'client_contract': timesheet.client_contract,
                    'staff': timesheet.staff,
                    'tenant_id': tenant_id
                }
            )
            timecard.work_type = work_type
            timecard.start_time = start_time
            timecard.end_time = end_time
            timecard.start_time_next_day = request.POST.get(f'start_time_next_day_{day}') == 'on'
            timecard.end_time_next_day = request.POST.get(f'end_time_next_day_{day}') == 'on'
            timecard.break_minutes = int(request.POST.get(f'break_minutes_{day}', 0) or 0)
            timecard.save(skip_timesheet_update=True)

        timesheet.refresh_from_db()
        timesheet.calculate_totals()
        messages.success(request, '一括保存しました。')
        return redirect('kintai:client_timesheet_detail', pk=timesheet.pk)

    year = timesheet.target_month.year
    month = timesheet.target_month.month
    _, last_day = calendar.monthrange(year, month)

    timecards_dict = {tc.work_date.day: tc for tc in timesheet.timecards.all()}

    calendar_data = []
    for day in range(1, last_day + 1):
        work_date = date(year, month, day)
        is_holiday = jpholiday.is_holiday(work_date)
        try:
            holiday_name = jpholiday.is_holiday_name(work_date) if is_holiday else None
        except Exception:
            holiday_name = None

        calendar_data.append({
            'day': day,
            'date': work_date,
            'weekday': work_date.weekday(),
            'weekday_name': ['月', '火', '水', '木', '金', '土', '日'][work_date.weekday()],
            'is_weekend': work_date.weekday() >= 5,
            'is_holiday': is_holiday,
            'holiday_name': holiday_name,
            'timecard': timecards_dict.get(day),
        })

    # デフォルト値を契約から取得
    default_values = _get_contract_work_time(timesheet.client_contract)
    
    # 就業時間パターンデータを取得
    import json
    contracts_work_times = {}
    if timesheet.client_contract:
        contracts_work_times[timesheet.client_contract.pk] = _get_work_times_data(timesheet.client_contract)

    context = {
        'timesheet': timesheet,
        'calendar_data': calendar_data,
        'default_start_time': default_values['start_time'],
        'default_end_time': default_values['end_time'],
        'default_break_minutes': default_values['break_minutes'],
        'contracts_work_times_json': json.dumps(contracts_work_times),
    }
    return render(request, 'kintai/client_timecard_calendar.html', context)


@login_required
@permission_required('kintai.delete_clienttimesheet', raise_exception=True)
def client_timesheet_delete(request, pk):
    """クライアント月次勤怠削除"""
    tenant_id = get_current_tenant_id()
    timesheet = get_object_or_404(ClientTimesheet, pk=pk, tenant_id=tenant_id)
    if request.method == 'POST':
        timesheet.delete()
        messages.success(request, 'クライアント月次勤怠を削除しました。')
        return redirect('kintai:client_contract_search')
    return render(request, 'kintai/client_timesheet_delete.html', {'timesheet': timesheet})


@login_required
@permission_required('kintai.view_clienttimesheet', raise_exception=True)
def client_timesheet_preview(request, assignment_pk, target_month):
    """クライアント月次勤怠プレビュー（未作成状態）"""
    tenant_id = get_current_tenant_id()
    assignment = get_object_or_404(ContractAssignment, pk=assignment_pk, tenant_id=tenant_id)

    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        return redirect('kintai:client_contract_search')

    # 既に存在する場合は詳細画面へリダイレクト
    exists_timesheet = ClientTimesheet.objects.filter(
        tenant_id=tenant_id,
        client_contract=assignment.client_contract,
        staff=assignment.staff_contract.staff,
        target_month=target_date
    ).first()
    if exists_timesheet:
        return redirect('kintai:client_timesheet_detail', pk=exists_timesheet.pk)

    # 仮想的なTimesheetオブジェクトを作成（DBには保存しない）
    timesheet = ClientTimesheet(
        tenant_id=tenant_id,
        client_contract=assignment.client_contract,
        client=assignment.client_contract.client,
        staff=assignment.staff_contract.staff,
        target_month=target_date,
        status='00'  # 未作成
    )
    # 集計値をハイフン表示するためにNoneを設定（テンプレート側で制御）
    timesheet.total_work_days = None
    timesheet.total_work_hours = None
    timesheet.total_overtime_hours = None
    timesheet.total_late_night_overtime_hours = None
    timesheet.total_holiday_work_hours = None
    timesheet.total_absence_days = None
    timesheet.total_paid_leave_days = None

    context = {
        'timesheet': timesheet,
        'timecards': [],
        'is_preview': True,  # プレビューモードフラグ
        'target_date': target_date,
        'assignment': assignment,
    }
    return render(request, 'kintai/client_timesheet_detail.html', context)


@login_required
@permission_required('kintai.add_clienttimecard', raise_exception=True)
def client_timecard_create(request, timesheet_pk):
    """クライアント日次勤怠作成"""
    tenant_id = get_current_tenant_id()
    timesheet = get_object_or_404(ClientTimesheet, pk=timesheet_pk, tenant_id=tenant_id)

    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:client_timesheet_detail', pk=timesheet_pk)

    if request.method == 'POST':
        form = ClientTimecardForm(request.POST, timesheet=timesheet)
        if form.is_valid():
            timecard = form.save(commit=False)
            timecard.timesheet = timesheet
            timecard.client_contract = timesheet.client_contract
            timecard.staff = timesheet.staff
            timecard.tenant_id = tenant_id
            timecard.save()
            messages.success(request, '日次勤怠を作成しました。')
            return redirect('kintai:client_timesheet_detail', pk=timesheet_pk)
    else:
        form = ClientTimecardForm(timesheet=timesheet)

    work_times_data = _get_work_times_data(timesheet.client_contract)

    context = {
        'form': form,
        'timesheet': timesheet,
        'work_times_data_json': json.dumps(work_times_data),
    }
    return render(request, 'kintai/client_timecard_form.html', context)


@login_required
@permission_required('kintai.add_clienttimecard', raise_exception=True)
def client_timecard_create_initial(request, assignment_pk, target_month):
    """クライアント初回日次勤怠作成（同時に月次勤怠も作成）"""
    tenant_id = get_current_tenant_id()
    assignment = get_object_or_404(ContractAssignment, pk=assignment_pk, tenant_id=tenant_id)

    try:
        year, month = map(int, target_month.split('-'))
        target_date = date(year, month, 1)
    except ValueError:
        return redirect('kintai:client_contract_search')

    # 既に存在する場合は通常作成へリダイレクト
    exists_timesheet = ClientTimesheet.objects.filter(
        tenant_id=tenant_id,
        client_contract=assignment.client_contract,
        staff=assignment.staff_contract.staff,
        target_month=target_date
    ).first()
    if exists_timesheet:
        return redirect('kintai:client_timecard_create', timesheet_pk=exists_timesheet.pk)

    # 仮想Timesheetを作成
    virtual_timesheet = ClientTimesheet(
        tenant_id=tenant_id,
        client_contract=assignment.client_contract,
        client=assignment.client_contract.client,
        staff=assignment.staff_contract.staff,
        target_month=target_date,
        status='10'
    )

    if request.method == 'POST':
        form = ClientTimecardForm(request.POST, timesheet=virtual_timesheet)
        if form.is_valid():
            virtual_timesheet.save()
            timecard = form.save(commit=False)
            timecard.timesheet = virtual_timesheet
            timecard.client_contract = virtual_timesheet.client_contract
            timecard.staff = virtual_timesheet.staff
            timecard.tenant_id = tenant_id
            timecard.save()
            messages.success(request, '月次勤怠と日次勤怠を作成しました。')
            return redirect('kintai:client_timesheet_detail', pk=virtual_timesheet.pk)
    else:
        form = ClientTimecardForm(timesheet=virtual_timesheet)

    work_times_data = _get_work_times_data(assignment.client_contract)

    context = {
        'form': form,
        'timesheet': virtual_timesheet,
        'is_preview': True,
        'work_times_data_json': json.dumps(work_times_data),
    }
    return render(request, 'kintai/client_timecard_form.html', context)


@login_required
@permission_required('kintai.change_clienttimecard', raise_exception=True)
def client_timecard_edit(request, pk):
    """クライアント日次勤怠編集"""
    tenant_id = get_current_tenant_id()
    timecard = get_object_or_404(ClientTimecard, pk=pk, tenant_id=tenant_id)
    timesheet = timecard.timesheet

    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:client_timesheet_detail', pk=timesheet.pk)

    if request.method == 'POST':
        form = ClientTimecardForm(request.POST, instance=timecard, timesheet=timesheet)
        if form.is_valid():
            form.save()
            messages.success(request, '日次勤怠を更新しました。')
            return redirect('kintai:client_timesheet_detail', pk=timesheet.pk)
    else:
        form = ClientTimecardForm(instance=timecard, timesheet=timesheet)

    work_times_data = _get_work_times_data(timesheet.client_contract)

    context = {
        'form': form,
        'timecard': timecard,
        'timesheet': timesheet,
        'work_times_data_json': json.dumps(work_times_data),
    }
    return render(request, 'kintai/client_timecard_form.html', context)


@login_required
@permission_required('kintai.delete_clienttimecard', raise_exception=True)
def client_timecard_delete(request, pk):
    """クライアント日次勤怠削除"""
    tenant_id = get_current_tenant_id()
    timecard = get_object_or_404(ClientTimecard, pk=pk, tenant_id=tenant_id)
    timesheet = timecard.timesheet

    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:client_timesheet_detail', pk=timesheet.pk)

    if request.method == 'POST':
        timecard.delete()
        timesheet.calculate_totals()
        messages.success(request, '日次勤怠を削除しました。')
        return redirect('kintai:client_timesheet_detail', pk=timesheet.pk)

    context = {
        'timecard': timecard,
    }
    return render(request, 'kintai/client_timecard_delete.html', context)


@login_required
@permission_required('kintai.view_stafftimesheet', raise_exception=True)
def kintai_status_management(request):
    """勤怠登録状況管理画面"""
    from datetime import date
    from calendar import monthrange
    from django.db.models import Q, Count, Max
    
    today = timezone.localdate()
    target_month_str = request.GET.get('target_month')
    
    if target_month_str:
        try:
            year, month = map(int, target_month_str.split('-'))
            target_date = date(year, month, 1)
        except ValueError:
            year, month = today.year, today.month
            target_date = date(year, month, 1)
    else:
        year, month = today.year, today.month
        target_date = date(year, month, 1)
    
    _, last_day = monthrange(year, month)
    month_end = date(year, month, last_day)
    
    tenant_id = get_current_tenant_id()
    
    # 指定月に有効なスタッフ契約を取得
    # APPROVED ('10'), ISSUED ('20'), CONFIRMED ('30') を含める
    contracts = StaffContract.objects.select_related(
        'staff'
    ).filter(
        tenant_id=tenant_id,
        contract_status__in=[
            Constants.CONTRACT_STATUS.APPROVED,
            Constants.CONTRACT_STATUS.ISSUED,
            Constants.CONTRACT_STATUS.CONFIRMED
        ],
        start_date__lte=month_end
    ).filter(
        Q(end_date__gte=target_date) | Q(end_date__isnull=True)
    ).order_by('staff__employee_no', '-start_date')
    
    # 各契約の勤怠登録状況を集計
    contract_status_list = []
    for contract in contracts:
        # 1. StaffTimerecord の登録状況
        timerecords = StaffTimerecord.objects.filter(
            staff_contract=contract,
            work_date__year=year,
            work_date__month=month
        )
        timerecord_count = timerecords.count()
        
        # 2. StaffTimerecordApproval の申請・承認状況
        approval = StaffTimerecordApproval.objects.unfiltered().filter(
            staff_contract=contract,
            period_start__lte=month_end,
            period_end__gte=target_date
        ).first()
        
        approval_status = None
        approval_status_display = '-'
        if approval:
            approval_status = approval.status
            approval_status_display = approval.get_status_display()
        
        # 3. StaffTimesheet の作成状況
        staff_timesheet = StaffTimesheet.objects.filter(
            staff_contract=contract,
            target_month=target_date
        ).first()
        
        staff_timesheet_status = None
        staff_timesheet_status_display = '-'
        staff_timecard_count = 0
        if staff_timesheet:
            staff_timesheet_status = staff_timesheet.status
            staff_timesheet_status_display = staff_timesheet.get_status_display()
            staff_timecard_count = staff_timesheet.timecards.count()
        
        # 4. ClientTimesheet の作成状況（契約アサインメント経由）
        from apps.contract.models import ContractAssignment
        assignments = ContractAssignment.objects.filter(
            staff_contract=contract,
            assignment_start_date__lte=month_end
        ).filter(
            Q(assignment_end_date__gte=target_date) | Q(assignment_end_date__isnull=True)
        ).select_related('client_contract', 'client_contract__client')

        client_timesheet_list = []
        for assignment in assignments:
            client_timesheet = ClientTimesheet.objects.filter(
                tenant_id=tenant_id,
                client_contract=assignment.client_contract,
                staff=contract.staff,
                target_month=target_date
            ).first()

            if client_timesheet:
                client_timecard_count = client_timesheet.timecards.count()
                client_timesheet_list.append({
                    'assignment': assignment,
                    'timesheet': client_timesheet,
                    'timecard_count': client_timecard_count,
                    'status_display': client_timesheet.get_status_display(),
                    'is_created': True
                })
            else:
                client_timesheet_list.append({
                    'assignment': assignment,
                    'timesheet': None,
                    'timecard_count': 0,
                    'status_display': '未作成',
                    'is_created': False
                })
        
        # 契約期間と対象月の重なる日数を計算
        c_start = contract.start_date
        c_end = contract.end_date
        
        overlap_start = max(target_date, c_start) if c_start else target_date
        overlap_end = min(month_end, c_end) if c_end else month_end
        
        if overlap_start <= overlap_end:
            required_days = (overlap_end - overlap_start).days + 1
        else:
            required_days = 0
        
        # 総合ステータスの判定
        overall_status = 'not_started'  # 未着手
        
        # 何らかのアクション（打刻、承認、勤怠作成）があるかチェック
        has_action = (
            timerecord_count > 0 or
            approval is not None or
            staff_timesheet is not None or
            any(ct['is_created'] for ct in client_timesheet_list)
        )

        if not has_action:
            overall_status = 'not_started'
        else:
            # 全て承認済みかチェック
            all_approved = True

            # スタッフ勤怠
            if not staff_timesheet or staff_timesheet.status != Constants.KINTAI_STATUS.APPROVED:
                all_approved = False

            # クライアント勤怠（アサインがある場合）
            if client_timesheet_list:
                if any(not ct['is_created'] or ct['timesheet'].status != Constants.KINTAI_STATUS.APPROVED for ct in client_timesheet_list):
                    all_approved = False

            if all_approved:
                overall_status = 'completed'
            else:
                # 進行中の詳細ステータス
                if client_timesheet_list and any(ct['is_created'] and ct['timesheet'].status == Constants.KINTAI_STATUS.APPROVED for ct in client_timesheet_list):
                    overall_status = 'in_progress'
                elif staff_timesheet and staff_timesheet.status == Constants.KINTAI_STATUS.APPROVED:
                    overall_status = 'staff_approved'
                elif approval and approval.status == Constants.KINTAI_STATUS.APPROVED:
                    overall_status = 'approval_approved'
                elif timerecord_count > 0:
                    overall_status = 'timerecord_exists'
                else:
                    overall_status = 'in_progress'
        
        contract_status_list.append({
            'contract': contract,
            'required_days': required_days,
            'timerecord_count': timerecord_count,
            'approval': approval,
            'approval_status': approval_status,
            'approval_status_display': approval_status_display,
            'staff_timesheet': staff_timesheet,
            'staff_timesheet_status': staff_timesheet_status,
            'staff_timesheet_status_display': staff_timesheet_status_display,
            'staff_timecard_count': staff_timecard_count,
            'client_timesheet_list': client_timesheet_list,
            'overall_status': overall_status,
        })
    
    # ステータスごとの集計
    status_summary = {
        'not_started': 0,
        'timerecord_exists': 0,
        'in_progress': 0,
        'approval_approved': 0,
        'staff_approved': 0,
        'completed': 0,
    }
    for item in contract_status_list:
        status = item['overall_status']
        if status in status_summary:
            status_summary[status] += 1
    
    from django.core.paginator import Paginator
    paginator = Paginator(contract_status_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'contract_status_list': page_obj,
        'page_obj': page_obj,
        'status_summary': status_summary,
        'year': year,
        'month': month,
        'target_date': target_date,
    }
    return render(request, 'kintai/kintai_status_management.html', context)
