from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import date, datetime, timedelta
from calendar import monthrange
import jpholiday
from django.utils import timezone
from .models import StaffTimerecord, StaffTimerecordBreak, StaffTimerecordApproval
from .forms import StaffTimerecordForm, StaffTimerecordBreakForm
from .utils import is_timerecord_locked
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.api.helpers import fetch_gsi_address
from apps.common.constants import Constants
from apps.profile.decorators import check_staff_agreement


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimerecord', raise_exception=True)
def timerecord_list(request):
    """勤怠打刻一覧"""
    # スタッフ特定（メールアドレス連携）
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

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
    timerecords = timerecords.select_related(
        'staff', 'staff__international', 'staff__disability'
    ).order_by('-work_date', '-created_at')
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
@check_staff_agreement
@permission_required('kintai.add_stafftimerecord', raise_exception=True)
def timerecord_create(request):
    """勤怠打刻作成"""
    staff = Staff.objects.unfiltered().filter(email=request.user.email).first()

    if request.method == 'POST':
        form = StaffTimerecordForm(request.POST, user=request.user)
        if form.is_valid():
            work_date = form.cleaned_data.get('work_date')
            staff_in_form = form.cleaned_data.get('staff_contract').staff if form.cleaned_data.get('staff_contract') else None
            # スタッフユーザーの場合は自分、管理者の場合はフォームのスタッフを確認
            target_staff = staff or staff_in_form
            if is_timerecord_locked(target_staff, work_date):
                messages.error(request, '申請済みまたは承認済みの勤怠は登録できません。')
                return redirect('kintai:timerecord_calender')

            timerecord = form.save()
            messages.success(request, '勤怠打刻を登録しました。')
            return redirect('kintai:timerecord_detail', pk=timerecord.pk)
        else:
            print("Form errors:", form.errors)
    else:
        # 初期値として今日の日付を設定
        initial = {'work_date': date.today()}
        # GETパラメータがあれば上書き
        if request.GET.get('work_date'):
            initial['work_date'] = request.GET.get('work_date')
        if request.GET.get('staff_contract'):
            initial['staff_contract'] = request.GET.get('staff_contract')

        form = StaffTimerecordForm(initial=initial, user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'kintai/timerecord_form.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimerecord', raise_exception=True)
def timerecord_calender(request):
    """勤怠打刻カレンダー表示"""
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

    if not staff:
        messages.error(request, 'スタッフ情報が見つかりません。')
        return redirect('/')

    # 対象年月
    target_month_str = request.GET.get('target_month', '')
    if target_month_str:
        try:
            target_month = datetime.strptime(target_month_str, '%Y-%m').date().replace(day=1)
        except ValueError:
            target_month = date.today().replace(day=1)
    else:
        target_month = date.today().replace(day=1)

    year = target_month.year
    month = target_month.month
    _, last_day_num = monthrange(year, month)
    first_day = date(year, month, 1)
    last_day = date(year, month, last_day_num)

    # 契約取得
    contracts = StaffContract.objects.filter(
        staff=staff,
        start_date__lte=last_day,
        contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
    ).filter(
        Q(end_date__gte=first_day) | Q(end_date__isnull=True)
    ).order_by('start_date')

    # 打刻データ取得
    timerecords = StaffTimerecord.objects.filter(
        staff=staff,
        work_date__range=(first_day, last_day)
    ).select_related('staff_contract').prefetch_related('breaks')

    timerecord_map = {tr.work_date: tr for tr in timerecords}

    # カレンダーデータ作成
    calendar_data = []
    for d_num in range(1, last_day_num + 1):
        work_date = date(year, month, d_num)

        # 該当日の有効な契約があるか確認
        active_contract = None
        for c in contracts:
            if c.start_date <= work_date and (c.end_date is None or c.end_date >= work_date):
                active_contract = c
                break

        # 契約がない期間は対象外
        if not active_contract:
            continue

        timerecord = timerecord_map.get(work_date)

        calendar_data.append({
            'date': work_date,
            'weekday': work_date.weekday(), # 0:Mon, 5:Sat, 6:Sun
            'is_holiday': jpholiday.is_holiday(work_date),
            'timerecord': timerecord,
            'contract': active_contract,
        })

    # 承認状況の取得
    approvals = StaffTimerecordApproval.objects.unfiltered().filter(
        staff=staff,
        closing_date=last_day
    )

    overall_status = '10'  # デフォルト：作成中
    if approvals.filter(status='30').exists():
        overall_status = '30'  # 承認済み
    elif approvals.filter(status='20').exists():
        overall_status = '20'  # 提出済み
    elif approvals.filter(status='40').exists():
        overall_status = '40'  # 差戻し

    context = {
        'staff': staff,
        'target_month': target_month,
        'calendar_data': calendar_data,
        'overall_status': overall_status,
        'is_locked': overall_status in ['20', '30'],
    }
    return render(request, 'kintai/timerecord_calender.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimerecord', raise_exception=True)
