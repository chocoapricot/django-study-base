from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import (
    ClientRegistStatus,
    ClientContactType,
    ClientTag,
)
from .forms import (
    ClientRegistStatusForm,
    ClientContactTypeForm,
    ClientTagForm,
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

# クライアント連絡種別管理ビュー
@login_required
@permission_required("master.view_clientcontacttype", raise_exception=True)
def client_contact_type_list(request):
    """クライアント連絡種別一覧"""
    search_query = request.GET.get("search", "")
    items = ClientContactType.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="ClientContactType", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="ClientContactType", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:client_contact_type_change_history_list",
    }
    return render(request, "master/client_contact_type_list.html", context)


@login_required
@permission_required("master.add_clientcontacttype", raise_exception=True)
def client_contact_type_create(request):
    """クライアント連絡種別作成"""
    if request.method == "POST":
        form = ClientContactTypeForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"クライアント連絡種別「{item.name}」を作成しました。")
            return redirect("master:client_contact_type_list")
    else:
        form = ClientContactTypeForm()
    context = {"form": form, "title": "クライアント連絡種別作成"}
    return render(request, "master/client_contact_type_form.html", context)


@login_required
@permission_required("master.change_clientcontacttype", raise_exception=True)
def client_contact_type_update(request, pk):
    """クライアント連絡種別編集"""
    item = get_object_or_404(ClientContactType, pk=pk)
    if request.method == "POST":
        form = ClientContactTypeForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"クライアント連絡種別「{item.name}」を更新しました。")
            return redirect("master:client_contact_type_list")
    else:
        form = ClientContactTypeForm(instance=item)
    context = {"form": form, "item": item, "title": "クライアント連絡種別編集"}
    return render(request, "master/client_contact_type_form.html", context)


@login_required
@permission_required("master.delete_clientcontacttype", raise_exception=True)
def client_contact_type_delete(request, pk):
    """クライアント連絡種別削除"""
    item = get_object_or_404(ClientContactType, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"クライアント連絡種別「{item_name}」を削除しました。")
        return redirect("master:client_contact_type_list")
    context = {"item": item, "title": "クライアント連絡種別削除"}
    return render(request, "master/client_contact_type_delete.html", context)


@login_required
@permission_required("master.view_clientcontacttype", raise_exception=True)
def client_contact_type_change_history_list(request):
    """クライアント連絡種別変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="ClientContactType", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "クライアント連絡種別変更履歴",
            "back_url_name": "master:client_contact_type_list",
            "model_name": "ClientContactType",
        },
    )

# クライアントタグ管理ビュー
@login_required
@permission_required("master.view_clienttag", raise_exception=True)
def client_tag_list(request):
    """クライアントタグ一覧"""
    search_query = request.GET.get("search", "")
    items = ClientTag.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="ClientTag", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="ClientTag", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:client_tag_change_history_list",
    }
    return render(request, "master/client_tag_list.html", context)


@login_required
@permission_required("master.add_clienttag", raise_exception=True)
def client_tag_create(request):
    """クライアントタグ作成"""
    if request.method == "POST":
        form = ClientTagForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"クライアントタグ「{item.name}」を作成しました。")
            return redirect("master:client_tag_list")
    else:
        form = ClientTagForm()
    context = {"form": form, "title": "クライアントタグ作成"}
    return render(request, "master/client_tag_form.html", context)


@login_required
@permission_required("master.change_clienttag", raise_exception=True)
def client_tag_update(request, pk):
    """クライアントタグ編集"""
    item = get_object_or_404(ClientTag, pk=pk)
    if request.method == "POST":
        form = ClientTagForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"クライアントタグ「{item.name}」を更新しました。")
            return redirect("master:client_tag_list")
    else:
        form = ClientTagForm(instance=item)
    context = {"form": form, "item": item, "title": "クライアントタグ編集"}
    return render(request, "master/client_tag_form.html", context)


@login_required
@permission_required("master.delete_clienttag", raise_exception=True)
def client_tag_delete(request, pk):
    """クライアントタグ削除"""
    item = get_object_or_404(ClientTag, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"クライアントタグ「{item_name}」を削除しました。")
        return redirect("master:client_tag_list")
    context = {"item": item, "title": "クライアントタグ削除"}
    return render(request, "master/client_tag_delete.html", context)


@login_required
@permission_required("master.view_clienttag", raise_exception=True)
def client_tag_change_history_list(request):
    """クライアントタグ変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="ClientTag", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "クライアントタグ変更履歴",
            "back_url_name": "master:client_tag_list",
            "model_name": "ClientTag",
        },
    )
