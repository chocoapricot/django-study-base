from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from itertools import chain

from .models import WorkTimePattern, WorkTimePatternWork, WorkTimePatternBreak
from .forms_worktime import WorkTimePatternForm, WorkTimePatternWorkForm, WorkTimePatternBreakForm
from apps.system.logs.models import AppLog


@login_required
@permission_required("master.view_worktimepattern", raise_exception=True)
def worktime_pattern_list(request):
    """就業時間パターン一覧"""
    search_query = request.GET.get("search", "")
    patterns = WorkTimePattern.objects.all()
    
    if search_query:
        patterns = patterns.filter(name__icontains=search_query)
    
    patterns = patterns.order_by('display_order', 'name')
    
    paginator = Paginator(patterns, 20)
    page = request.GET.get("page")
    patterns_page = paginator.get_page(page)
    
    change_logs = AppLog.objects.filter(
        model_name__in=["WorkTimePattern", "WorkTimePatternWork", "WorkTimePatternBreak"], 
        action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]
    
    change_logs_count = AppLog.objects.filter(
        model_name__in=["WorkTimePattern", "WorkTimePatternWork", "WorkTimePatternBreak"], 
        action__in=["create", "update", "delete"]
    ).count()
    
    context = {
        'patterns': patterns_page,
        'search_query': search_query,
        'title': '就業時間パターン管理',
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    }
    return render(request, 'master/worktime_pattern_list.html', context)


@login_required
@permission_required("master.add_worktimepattern", raise_exception=True)
def worktime_pattern_create(request):
    """就業時間パターン作成"""
    if request.method == 'POST':
        form = WorkTimePatternForm(request.POST)
        if form.is_valid():
            pattern = form.save()
            messages.success(request, f"就業時間パターン「{pattern.name}」を作成しました。")
            return redirect('master:worktime_pattern_list')
    else:
        form = WorkTimePatternForm()
    
    context = {
        'form': form,
        'title': '就業時間パターン作成',
    }
    return render(request, 'master/worktime_pattern_form.html', context)


@login_required
@permission_required("master.change_worktimepattern", raise_exception=True)
def worktime_pattern_update(request, pk):
    """就業時間パターン編集"""
    pattern = get_object_or_404(WorkTimePattern, pk=pk)
    
    if request.method == 'POST':
        form = WorkTimePatternForm(request.POST, instance=pattern)
        if form.is_valid():
            pattern = form.save()
            messages.success(request, f"就業時間パターン「{pattern.name}」を更新しました。")
            return redirect('master:worktime_pattern_list')
    else:
        form = WorkTimePatternForm(instance=pattern)
    
    context = {
        'form': form,
        'pattern': pattern,
        'title': f'就業時間パターン編集 - {pattern.name}',
    }
    return render(request, 'master/worktime_pattern_form.html', context)


@login_required
@permission_required("master.view_worktimepattern", raise_exception=True)
def worktime_pattern_detail(request, pk):
    """就業時間パターン詳細"""
    pattern = get_object_or_404(WorkTimePattern, pk=pk)
    work_times = pattern.work_times.all()
    
    # 就業時間パターンの変更履歴
    pattern_logs = AppLog.objects.filter(
        model_name='WorkTimePattern',
        object_id=str(pattern.pk)
    )
    
    # 関連する勤務時間の変更履歴
    work_time_ids = [str(wt.pk) for wt in work_times]
    work_logs = AppLog.objects.filter(
        model_name='WorkTimePatternWork',
        object_id__in=work_time_ids
    )
    
    # 関連する休憩時間の変更履歴
    break_ids = []
    for wt in work_times:
        break_ids.extend([str(bt.pk) for bt in wt.break_times.all()])
    break_logs = AppLog.objects.filter(
        model_name='WorkTimePatternBreak',
        object_id__in=break_ids
    )
    
    # 履歴を結合してソート
    change_logs = sorted(
        chain(pattern_logs, work_logs, break_logs),
        key=lambda log: log.timestamp,
        reverse=True
    )
    
    context = {
        'pattern': pattern,
        'work_times': work_times,
        'title': f'就業時間パターン詳細 - {pattern.name}',
        'change_logs': change_logs[:5],
        'change_logs_count': len(change_logs),
    }
    return render(request, 'master/worktime_pattern_detail.html', context)