def timerecord_detail(request, pk):
    """勤怠打刻詳細"""
    timerecord = get_object_or_404(
        StaffTimerecord.objects.select_related('staff', 'staff__international', 'staff__disability'),
        pk=pk
    )
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

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
@require_POST
@permission_required('kintai.view_stafftimerecord', raise_exception=True)
def timerecord_reverse_geocode(request):
    """緯度経度から住所を取得し、DBに保存するAPI"""
    model_name = request.POST.get('model_name')
    object_id = request.POST.get('object_id')
    location_type = request.POST.get('type')  # 'start' or 'end'

    if not all([model_name, object_id, location_type]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    if model_name == 'timerecord':
        obj = get_object_or_404(StaffTimerecord, pk=object_id)
    elif model_name == 'break':
        obj = get_object_or_404(StaffTimerecordBreak, pk=object_id)
    else:
        return JsonResponse({'error': 'Invalid model_name'}, status=400)

    # 権限チェック（スタッフは自分のデータのみ）
    staff = Staff.objects.unfiltered().filter(email=request.user.email).first()
    if staff:
        if model_name == 'timerecord' and obj.staff != staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        elif model_name == 'break' and obj.timerecord.staff != staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)

    if location_type == 'start':
        lat = obj.start_latitude
        lng = obj.start_longitude
        address_field = 'start_address'
    elif location_type == 'end':
        lat = obj.end_latitude
        lng = obj.end_longitude
        address_field = 'end_address'
    else:
        return JsonResponse({'error': 'Invalid type'}, status=400)

    if not lat or not lng:
        return JsonResponse({'error': 'No location data'}, status=400)

    # 既に住所がある場合はそれを返す
    existing_address = getattr(obj, address_field)
    if existing_address:
        return JsonResponse({'address': existing_address})

    # 住所取得
    address = fetch_gsi_address(lat, lng)
    if address:
        setattr(obj, address_field, address)
        obj.save(update_fields=[address_field])
        return JsonResponse({'address': address})

    return JsonResponse({'error': 'Address not found'}, status=404)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimerecord', raise_exception=True)
def timerecord_update(request, pk):
    """勤怠打刻編集"""
    timerecord = get_object_or_404(StaffTimerecord, pk=pk)
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')

    # ロック状態の判定
    if is_timerecord_locked(timerecord.staff, timerecord.work_date):
        messages.error(request, '申請済みまたは承認済みの勤怠は編集できません。')
        return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    
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
@check_staff_agreement
@permission_required('kintai.delete_stafftimerecord', raise_exception=True)
def timerecord_delete(request, pk):
    """勤怠打刻削除"""
    timerecord = get_object_or_404(StaffTimerecord, pk=pk)
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ削除可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')

    # ロック状態の判定
    if is_timerecord_locked(timerecord.staff, timerecord.work_date):
        messages.error(request, '申請済みまたは承認済みの勤怠は削除できません。')
        return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    
    if request.method == 'POST':
        timerecord.delete()
        messages.success(request, '勤怠打刻を削除しました。')
        return redirect('kintai:timerecord_list')
    
    context = {
        'timerecord': timerecord,
    }
    return render(request, 'kintai/timerecord_confirm_delete.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimerecord', raise_exception=True)
