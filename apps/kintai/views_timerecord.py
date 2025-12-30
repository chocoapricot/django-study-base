from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import date, datetime
from .models import StaffTimerecord, StaffTimerecordBreak
from .forms import StaffTimerecordForm, StaffTimerecordBreakForm
from apps.staff.models import Staff


@login_required
def timerecord_list(request):
    """勤怠打刻一覧"""
    # スタッフ特定（メールアドレス連携）
    staff = None
    if request.user.email:
        staff = Staff.objects.filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ表示
    if staff:
        timerecords = StaffTimerecord.objects.filter(staff=staff)
    else:
        timerecords = StaffTimerecord.objects.all()
    
    # 検索
    search_query = request.GET.get('q', '')
    if search_query:
        timerecords = timerecords.filter(
            Q(staff__name_last__icontains=search_query) |
            Q(staff__name_first__icontains=search_query) |
            Q(staff__staff_id__icontains=search_query)
        )
    
    # 日付フィルタ
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        timerecords = timerecords.filter(work_date__gte=date_from)
    if date_to:
        timerecords = timerecords.filter(work_date__lte=date_to)
    
    # ページネーション
    timerecords = timerecords.select_related('staff').order_by('-work_date', '-created_at')
    paginator = Paginator(timerecords, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'kintai/timerecord_list.html', context)


@login_required
def timerecord_create(request):
    """勤怠打刻作成"""
    if request.method == 'POST':
        form = StaffTimerecordForm(request.POST, user=request.user)
        if form.is_valid():
            timerecord = form.save()
            messages.success(request, '勤怠打刻を登録しました。')
            return redirect('kintai:timerecord_detail', pk=timerecord.pk)
        else:
            print("Form errors:", form.errors)
    else:
        # 初期値として今日の日付を設定
        initial = {'work_date': date.today()}
        form = StaffTimerecordForm(initial=initial, user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'kintai/timerecord_form.html', context)


@login_required
def timerecord_detail(request, pk):
    """勤怠打刻詳細"""
    timerecord = get_object_or_404(StaffTimerecord, pk=pk)
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ表示
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')
    
    # 休憩時間を取得
    breaks = timerecord.breaks.all().order_by('break_start')
    
    context = {
        'timerecord': timerecord,
        'breaks': breaks,
    }
    return render(request, 'kintai/timerecord_detail.html', context)


@login_required
def timerecord_update(request, pk):
    """勤怠打刻編集"""
    timerecord = get_object_or_404(StaffTimerecord, pk=pk)
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')
    
    if request.method == 'POST':
        form = StaffTimerecordForm(request.POST, instance=timerecord, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '勤怠打刻を更新しました。')
            return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    else:
        form = StaffTimerecordForm(instance=timerecord, user=request.user)
    
    context = {
        'form': form,
        'timerecord': timerecord,
    }
    return render(request, 'kintai/timerecord_form.html', context)


@login_required
def timerecord_delete(request, pk):
    """勤怠打刻削除"""
    timerecord = get_object_or_404(StaffTimerecord, pk=pk)
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ削除可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')
    
    if request.method == 'POST':
        timerecord.delete()
        messages.success(request, '勤怠打刻を削除しました。')
        return redirect('kintai:timerecord_list')
    
    context = {
        'timerecord': timerecord,
    }
    return render(request, 'kintai/timerecord_confirm_delete.html', context)


@login_required
def timerecord_break_create(request, timerecord_pk):
    """休憩時間作成"""
    timerecord = get_object_or_404(StaffTimerecord, pk=timerecord_pk)
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')
    
    if request.method == 'POST':
        form = StaffTimerecordBreakForm(request.POST)
        if form.is_valid():
            break_record = form.save(commit=False)
            break_record.timerecord = timerecord
            break_record.save()
            messages.success(request, '休憩時間を登録しました。')
            return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    else:
        form = StaffTimerecordBreakForm()
    
    context = {
        'form': form,
        'timerecord': timerecord,
    }
    return render(request, 'kintai/timerecord_break_form.html', context)


@login_required
def timerecord_break_update(request, pk):
    """休憩時間編集"""
    break_record = get_object_or_404(StaffTimerecordBreak, pk=pk)
    timerecord = break_record.timerecord
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')
    
    if request.method == 'POST':
        form = StaffTimerecordBreakForm(request.POST, instance=break_record)
        if form.is_valid():
            form.save()
            messages.success(request, '休憩時間を更新しました。')
            return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    else:
        form = StaffTimerecordBreakForm(instance=break_record)
    
    context = {
        'form': form,
        'timerecord': timerecord,
        'break_record': break_record,
    }
    return render(request, 'kintai/timerecord_break_form.html', context)


@login_required
def timerecord_break_delete(request, pk):
    """休憩時間削除"""
    break_record = get_object_or_404(StaffTimerecordBreak, pk=pk)
    timerecord = break_record.timerecord
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')
    
    if request.method == 'POST':
        break_record.delete()
        messages.success(request, '休憩時間を削除しました。')
        return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    
    context = {
        'break_record': break_record,
        'timerecord': timerecord,
    }
    return render(request, 'kintai/timerecord_break_confirm_delete.html', context)