@login_required
@permission_required("master.delete_worktimepattern", raise_exception=True)
def worktime_pattern_delete(request, pk):
    """就業時間パターン削除"""
    pattern = get_object_or_404(WorkTimePattern, pk=pk)
    
    if request.method == 'POST':
        pattern_name = pattern.name
        pattern.delete()
        messages.success(request, f"就業時間パターン「{pattern_name}」を削除しました。")
        return redirect('master:worktime_pattern_list')
    
    context = {
        'pattern': pattern,
        'title': f'就業時間パターン削除 - {pattern.name}'
    }
    return render(request, 'master/worktime_pattern_confirm_delete.html', context)


@login_required
@permission_required("master.view_worktimepattern", raise_exception=True)
def worktime_pattern_change_history_list(request):
    """就業時間パターン変更履歴一覧"""
    logs = AppLog.objects.filter(
        model_name__in=["WorkTimePattern", "WorkTimePatternWork", "WorkTimePatternBreak"], 
        action__in=["create", "update", "delete"]
    ).order_by("-timestamp")
    
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "就業時間パターン変更履歴",
            "back_url_name": "master:worktime_pattern_list",
            "model_name": "WorkTimePattern",
        },
    )


# 勤務時間の管理
@login_required
@permission_required("master.add_worktimepatternwork", raise_exception=True)
def worktime_pattern_work_create(request, pattern_pk):
    """勤務時間作成"""
    pattern = get_object_or_404(WorkTimePattern, pk=pattern_pk)
    
    if request.method == 'POST':
        form = WorkTimePatternWorkForm(request.POST, worktime_pattern=pattern)
        if form.is_valid():
            work_time = form.save(commit=False)
            work_time.worktime_pattern = pattern
            work_time.save()
            messages.success(request, "勤務時間を作成しました。")
            return redirect('master:worktime_pattern_detail', pk=pattern_pk)
    else:
        form = WorkTimePatternWorkForm(worktime_pattern=pattern)
    
    context = {
        'form': form,
        'pattern': pattern,
        'title': '勤務時間作成'
    }
    return render(request, 'master/worktime_pattern_work_form.html', context)


@login_required
@permission_required("master.change_worktimepatternwork", raise_exception=True)
def worktime_pattern_work_update(request, pk):
    """勤務時間編集"""
    work_time = get_object_or_404(WorkTimePatternWork, pk=pk)
    pattern = work_time.worktime_pattern
    
    if request.method == 'POST':
        form = WorkTimePatternWorkForm(request.POST, instance=work_time)
        if form.is_valid():
            form.save()
            messages.success(request, "勤務時間を更新しました。")
            return redirect('master:worktime_pattern_detail', pk=pattern.pk)
    else:
        form = WorkTimePatternWorkForm(instance=work_time)
    
    context = {
        'form': form,
        'work_time': work_time,
        'pattern': pattern,
        'title': '勤務時間編集'
    }
    return render(request, 'master/worktime_pattern_work_form.html', context)


@login_required
@permission_required("master.delete_worktimepatternwork", raise_exception=True)
def worktime_pattern_work_delete(request, pk):
    """勤務時間削除"""
    work_time = get_object_or_404(WorkTimePatternWork, pk=pk)
    pattern_pk = work_time.worktime_pattern.pk
    
    if request.method == 'POST':
        work_time.delete()
        messages.success(request, "勤務時間を削除しました。")
        return redirect('master:worktime_pattern_detail', pk=pattern_pk)
    
    context = {
        'work_time': work_time,
        'title': '勤務時間削除'
    }
    return render(request, 'master/worktime_pattern_work_confirm_delete.html', context)