def timerecord_break_create(request, timerecord_pk):
    """休憩時間作成"""
    timerecord = get_object_or_404(StaffTimerecord, pk=timerecord_pk)
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')

    # ロック状態の判定
    if is_timerecord_locked(timerecord.staff, timerecord.work_date):
        messages.error(request, '申請済みまたは承認済みの勤怠は編集できません。')
        return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    
    if request.method == 'POST':
        form = StaffTimerecordBreakForm(request.POST, timerecord=timerecord)
        if form.is_valid():
            break_record = form.save(commit=False)
            break_record.timerecord = timerecord
            break_record.save()
            messages.success(request, '休憩時間を登録しました。')
            return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    else:
        form = StaffTimerecordBreakForm(timerecord=timerecord)
    
    context = {
        'form': form,
        'timerecord': timerecord,
    }
    return render(request, 'kintai/timerecord_break_form.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimerecord', raise_exception=True)
def timerecord_break_update(request, pk):
    """休憩時間編集"""
    break_record = get_object_or_404(StaffTimerecordBreak, pk=pk)
    timerecord = break_record.timerecord
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')

    # ロック状態の判定
    if is_timerecord_locked(timerecord.staff, timerecord.work_date):
        messages.error(request, '申請済みまたは承認済みの勤怠は編集できません。')
        return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    
    if request.method == 'POST':
        form = StaffTimerecordBreakForm(request.POST, instance=break_record, timerecord=timerecord)
        if form.is_valid():
            form.save()
            messages.success(request, '休憩時間を更新しました。')
            return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    else:
        form = StaffTimerecordBreakForm(instance=break_record, timerecord=timerecord)
    
    context = {
        'form': form,
        'timerecord': timerecord,
        'break_record': break_record,
    }
    return render(request, 'kintai/timerecord_break_form.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimerecord', raise_exception=True)
def timerecord_break_delete(request, pk):
    """休憩時間削除"""
    break_record = get_object_or_404(StaffTimerecordBreak, pk=pk)
    timerecord = break_record.timerecord
    
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()

    # スタッフユーザーの場合は自分の打刻のみ編集可能
    if staff and timerecord.staff != staff:
        messages.error(request, 'アクセス権限がありません。')
        return redirect('kintai:timerecord_list')

    # ロック状態の判定
    if is_timerecord_locked(timerecord.staff, timerecord.work_date):
        messages.error(request, '申請済みまたは承認済みの勤怠は編集できません。')
        return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    
    if request.method == 'POST':
        break_record.delete()
        messages.success(request, '休憩時間を削除しました。')
        return redirect('kintai:timerecord_detail', pk=timerecord.pk)
    
    context = {
        'break_record': break_record,
        'timerecord': timerecord,
    }
    return render(request, 'kintai/timerecord_break_confirm_delete.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.view_stafftimerecord', raise_exception=True)
