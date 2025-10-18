from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import (
    ClientRegistStatus,
)
from .forms import (
    ClientRegistStatusForm,
)
from apps.system.logs.models import AppLog

# クライアント登録状況管理ビュー
@login_required
@permission_required("master.view_clientregiststatus", raise_exception=True)
def client_regist_status_list(request):
    """クライアント登録状況一覧"""
    search_query = request.GET.get("search", "")
    items = ClientRegistStatus.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="ClientRegistStatus", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="ClientRegistStatus", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:client_regist_status_change_history_list",
    }
    return render(request, "master/client_regist_status_list.html", context)


@login_required
@permission_required("master.add_clientregiststatus", raise_exception=True)
def client_regist_status_create(request):
    """クライアント登録状況作成"""
    if request.method == "POST":
        form = ClientRegistStatusForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"クライアント登録状況「{item.name}」を作成しました。")
            return redirect("master:client_regist_status_list")
    else:
        form = ClientRegistStatusForm()
    context = {"form": form, "title": "クライアント登録状況作成"}
    return render(request, "master/client_regist_status_form.html", context)


@login_required
@permission_required("master.change_clientregiststatus", raise_exception=True)
def client_regist_status_update(request, pk):
    """クライアント登録状況編集"""
    item = get_object_or_404(ClientRegistStatus, pk=pk)
    if request.method == "POST":
        form = ClientRegistStatusForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"クライアント登録状況「{item.name}」を更新しました。")
            return redirect("master:client_regist_status_list")
    else:
        form = ClientRegistStatusForm(instance=item)
    context = {"form": form, "item": item, "title": f"クライアント登録状況編集"}
    return render(request, "master/client_regist_status_form.html", context)


@login_required
@permission_required("master.delete_clientregiststatus", raise_exception=True)
def client_regist_status_delete(request, pk):
    """クライアント登録状況削除"""
    item = get_object_or_404(ClientRegistStatus, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"クライアント登録状況「{item_name}」を削除しました。")
        return redirect("master:client_regist_status_list")
    context = {"item": item, "title": f"クライアント登録状況削除"}
    return render(request, "master/client_regist_status_delete.html", context)


@login_required
@permission_required("master.view_clientregiststatus", raise_exception=True)
def client_regist_status_change_history_list(request):
    """クライアント登録状況変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="ClientRegistStatus", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "クライアント登録状況変更履歴",
            "back_url_name": "master:client_regist_status_list",
            "model_name": "ClientRegistStatus",
        },
    )