# 休憩時間の管理
@login_required
@permission_required("master.add_worktimepatternbreak", raise_exception=True)
def worktime_pattern_break_create(request, work_pk):
    """休憩時間作成"""
    work_time = get_object_or_404(WorkTimePatternWork, pk=work_pk)
    
    if request.method == 'POST':
        form = WorkTimePatternBreakForm(request.POST, work_time=work_time)
        if form.is_valid():
            break_time = form.save(commit=False)
            break_time.work_time = work_time
            break_time.save()
            messages.success(request, "休憩時間を作成しました。")
            return redirect('master:worktime_pattern_detail', pk=work_time.worktime_pattern.pk)
    else:
        form = WorkTimePatternBreakForm(work_time=work_time)
    
    context = {
        'form': form,
        'work_time': work_time,
        'title': f'休憩時間作成 - {work_time.get_full_display()}'
    }
    return render(request, 'master/worktime_pattern_break_form.html', context)


@login_required
@permission_required("master.change_worktimepatternbreak", raise_exception=True)
def worktime_pattern_break_update(request, pk):
    """休憩時間編集"""
    break_time = get_object_or_404(WorkTimePatternBreak, pk=pk)
    work_time = break_time.work_time
    
    if request.method == 'POST':
        form = WorkTimePatternBreakForm(request.POST, instance=break_time)
        if form.is_valid():
            form.save()
            messages.success(request, "休憩時間を更新しました。")
            return redirect('master:worktime_pattern_detail', pk=work_time.worktime_pattern.pk)
    else:
        form = WorkTimePatternBreakForm(instance=break_time)
    
    context = {
        'form': form,
        'break_time': break_time,
        'work_time': work_time,
        'title': f'休憩時間編集 - {work_time.get_full_display()}'
    }
    return render(request, 'master/worktime_pattern_break_form.html', context)


@login_required
@permission_required("master.delete_worktimepatternbreak", raise_exception=True)
def worktime_pattern_break_delete(request, pk):
    """休憩時間削除"""
    break_time = get_object_or_404(WorkTimePatternBreak, pk=pk)
    work_time = break_time.work_time
    pattern_pk = work_time.worktime_pattern.pk
    
    if request.method == 'POST':
        break_time.delete()
        messages.success(request, "休憩時間を削除しました。")
        return redirect('master:worktime_pattern_detail', pk=pattern_pk)
    
    context = {
        'break_time': break_time,
        'work_time': work_time,
        'title': f'休憩時間削除 - {work_time.get_full_display()}'
    }
    return render(request, 'master/worktime_pattern_break_confirm_delete.html', context)



@login_required
@permission_required("master.view_worktimepattern", raise_exception=True)
def worktime_pattern_select_modal(request):
    """就業時間パターン選択モーダル用API"""
    search_query = request.GET.get("q", "")
    patterns = WorkTimePattern.objects.filter(is_active=True)
    
    if search_query:
        patterns = patterns.filter(name__icontains=search_query)
    
    patterns = patterns.order_by('display_order', 'name')
    
    # ページネーション
    paginator = Paginator(patterns, 10)
    page = request.GET.get("page", 1)
    patterns_page = paginator.get_page(page)
    
    # JSON形式でデータを返す
    data = {
        'patterns': [],
        'has_previous': patterns_page.has_previous(),
        'has_next': patterns_page.has_next(),
        'current_page': patterns_page.number,
        'total_pages': paginator.num_pages,
    }
    
    for pattern in patterns_page:
        work_times = pattern.work_times.all()
        work_times_data = []
        for wt in work_times:
            breaks = wt.break_times.all()
            breaks_data = [
                {
                    'start_time': bt.start_time.strftime('%H:%M'),
                    'start_time_next_day': bt.start_time_next_day,
                    'end_time': bt.end_time.strftime('%H:%M'),
                    'end_time_next_day': bt.end_time_next_day,
                }
                for bt in breaks
            ]
            work_times_data.append({
                'time_name': wt.time_name.content if wt.time_name else '',
                'start_time': wt.start_time.strftime('%H:%M'),
                'start_time_next_day': wt.start_time_next_day,
                'end_time': wt.end_time.strftime('%H:%M'),
                'end_time_next_day': wt.end_time_next_day,
                'breaks': breaks_data,
            })
        
        data['patterns'].append({
            'id': pattern.id,
            'name': pattern.name,
            'memo': pattern.memo or '',
            'work_times': work_times_data,
        })
    
    return JsonResponse(data)