def timerecord_punch(request):
    """勤怠打刻画面（ダッシュボード形式）"""
    # スタッフ特定
    staff = None
    if request.user.email:
        staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()
    
    if not staff:
        messages.error(request, 'スタッフ情報が見つかりません。')
        return redirect('/')
    
    # 日本時間の今日を取得
    now_jst = timezone.localtime(timezone.now())
    today = now_jst.date()
    yesterday = today - timedelta(days=1)
    
    # 今日の有効かつ確認済みの契約を取得（複数の場合もある）
    # ※勤怠打刻マスタの打刻方法が「打刻」のもののみ対象とする
    available_contracts = StaffContract.objects.filter(
        staff=staff, 
        start_date__lte=today,
        contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
        time_punch__punch_method=Constants.PUNCH_METHOD.PUNCH
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).order_by('start_date')
    
    # 単一契約の場合は current_contract に設定
    current_contract = available_contracts.first() if available_contracts.count() == 1 else None
    
    # 時間丸め設定による休憩入力可否の判定
    show_break_buttons = True  # デフォルトは表示
    if current_contract and current_contract.time_punch:
        # 時間丸め設定で休憩入力が無効の場合は非表示
        show_break_buttons = current_contract.time_punch.break_input
    elif available_contracts.count() > 1:
        # 複数契約がある場合は、すべての契約で休憩入力が無効の場合のみ非表示
        show_break_buttons = any(
            contract.time_punch is None or contract.time_punch.break_input 
            for contract in available_contracts
        )
    
    # 位置情報取得設定の取得
    require_location_info = True  # デフォルトは取得する
    if current_contract and current_contract.time_punch:
        require_location_info = current_contract.time_punch.location_info
    elif available_contracts.count() > 1:
        # 複数契約がある場合は、どれか一つでも取得設定があれば取得を試みる（安全側）
        require_location_info = any(
            contract.time_punch is None or contract.time_punch.location_info 
            for contract in available_contracts
        )
    
    # 今日の打刻を優先取得（進行中・完了問わず、最新のもの）
    timerecord = StaffTimerecord.objects.filter(staff=staff, work_date=today).order_by('-start_time', '-id').first()

    # 今日のものがなければ、昨日の進行中の打刻（退勤していないもの、深夜勤務など）を優先的に取得
    if not timerecord:
        timerecord = StaffTimerecord.objects.filter(
            staff=staff,
            work_date=yesterday,
            end_time__isnull=True,
            rounded_end_time__isnull=True
        ).order_by('-start_time', '-id').first()
    
    # 状態判定
    status = 'not_started'  # 未出勤
    current_break = None
    
    if timerecord:
        if timerecord.end_time or timerecord.rounded_end_time:
            status = 'finished'  # 退勤済み
        else:
            # 休憩中かどうか確認
            current_break = timerecord.breaks.filter(
                break_end__isnull=True,
                rounded_break_end__isnull=True
            ).first()
            if current_break:
                status = 'on_break'  # 休憩中
            else:
                status = 'working'  # 勤務中
    
    # 進行中の打刻がある場合は、その契約をカレントとする
    if timerecord and timerecord.staff_contract:
        current_contract = timerecord.staff_contract
    
    # 位置情報取得設定の再判定（進行中の打刻契約がある場合を考慮）
    if current_contract and current_contract.time_punch:
        require_location_info = current_contract.time_punch.location_info
    elif available_contracts.count() > 1:
        require_location_info = any(
            contract.time_punch is None or contract.time_punch.location_info 
            for contract in available_contracts
        )
    
    # 取り消し可能判定（直近5分以内）
    can_cancel = False
    now = timezone.now()
    if timerecord:
        # 判定順序：退勤 -> 休憩完了 -> 休憩開始 -> 出勤
        if timerecord.end_time:
            if (now - timerecord.end_time).total_seconds() < 300:
                can_cancel = True
        else:
            # 最新の休憩（休憩開始時刻順で最後のもの）を取得
            last_break = timerecord.breaks.order_by('-break_start').first()
            if last_break:
                if last_break.break_end:
                    if (now - last_break.break_end).total_seconds() < 300:
                        can_cancel = True
                elif last_break.break_start and (now - last_break.break_start).total_seconds() < 300:
                    can_cancel = True
            
            if not can_cancel and timerecord.start_time and (now - timerecord.start_time).total_seconds() < 300:
                can_cancel = True

    # ロック状態の判定
    is_locked = is_timerecord_locked(staff, today)

    context = {
        'staff': staff,
        'timerecord': timerecord,
        'current_contract': current_contract,
        'available_contracts': available_contracts,
        'status': status,
        'current_break': current_break,
        'today': today,
        'can_cancel': can_cancel and not is_locked,
        'show_break_buttons': show_break_buttons,
        'require_location_info': require_location_info,
        'is_locked': is_locked,
    }
    return render(request, 'kintai/timerecord_punch.html', context)


