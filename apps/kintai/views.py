from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import StaffTimesheet, StaffTimecard
from .forms import StaffTimesheetForm, StaffTimecardForm


@login_required
def timesheet_list(request):
    """月次勤怠一覧"""
    timesheets = StaffTimesheet.objects.select_related('staff', 'staff_contract').all()
    context = {
        'timesheets': timesheets,
    }
    return render(request, 'kintai/timesheet_list.html', context)


@login_required
def contract_search(request):
    """契約検索"""
    from datetime import date, datetime
    from django.db.models import Q
    from apps.contract.models import StaffContract
    
    # 年月の取得（デフォルトは当月）
    today = timezone.now().date()
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
    import calendar
    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    # 検索対象の契約を取得
    # 契約期間が指定月と重なるものを抽出
    # start_date <= month_end AND (end_date >= month_start OR end_date IS NULL)
    contracts = StaffContract.objects.select_related('staff').filter(
        start_date__lte=month_end
    ).filter(
        Q(end_date__gte=target_date) | Q(end_date__isnull=True)
    ).order_by('staff__employee_no')

    # 各契約に対して、指定月の勤怠が存在するかチェック
    contract_list = []
    for contract in contracts:
        timesheet = StaffTimesheet.objects.filter(
            staff_contract=contract,
            target_month=target_date
        ).first()
        
        contract_list.append({
            'contract': contract,
            'timesheet': timesheet,
        })

    context = {
        'contract_list': contract_list,
        'year': year,
        'month': month,
        'target_date': target_date,
    }
    return render(request, 'kintai/contract_search.html', context)


import json
from apps.contract.models import StaffContract

@login_required
def timesheet_create(request):
    """月次勤怠作成"""
    if request.method == 'POST':
        form = StaffTimesheetForm(request.POST)
        if form.is_valid():
            timesheet = form.save()
            messages.success(request, '月次勤怠を作成しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    else:
        today = timezone.now().date()
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
def timesheet_detail(request, pk):
    """月次勤怠詳細"""
    import jpholiday
    
    timesheet = get_object_or_404(StaffTimesheet.objects.select_related('staff', 'staff_contract'), pk=pk)
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
def timesheet_delete(request, pk):
    """月次勤怠削除"""
    timesheet = get_object_or_404(StaffTimesheet, pk=pk)
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
def timesheet_preview(request, contract_pk, target_month):
    """月次勤怠プレビュー（未作成状態）"""
    from datetime import datetime, date
    from apps.contract.models import StaffContract
    
    contract = get_object_or_404(StaffContract, pk=contract_pk)
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
        staff=contract.staff,
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
def timecard_create(request, timesheet_pk):
    """日次勤怠作成"""
    timesheet = get_object_or_404(StaffTimesheet, pk=timesheet_pk)
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet_pk)
    
    if request.method == 'POST':
        # pass timesheet to the form so form-level validation can check contract period
        form = StaffTimecardForm(request.POST, timesheet=timesheet)
        if form.is_valid():
            timecard = form.save(commit=False)
            timecard.timesheet = timesheet
            timecard.save()
            # 月次勤怠の集計を更新
            timesheet.calculate_totals()
            messages.success(request, '日次勤怠を作成しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet_pk)
    else:
        form = StaffTimecardForm()
    
    context = {
        'form': form,
        'timesheet': timesheet,
    }
    return render(request, 'kintai/timecard_form.html', context)


@login_required
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
        staff=contract.staff,
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
            timecard.save()
            
            # 集計更新
            timesheet.calculate_totals()
            
            messages.success(request, '月次勤怠と日次勤怠を作成しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    else:
        form = StaffTimecardForm()

    context = {
        'form': form,
        'timesheet': virtual_timesheet,
        'is_preview': True,
    }
    return render(request, 'kintai/timecard_form.html', context)


@login_required
def timecard_edit(request, pk):
    """日次勤怠編集"""
    timecard = get_object_or_404(StaffTimecard, pk=pk)
    timesheet = timecard.timesheet
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    
    if request.method == 'POST':
        form = StaffTimecardForm(request.POST, instance=timecard, timesheet=timesheet)
        if form.is_valid():
            form.save()
            # 月次勤怠の集計を更新
            timesheet.calculate_totals()
            messages.success(request, '日次勤怠を更新しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    else:
        form = StaffTimecardForm(instance=timecard)
    
    context = {
        'form': form,
        'timecard': timecard,
        'timesheet': timesheet,
    }
    return render(request, 'kintai/timecard_form.html', context)


@login_required
def timecard_delete(request, pk):
    """日次勤怠削除"""
    timecard = get_object_or_404(StaffTimecard, pk=pk)
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
def timecard_calendar(request, timesheet_pk):
    """日次勤怠カレンダー入力"""
    from datetime import date, timedelta
    import calendar
    import jpholiday
    
    timesheet = get_object_or_404(StaffTimesheet, pk=timesheet_pk)
    
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
            start_time_str = request.POST.get(f'start_time_{day}')
            start_time_next_day = request.POST.get(f'start_time_next_day_{day}') == 'on'
            end_time_str = request.POST.get(f'end_time_{day}')
            end_time_next_day = request.POST.get(f'end_time_next_day_{day}') == 'on'
            break_minutes = request.POST.get(f'break_minutes_{day}', 0)
            paid_leave_days = request.POST.get(f'paid_leave_days_{day}', 0)
            
            if not work_type:
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
            timecard, created = StaffTimecard.objects.get_or_create(
                timesheet=timesheet,
                work_date=work_date,
                defaults={'work_type': work_type}
            )
            
            # データを更新
            timecard.work_type = work_type
            timecard.start_time = start_time
            timecard.start_time_next_day = start_time_next_day
            timecard.end_time = end_time
            timecard.end_time_next_day = end_time_next_day
            timecard.break_minutes = int(break_minutes) if break_minutes else 0
            timecard.paid_leave_days = float(paid_leave_days) if paid_leave_days else 0
            timecard.save()
        
        # 月次勤怠の集計を更新
        timesheet.calculate_totals()
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
    
    context = {
        'timesheet': timesheet,
        'calendar_data': calendar_data,
    }
    return render(request, 'kintai/timecard_calendar.html', context)


@login_required
def timecard_calendar_initial(request, contract_pk, target_month):
    """初回日次勤怠カレンダー入力（同時に月次勤怠も作成）"""
    from datetime import date, timedelta
    import calendar
    import jpholiday
    from apps.contract.models import StaffContract
    
    contract = get_object_or_404(StaffContract, pk=contract_pk)
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
        staff=contract.staff,
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
            start_time_str = request.POST.get(f'start_time_{day}')
            start_time_next_day = request.POST.get(f'start_time_next_day_{day}') == 'on'
            end_time_str = request.POST.get(f'end_time_{day}')
            end_time_next_day = request.POST.get(f'end_time_next_day_{day}') == 'on'
            break_minutes = request.POST.get(f'break_minutes_{day}', 0)
            paid_leave_days = request.POST.get(f'paid_leave_days_{day}', 0)
            
            if not work_type:
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
                work_date=work_date,
                work_type=work_type,
                start_time=start_time,
                start_time_next_day=start_time_next_day,
                end_time=end_time,
                end_time_next_day=end_time_next_day,
                break_minutes=int(break_minutes) if break_minutes else 0,
                paid_leave_days=float(paid_leave_days) if paid_leave_days else 0
            )
            timecard.save()
        
        # 月次勤怠の集計を更新
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
    
    context = {
        'timesheet': virtual_timesheet,
        'calendar_data': calendar_data,
    }
    return render(request, 'kintai/timecard_calendar.html', context)
