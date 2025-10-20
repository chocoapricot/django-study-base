from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from .models import HakenTeishokubiExempt
from .forms import HakenTeishokubiExemptForm


@login_required
@permission_required("master.view_hakenteishokubiexempt", raise_exception=True)
def haken_teishokubi_exempt_list(request):
    """派遣抵触日制限外一覧"""
    search_query = request.GET.get("search", "")
    items = HakenTeishokubiExempt.objects.all()
    if search_query:
        items = items.filter(content__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    
    # 変更履歴を取得
    from apps.system.logs.models import AppLog
    change_logs = AppLog.objects.filter(
        model_name="HakenTeishokubiExempt", 
        action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(
        model_name="HakenTeishokubiExempt", 
        action__in=["create", "update", "delete"]
    ).count()
    
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:haken_teishokubi_exempt_change_history_list",
    }
    return render(request, "master/haken_teishokubi_exempt_list.html", context)


@login_required
@permission_required("master.add_hakenteishokubiexempt", raise_exception=True)
def haken_teishokubi_exempt_create(request):
    """派遣抵触日制限外作成"""
    if request.method == "POST":
        form = HakenTeishokubiExemptForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"派遣抵触日制限外「{item.content[:30]}...」を作成しました。")
            return redirect("master:haken_teishokubi_exempt_list")
    else:
        form = HakenTeishokubiExemptForm()
    context = {"form": form, "title": "派遣抵触日制限外作成"}
    return render(request, "master/haken_teishokubi_exempt_form.html", context)


@login_required
@permission_required("master.change_hakenteishokubiexempt", raise_exception=True)
def haken_teishokubi_exempt_update(request, pk):
    """派遣抵触日制限外更新"""
    item = get_object_or_404(HakenTeishokubiExempt, pk=pk)
    if request.method == "POST":
        form = HakenTeishokubiExemptForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"派遣抵触日制限外「{item.content[:30]}...」を更新しました。")
            return redirect("master:haken_teishokubi_exempt_list")
    else:
        form = HakenTeishokubiExemptForm(instance=item)
    context = {"form": form, "title": "派遣抵触日制限外編集", "item": item}
    return render(request, "master/haken_teishokubi_exempt_form.html", context)


@login_required
@permission_required("master.delete_hakenteishokubiexempt", raise_exception=True)
def haken_teishokubi_exempt_delete(request, pk):
    """派遣抵触日制限外削除"""
    item = get_object_or_404(HakenTeishokubiExempt, pk=pk)
    if request.method == "POST":
        item_content = item.content[:30]
        item.delete()
        messages.success(request, f"派遣抵触日制限外「{item_content}...」を削除しました。")
        return redirect("master:haken_teishokubi_exempt_list")
    context = {"item": item, "title": "派遣抵触日制限外削除"}
    return render(request, "master/haken_teishokubi_exempt_confirm_delete.html", context)


# モーダル用のビューは不要（契約アプリの共通モーダルを使用）


@login_required
@permission_required("master.view_hakenteishokubiexempt", raise_exception=True)
def haken_teishokubi_exempt_change_history_list(request):
    """派遣抵触日制限外変更履歴一覧"""
    from apps.system.logs.models import AppLog
    
    logs = AppLog.objects.filter(
        model_name="HakenTeishokubiExempt",
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
            "page_title": "派遣抵触日制限外変更履歴",
            "back_url_name": "master:haken_teishokubi_exempt_list",
            "model_name": "HakenTeishokubiExempt",
        },
    )


# 関数ベースビューなので、as_view()は不要