@login_required
@check_staff_agreement
@permission_required('kintai.change_stafftimerecord', raise_exception=True)
def timerecord_action(request):
    """打刻アクション（出勤・退勤・休憩開始・休憩終了）"""
    if request.method != 'POST':
        return redirect('kintai:timerecord_punch')
    
    action = request.POST.get('action')
    now = timezone.now()
    now_jst = timezone.localtime(now)
    today = now_jst.date()
    yesterday = today - timedelta(days=1)
    
    # スタッフ特定
    staff = Staff.objects.unfiltered().select_related('international', 'disability').filter(email=request.user.email).first()
    if not staff:
        messages.error(request, 'スタッフ情報が見つかりません。')
        return redirect('/')

    # ロック状態の判定
    if is_timerecord_locked(staff, today):
        messages.error(request, '申請済みまたは承認済みの勤怠は打刻できません。')
        return redirect('kintai:timerecord_punch')
    
    # 位置情報
    lat = request.POST.get('latitude')
    lng = request.POST.get('longitude')
    address = request.POST.get('address')
    
    if action == 'start':
        # 出勤打刻
        # 進行中の打刻があるかチェック
        if StaffTimerecord.objects.filter(
            staff=staff,
            end_time__isnull=True,
            rounded_end_time__isnull=True
        ).exists():
            messages.warning(request, '既に勤務中（出勤打刻済み）です。')
        elif StaffTimerecord.objects.filter(staff=staff, work_date=today).exists():
            messages.warning(request, '本日は既に打刻（勤務完了）されています。')
        else:
            # 契約IDが指定されている場合はそれを使用、なければ有効かつ確認済みの契約を取得
            contract_id = request.POST.get('contract_id')
            if contract_id:
                try:
                    contract = StaffContract.objects.get(
                        id=contract_id,
                        staff=staff,
                        start_date__lte=today,
                        contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
                        time_punch__punch_method=Constants.PUNCH_METHOD.PUNCH
                    )
                    # 契約の有効性を再確認
                    if contract.end_date and contract.end_date < today:
                        contract = None
                except StaffContract.DoesNotExist:
                    contract = None
            else:
                # 有効かつ確認済みの契約を取得
                # ※勤怠打刻マスタの打刻方法が「打刻」のもののみ対象とする
                contract = StaffContract.objects.filter(
                    staff=staff, 
                    start_date__lte=today,
                    contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
                    time_punch__punch_method=Constants.PUNCH_METHOD.PUNCH
                ).filter(
                    Q(end_date__gte=today) | Q(end_date__isnull=True)
                ).first()
            
            if not contract:
                messages.error(request, f'{today.strftime("%Y/%m/%d")} に有効で確認済みのスタッフ契約がありません。打刻できません。')
            else:
                StaffTimerecord.objects.create(
                    staff=staff,
                    staff_contract=contract,
                    work_date=today,
                    start_time=now,
                    start_latitude=lat if lat else None,
                    start_longitude=lng if lng else None,
                    start_address=address if address else None
                )
                messages.success(request, f'{timezone.localtime(now).strftime("%H:%M")} に出勤打刻しました。')
            
    elif action == 'end':
        # 退勤打刻
        # 今日の打刻を優先取得
        timerecord = StaffTimerecord.objects.filter(staff=staff, work_date=today).order_by('-start_time', '-id').first()
        # 今日のがなければ進行中を取得
        if not timerecord:
            timerecord = StaffTimerecord.objects.filter(
                staff=staff,
                end_time__isnull=True,
                rounded_end_time__isnull=True
            ).order_by('-work_date', '-start_time', '-id').first()

        if timerecord:
            # 一昨日以前の打刻は操作不可
            if timerecord.work_date < yesterday:
                messages.error(request, f'{timerecord.work_date.strftime("%Y/%m/%d")} の打刻は一昨日以前のため操作できません。')
                return redirect('kintai:timerecord_punch')
            if timerecord.end_time or timerecord.rounded_end_time:
                messages.warning(request, '本日は既に退勤打刻済みです。')
            elif timerecord.breaks.filter(break_end__isnull=True, rounded_break_end__isnull=True).exists():
                # 休憩中の場合はエラー
                messages.error(request, '休憩を終了してから退勤打刻してください。')
            else:
                timerecord.end_time = now
                timerecord.end_latitude = lat if lat else None
                timerecord.end_longitude = lng if lng else None
                timerecord.end_address = address if address else None
                timerecord.save()
                messages.success(request, f'{timezone.localtime(now).strftime("%H:%M")} に退勤打刻しました。')
        else:
            messages.error(request, '出勤打刻が見つかりません。')
            
    elif action == 'break_start':
        # 休憩開始
        # 今日の打刻を優先取得
        timerecord = StaffTimerecord.objects.filter(staff=staff, work_date=today).order_by('-start_time', '-id').first()
        # 今日のがなければ進行中を取得
        if not timerecord:
            timerecord = StaffTimerecord.objects.filter(
                staff=staff,
                end_time__isnull=True,
                rounded_end_time__isnull=True
            ).order_by('-work_date', '-start_time', '-id').first()

        if timerecord:
            # 一昨日以前の打刻は操作不可
            if timerecord.work_date < yesterday:
                messages.error(request, f'{timerecord.work_date.strftime("%Y/%m/%d")} の打刻は一昨日以前のため操作できません。')
                return redirect('kintai:timerecord_punch')
            if timerecord.end_time or timerecord.rounded_end_time:
                messages.warning(request, '本日は既に退勤打刻済みです。')
            elif timerecord.breaks.filter(break_end__isnull=True, rounded_break_end__isnull=True).exists():
                messages.warning(request, '既に休憩中です。')
            else:
                StaffTimerecordBreak.objects.create(
                    timerecord=timerecord,
                    break_start=now,
                    start_latitude=lat if lat else None,
                    start_longitude=lng if lng else None,
                    start_address=address if address else None
                )
                messages.success(request, f'{timezone.localtime(now).strftime("%H:%M")} に休憩開始しました。')
        else:
            messages.error(request, '出勤打刻が見つかりません。')
            
    elif action == 'break_end':
        # 休憩終了
        # 今日の打刻を優先取得
        timerecord = StaffTimerecord.objects.filter(staff=staff, work_date=today).order_by('-start_time', '-id').first()
        # 今日のがなければ進行中を取得
        if not timerecord:
            timerecord = StaffTimerecord.objects.filter(
                staff=staff,
                end_time__isnull=True,
                rounded_end_time__isnull=True
            ).order_by('-work_date', '-start_time', '-id').first()

        if timerecord:
            # 一昨日以前の打刻は操作不可
            if timerecord.work_date < yesterday:
                messages.error(request, f'{timerecord.work_date.strftime("%Y/%m/%d")} の打刻は一昨日以前のため操作できません。')
                return redirect('kintai:timerecord_punch')
            if timerecord.end_time or timerecord.rounded_end_time:
                messages.warning(request, '本日は既に退勤打刻済みです。')
                return redirect('kintai:timerecord_punch')

            current_break = timerecord.breaks.filter(
                break_end__isnull=True,
                rounded_break_end__isnull=True
            ).first()
            if current_break:
                current_break.break_end = now
                current_break.end_latitude = lat if lat else None
                current_break.end_longitude = lng if lng else None
                current_break.end_address = address if address else None
                current_break.save()
                messages.success(request, f'{timezone.localtime(now).strftime("%H:%M")} に休憩終了しました。')
            else:
                messages.warning(request, '休憩中ではありません。')
        else:
            messages.error(request, '出勤打刻が見つかりません。')
            
    elif action == 'cancel':
        # 打刻の取り消し（5分以内）
        timerecord = StaffTimerecord.objects.filter(staff=staff).order_by('-work_date', '-start_time', '-id').first()
        if not timerecord:
            messages.error(request, '取り消し可能な打刻が見つかりません。')
            return redirect('kintai:timerecord_punch')

        cancelled = False
        msg = ""
        
        # 1. 退勤の取り消し
        if timerecord.end_time and (now - timerecord.end_time).total_seconds() < 300:
            timerecord.end_time = None
            timerecord.rounded_end_time = None
            timerecord.save()
            cancelled = True
            msg = "退勤打刻を取り消しました。"
        
        # 2. 休憩の取り消し
        if not cancelled:
            # 最新の休憩（休憩開始時刻順で最後のもの）を取得
            last_break = timerecord.breaks.order_by('-break_start').first()
            if last_break:
                if last_break.break_end and (now - last_break.break_end).total_seconds() < 300:
                    last_break.break_end = None
                    last_break.rounded_break_end = None
                    last_break.save()
                    cancelled = True
                    msg = "休憩終了を取り消しました。"
                elif not last_break.break_end and (now - last_break.break_start).total_seconds() < 300:
                    last_break.delete()
                    cancelled = True
                    msg = "休憩開始を取り消しました。"
        
        # 3. 出勤の取り消し
        if not cancelled and not timerecord.end_time:
            if (now - timerecord.start_time).total_seconds() < 300:
                timerecord.delete()
                cancelled = True
                msg = "出勤打刻を取り消しました。"
        
        if cancelled:
            messages.success(request, msg)
        else:
            messages.error(request, '直近5分以内の打刻が見つからないため、取り消しできません。')
            
    return redirect('kintai:timerecord_punch')


