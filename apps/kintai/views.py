from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
def timesheet_create(request):
    """月次勤怠作成"""
    if request.method == 'POST':
        form = StaffTimesheetForm(request.POST)
        if form.is_valid():
            timesheet = form.save()
            messages.success(request, '月次勤怠を作成しました。')
            return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    else:
        form = StaffTimesheetForm()
    
    context = {
        'form': form,
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
    
    context = {
        'timesheet': timesheet,
        'timecards': timecards,
    }
    return render(request, 'kintai/timesheet_detail.html', context)


@login_required
def timesheet_edit(request, pk):
    """月次勤怠編集"""
    timesheet = get_object_or_404(StaffTimesheet, pk=pk)
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=pk)
    
    if request.method == 'POST':
        form = StaffTimesheetForm(request.POST, instance=timesheet)
        if form.is_valid():
            form.save()
            messages.success(request, '月次勤怠を更新しました。')
            return redirect('kintai:timesheet_detail', pk=pk)
    else:
        form = StaffTimesheetForm(instance=timesheet)
    
    context = {
        'form': form,
        'timesheet': timesheet,
    }
    return render(request, 'kintai/timesheet_form.html', context)


@login_required
def timesheet_delete(request, pk):
    """月次勤怠削除"""
    timesheet = get_object_or_404(StaffTimesheet, pk=pk)
    if request.method == 'POST':
        timesheet.delete()
        messages.success(request, '月次勤怠を削除しました。')
        return redirect('kintai:timesheet_list')
    context = {
        'timesheet': timesheet,
    }
    return render(request, 'kintai/timesheet_delete.html', context)


@login_required
def timecard_create(request, timesheet_pk):
    """日次勤怠作成"""
    timesheet = get_object_or_404(StaffTimesheet, pk=timesheet_pk)
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet_pk)
    
    if request.method == 'POST':
        form = StaffTimecardForm(request.POST)
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
def timecard_edit(request, pk):
    """日次勤怠編集"""
    timecard = get_object_or_404(StaffTimecard, pk=pk)
    timesheet = timecard.timesheet
    
    if not timesheet.is_editable:
        messages.error(request, 'この月次勤怠は編集できません。')
        return redirect('kintai:timesheet_detail', pk=timesheet.pk)
    
    if request.method == 'POST':
        form = StaffTimecardForm(request.POST, instance=timecard)
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
        year = timesheet.year
        month = timesheet.month
        
        # 月の日数を取得
        _, last_day = calendar.monthrange(year, month)
        
        for day in range(1, last_day + 1):
            work_date = date(year, month, day)
            
            # フォームデータを取得
            work_type = request.POST.get(f'work_type_{day}')
            start_time_str = request.POST.get(f'start_time_{day}')
            end_time_str = request.POST.get(f'end_time_{day}')
            break_minutes = request.POST.get(f'break_minutes_{day}', 0)
            paid_leave_days = request.POST.get(f'paid_leave_days_{day}', 0)
            
            if not work_type:
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
            timecard.end_time = end_time
            timecard.break_minutes = int(break_minutes) if break_minutes else 0
            timecard.paid_leave_days = float(paid_leave_days) if paid_leave_days else 0
            timecard.save()
        
        # 月次勤怠の集計を更新
        timesheet.calculate_totals()
        messages.success(request, '日次勤怠を一括保存しました。')
        return redirect('kintai:timesheet_detail', pk=timesheet_pk)
    
    # カレンダーデータを作成
    year = timesheet.year
    month = timesheet.month
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
        
        timecard = timecards_dict.get(day)
        
        calendar_data.append({
            'day': day,
            'date': work_date,
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
