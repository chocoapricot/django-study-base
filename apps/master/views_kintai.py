from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import (
    OvertimePattern,
)
from .models_kintai import (
    TimePunch,
)
from .forms_kintai import (
    OvertimePatternForm,
)
from apps.system.logs.models import AppLog

# 時間外算出パターン管理ビュー
@login_required
@permission_required("master.view_overtimepattern", raise_exception=True)
def overtime_pattern_list(request):
    """時間外算出パターン一覧"""
    search_query = request.GET.get("search", "")
    items = OvertimePattern.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="OvertimePattern", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="OvertimePattern", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:overtime_pattern_change_history_list",
    }
    return render(request, "master/overtime_pattern_list.html", context)


@login_required
@permission_required("master.add_overtimepattern", raise_exception=True)
def overtime_pattern_create(request):
    """時間外算出パターン作成"""
    if request.method == "POST":
        form = OvertimePatternForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"時間外算出パターン「{item.name}」を作成しました。")
            return redirect("master:overtime_pattern_list")
    else:
        form = OvertimePatternForm()
    context = {"form": form, "title": "時間外算出パターン作成"}
    return render(request, "master/overtime_pattern_form.html", context)


@login_required
@permission_required("master.change_overtimepattern", raise_exception=True)
def overtime_pattern_update(request, pk):
    """時間外算出パターン編集"""
    item = get_object_or_404(OvertimePattern, pk=pk)
    if request.method == "POST":
        form = OvertimePatternForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"時間外算出パターン「{item.name}」を更新しました。")
            return redirect("master:overtime_pattern_list")
    else:
        form = OvertimePatternForm(instance=item)
    context = {"form": form, "item": item, "title": f"時間外算出パターン編集"}
    return render(request, "master/overtime_pattern_form.html", context)


@login_required
@permission_required("master.delete_overtimepattern", raise_exception=True)
def overtime_pattern_delete(request, pk):
    """時間外算出パターン削除"""
    item = get_object_or_404(OvertimePattern, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"時間外算出パターン「{item_name}」を削除しました。")
        return redirect("master:overtime_pattern_list")
    context = {"item": item, "title": f"時間外算出パターン削除"}
    return render(request, "master/overtime_pattern_delete.html", context)


@login_required
@permission_required("master.view_overtimepattern", raise_exception=True)
def overtime_pattern_change_history_list(request):
    """時間外算出パターン変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="OvertimePattern", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "時間外算出パターン変更履歴",
            "back_url_name": "master:overtime_pattern_list",
            "model_name": "OvertimePattern",
        },
    )


@login_required
@permission_required("master.view_overtimepattern", raise_exception=True)
def overtime_pattern_select_modal(request):
    """時間外算出パターン選択モーダル用API"""
    search_query = request.GET.get("q", "")
    patterns = OvertimePattern.objects.filter(is_active=True)

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
        # 計算方式の表示名を取得
        calculation_type_display = pattern.get_calculation_type_display()

        # 設定内容を構築
        settings = []
        if pattern.calculation_type == 'premium':
            if pattern.daily_overtime_enabled:
                if pattern.daily_overtime_minutes:
                    settings.append(f"日{pattern.daily_overtime_hours}:{pattern.daily_overtime_minutes:02d}")
                else:
                    settings.append(f"日{pattern.daily_overtime_hours}h")
            if pattern.weekly_overtime_enabled:
                if pattern.weekly_overtime_minutes:
                    settings.append(f"週{pattern.weekly_overtime_hours}:{pattern.weekly_overtime_minutes:02d}")
                else:
                    settings.append(f"週{pattern.weekly_overtime_hours}h")
            if pattern.monthly_overtime_enabled:
                settings.append(f"月{pattern.monthly_overtime_hours}h")
            if pattern.monthly_estimated_enabled:
                settings.append(f"見込{pattern.monthly_estimated_hours}h")
        elif pattern.calculation_type == 'monthly_range':
            settings.append(f"{pattern.monthly_range_min}～{pattern.monthly_range_max}h")
        elif pattern.calculation_type == 'variable':
            if pattern.daily_overtime_enabled:
                if pattern.daily_overtime_minutes:
                    settings.append(f"日{pattern.daily_overtime_hours}:{pattern.daily_overtime_minutes:02d}")
                else:
                    settings.append(f"日{pattern.daily_overtime_hours}h")
            if pattern.weekly_overtime_enabled:
                if pattern.weekly_overtime_minutes:
                    settings.append(f"週{pattern.weekly_overtime_hours}:{pattern.weekly_overtime_minutes:02d}")
                else:
                    settings.append(f"週{pattern.weekly_overtime_hours}h")
            if pattern.monthly_overtime_enabled:
                settings.append(f"月{pattern.monthly_overtime_hours}h")
            if pattern.monthly_estimated_enabled:
                settings.append(f"見込{pattern.monthly_estimated_hours}h")

        data['patterns'].append({
            'id': pattern.id,
            'name': pattern.name,
            'calculation_type': pattern.calculation_type,
            'calculation_type_display': calculation_type_display,
            'settings': ' '.join(settings) if settings else '未設定',
            'memo': pattern.memo or '',
        })

    return JsonResponse(data)


@login_required
@permission_required("master.view_timepunch", raise_exception=True)
def time_rounding_select_modal(request):
    """時間丸めパターン選択モーダル用API"""
    search_query = request.GET.get("q", "")
    patterns = TimePunch.objects.filter(is_active=True)

    if search_query:
        patterns = patterns.filter(name__icontains=search_query)

    patterns = patterns.order_by('sort_order', 'name')

    # ページネーション
    paginator = Paginator(patterns, 10)
    page = request.GET.get("page", 1)
    patterns_page = paginator.get_page(page)

    # JSON形式でデータを返す
    data = {
        'time_roundings': [],
        'has_previous': patterns_page.has_previous(),
        'has_next': patterns_page.has_next(),
        'previous_page_number': patterns_page.previous_page_number() if patterns_page.has_previous() else None,
        'next_page_number': patterns_page.next_page_number() if patterns_page.has_next() else None,
        'page_number': patterns_page.number,
        'num_pages': paginator.num_pages,
    }

    for pattern in patterns_page:
        data['time_roundings'].append({
            'id': pattern.id,
            'name': pattern.name,
            'rounding_summary': pattern.get_rounding_summary(),
            'description': pattern.description or '',
        })

    return JsonResponse(data)