@login_required
@require_POST
@permission_required('kintai.add_stafftimerecord', raise_exception=True)
def timerecord_apply(request):
    """勤怠打刻申請"""
    target_month_str = request.POST.get('target_month')
    if not target_month_str:
        messages.error(request, '対象年月が指定されていません。')
        return redirect('kintai:timerecord_calender')

    try:
        target_month = datetime.strptime(target_month_str, '%Y-%m').date().replace(day=1)
    except ValueError:
        messages.error(request, '無効な年月形式です。')
        return redirect('kintai:timerecord_calender')

    # スタッフ特定
    staff = Staff.objects.unfiltered().filter(email=request.user.email).first()
    if not staff:
        messages.error(request, 'スタッフ情報が見つかりません。')
        return redirect('/')

    year = target_month.year
    month = target_month.month
    _, last_day_num = monthrange(year, month)
    first_day = date(year, month, 1)
    last_day = date(year, month, last_day_num)

    # 該当月の有効な契約を取得
    contracts = StaffContract.objects.unfiltered().filter(
        staff=staff,
        start_date__lte=last_day,
        contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
    ).filter(
        Q(end_date__gte=first_day) | Q(end_date__isnull=True)
    )

    if not contracts.exists():
        messages.error(request, '申請対象の契約が見つかりません。')
        return redirect('kintai:timerecord_calender')

    for contract in contracts:
        # 契約期間と月の重なりを計算
        period_start = max(first_day, contract.start_date)
        period_end = min(last_day, contract.end_date) if contract.end_date else last_day

        # 申請データを登録・更新
        StaffTimerecordApproval.objects.unfiltered().update_or_create(
            staff=staff,
            staff_contract=contract,
            closing_date=last_day,
            defaults={
                'period_start': period_start,
                'period_end': period_end,
                'status': '20',  # 提出済み
            }
        )

    messages.success(request, f'{target_month.strftime("%Y年%m月")}の勤怠を申請しました。')
    return redirect(f"{reverse('kintai:timerecord_calender')}?target_month={target_month_str}")


@login_required
@require_POST
@permission_required('kintai.add_stafftimerecord', raise_exception=True)
def timerecord_withdraw(request):
    """勤怠打刻申請取り戻し"""
    target_month_str = request.POST.get('target_month')
    if not target_month_str:
        messages.error(request, '対象年月が指定されていません。')
        return redirect('kintai:timerecord_calender')

    try:
        target_month = datetime.strptime(target_month_str, '%Y-%m').date().replace(day=1)
    except ValueError:
        messages.error(request, '無効な年月形式です。')
        return redirect('kintai:timerecord_calender')

    # スタッフ特定
    staff = Staff.objects.unfiltered().filter(email=request.user.email).first()
    if not staff:
        messages.error(request, 'スタッフ情報が見つかりません。')
        return redirect('/')

    year = target_month.year
    month = target_month.month
    _, last_day_num = monthrange(year, month)
    last_day = date(year, month, last_day_num)

    # 該当月の提出済みレコードを取得
    approvals = StaffTimerecordApproval.objects.unfiltered().filter(
        staff=staff,
        closing_date=last_day,
        status='20' # 提出済みのみ
    )

    if not approvals.exists():
        messages.error(request, '取り戻し可能な申請が見つかりません。')
    else:
        approvals.update(status='10') # 作成中に戻す
        messages.success(request, f'{target_month.strftime("%Y年%m月")}の勤怠申請を取り戻しました。')

    return redirect(f"{reverse('kintai:timerecord_calender')}?target_month={target_month_str}")
