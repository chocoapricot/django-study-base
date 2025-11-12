from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from datetime import datetime, timezone
import uuid
import os
import csv
from django.conf import settings
from django.db import transaction

from .models import (
    BillPayment,
    BillBank,
    Bank,
    BankBranch,
)
from .forms import (
    BillPaymentForm,
    BillBankForm,
    BankForm,
    BankBranchForm,
    CSVImportForm,
)
from apps.system.logs.models import AppLog
from apps.common.constants import Constants

# 支払条件マスタ
@login_required
@permission_required("master.view_billpayment", raise_exception=True)
def bill_payment_list(request):
    """支払条件一覧"""
    search_query = request.GET.get("search", "")

    bill_payments = BillPayment.objects.all()

    if search_query:
        bill_payments = bill_payments.filter(Q(name__icontains=search_query))

    bill_payments = bill_payments.order_by("display_order", "name")

    # 利用件数を事前に計算してアノテーション
    bill_payments = bill_payments.annotate(
        client_usage_count=Count("client", distinct=True),
        contract_usage_count=Count("clientcontract", distinct=True),
    )

    # ページネーション
    paginator = Paginator(bill_payments, 20)
    page = request.GET.get("page")
    bill_payments_page = paginator.get_page(page)

    # 変更履歴を取得（最新5件）
    change_logs = AppLog.objects.filter(
        model_name="BillPayment", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="BillPayment", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "bill_payments": bill_payments_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/bill_payment_list.html", context)


@login_required
@permission_required("master.add_billpayment", raise_exception=True)
def bill_payment_create(request):
    """支払条件作成"""
    if request.method == "POST":
        form = BillPaymentForm(request.POST)
        if form.is_valid():
            bill_payment = form.save()
            messages.success(
                request, f"支払条件「{bill_payment.name}」を作成しました。"
            )
            return redirect("master:bill_payment_list")
    else:
        form = BillPaymentForm()

    context = {
        "form": form,
        "title": "支払条件作成",
    }
    return render(request, "master/bill_payment_form.html", context)


@login_required
@permission_required("master.change_billpayment", raise_exception=True)
def bill_payment_update(request, pk):
    """支払条件編集"""
    bill_payment = get_object_or_404(BillPayment, pk=pk)

    if request.method == "POST":
        form = BillPaymentForm(request.POST, instance=bill_payment)
        if form.is_valid():
            bill_payment = form.save()
            messages.success(
                request, f"支払条件「{bill_payment.name}」を更新しました。"
            )
            return redirect("master:bill_payment_list")
    else:
        form = BillPaymentForm(instance=bill_payment)

    context = {
        "form": form,
        "bill_payment": bill_payment,
        "title": f"支払条件編集 - {bill_payment.name}",
    }
    return render(request, "master/bill_payment_form.html", context)


@login_required
@permission_required("master.delete_billpayment", raise_exception=True)
def bill_payment_delete(request, pk):
    """支払条件削除"""
    bill_payment = get_object_or_404(BillPayment, pk=pk)

    if request.method == "POST":
        bill_payment_name = bill_payment.name
        bill_payment.delete()
        messages.success(request, f"支払条件「{bill_payment_name}」を削除しました。")
        return redirect("master:bill_payment_list")

    context = {
        "bill_payment": bill_payment,
        "title": f"支払条件削除 - {bill_payment.name}",
    }
    return render(request, "master/bill_payment_delete.html", context)


# 会社銀行マスタ
@login_required
@permission_required("master.view_billbank", raise_exception=True)
def bill_bank_list(request):
    """会社銀行一覧"""
    search_query = request.GET.get("search", "")

    bill_banks = BillBank.objects.all()

    if search_query:
        bill_banks = bill_banks.filter(
            Q(account_holder__icontains=search_query)
            | Q(account_holder_kana__icontains=search_query)
        )

    bill_banks = bill_banks.order_by("display_order", "bank_code", "branch_code")

    # ページネーション
    paginator = Paginator(bill_banks, 20)
    page = request.GET.get("page")
    bill_banks_page = paginator.get_page(page)

    # 変更履歴を取得（最新5件）
    change_logs = AppLog.objects.filter(
        model_name="BillBank", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="BillBank", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "bill_banks": bill_banks_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/bill_bank_list.html", context)


@login_required
@permission_required("master.add_billbank", raise_exception=True)
def bill_bank_create(request):
    """会社銀行作成"""
    if request.method == "POST":
        form = BillBankForm(request.POST)
        if form.is_valid():
            bill_bank = form.save()
            messages.success(
                request,
                f"会社銀行「{bill_bank.bank_name} {bill_bank.branch_name}」を作成しました。",
            )
            return redirect("master:bill_bank_list")
    else:
        form = BillBankForm()

    context = {
        "form": form,
        "title": "会社銀行作成",
    }
    return render(request, "master/bill_bank_form.html", context)


@login_required
@permission_required("master.change_billbank", raise_exception=True)
def bill_bank_update(request, pk):
    """会社銀行編集"""
    bill_bank = get_object_or_404(BillBank, pk=pk)

    if request.method == "POST":
        form = BillBankForm(request.POST, instance=bill_bank)
        if form.is_valid():
            bill_bank = form.save()
            messages.success(
                request,
                f"会社銀行「{bill_bank.bank_name} {bill_bank.branch_name}」を更新しました。",
            )
            return redirect("master:bill_bank_list")
    else:
        form = BillBankForm(instance=bill_bank)

    context = {
        "form": form,
        "bill_bank": bill_bank,
        "title": f"会社銀行編集 - {bill_bank.bank_name} {bill_bank.branch_name}",
    }
    return render(request, "master/bill_bank_form.html", context)


@login_required
@permission_required("master.delete_billbank", raise_exception=True)
def bill_bank_delete(request, pk):
    """会社銀行削除"""
    bill_bank = get_object_or_404(BillBank, pk=pk)

    if request.method == "POST":
        bill_bank_name = f"{bill_bank.bank_name} {bill_bank.branch_name}"
        bill_bank.delete()
        messages.success(request, f"会社銀行「{bill_bank_name}」を削除しました。")
        return redirect("master:bill_bank_list")

    context = {
        "bill_bank": bill_bank,
        "title": f"会社銀行削除 - {bill_bank.bank_name} {bill_bank.branch_name}",
    }
    return render(request, "master/bill_bank_delete.html", context)


# 支払条件変更履歴
@login_required
@permission_required("master.view_billpayment", raise_exception=True)
def bill_payment_change_history_list(request):
    """支払条件変更履歴一覧"""
    # 支払条件の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="BillPayment", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "支払条件変更履歴",
            "back_url_name": "master:bill_payment_list",
            "model_name": "BillPayment",
        },
    )


# 会社銀行変更履歴
@login_required
@permission_required("master.view_billbank", raise_exception=True)
def bill_bank_change_history_list(request):
    """会社銀行変更履歴一覧"""
    # 会社銀行の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="BillBank", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "会社銀行変更履歴",
            "back_url_name": "master:bill_bank_list",
            "model_name": "BillBank",
        },
    )


@login_required
@permission_required("master.add_bank", raise_exception=True)
def bank_create(request):
    """銀行作成"""
    if request.method == "POST":
        form = BankForm(request.POST)
        if form.is_valid():
            bank = form.save()
            messages.success(request, f"銀行「{bank.name}」を作成しました。")
            # 銀行管理画面に戻る
            return redirect("master:bank_management")
    else:
        form = BankForm()

    context = {
        "form": form,
        "title": "銀行作成",
    }
    return render(request, "master/bank_form.html", context)


@login_required
@permission_required("master.change_bank", raise_exception=True)
def bank_update(request, pk):
    """銀行編集"""
    bank = get_object_or_404(Bank, pk=pk)

    if request.method == "POST":
        form = BankForm(request.POST, instance=bank)
        if form.is_valid():
            bank = form.save()
            messages.success(request, f"銀行「{bank.name}」を更新しました。")
            return redirect("master:bank_management")
    else:
        form = BankForm(instance=bank)

    context = {
        "form": form,
        "bank": bank,
        "title": f"銀行編集 - {bank.name}",
    }
    return render(request, "master/bank_form.html", context)


@login_required
@permission_required("master.delete_bank", raise_exception=True)
def bank_delete(request, pk):
    """銀行削除"""
    bank = get_object_or_404(Bank, pk=pk)

    if request.method == "POST":
        bank_name = bank.name
        bank.delete()
        messages.success(request, f"銀行「{bank_name}」を削除しました。")
        return redirect("master:bank_management")

    context = {
        "bank": bank,
        "title": f"銀行削除 - {bank.name}",
    }
    return render(request, "master/bank_delete.html", context)

@login_required
@permission_required("master.add_bankbranch", raise_exception=True)
def bank_branch_create(request):
    """銀行支店作成"""
    bank_id = request.GET.get("bank") or request.GET.get("bank_id")
    bank = None
    initial_data = {}

    if bank_id:
        try:
            bank = Bank.objects.get(pk=bank_id)
            initial_data["bank"] = bank
        except Bank.DoesNotExist:
            pass

    if request.method == "POST":
        form = BankBranchForm(request.POST)
        if form.is_valid():
            bank_branch = form.save()
            messages.success(
                request,
                f"銀行支店「{bank_branch.bank.name} {bank_branch.name}」を作成しました。",
            )
            # 銀行管理画面に戻る
            return redirect("master:bank_management")
    else:
        form = BankBranchForm(initial=initial_data)

    context = {
        "form": form,
        "bank": bank,
        "title": "銀行支店作成",
    }
    return render(request, "master/bank_branch_form.html", context)


@login_required
@permission_required("master.change_bankbranch", raise_exception=True)
def bank_branch_update(request, pk):
    """銀行支店編集"""
    bank_branch = get_object_or_404(BankBranch.objects.select_related("bank"), pk=pk)

    if request.method == "POST":
        form = BankBranchForm(request.POST, instance=bank_branch)
        if form.is_valid():
            bank_branch = form.save()
            messages.success(
                request,
                f"銀行支店「{bank_branch.bank.name} {bank_branch.name}」を更新しました。",
            )
            return redirect("master:bank_management")
    else:
        form = BankBranchForm(instance=bank_branch)

    context = {
        "form": form,
        "bank_branch": bank_branch,
        "bank": bank_branch.bank,
        "title": f"銀行支店編集 - {bank_branch.bank.name} {bank_branch.name}",
    }
    return render(request, "master/bank_branch_form.html", context)


@login_required
@permission_required("master.delete_bankbranch", raise_exception=True)
def bank_branch_delete(request, pk):
    """銀行支店削除"""
    bank_branch = get_object_or_404(BankBranch.objects.select_related("bank"), pk=pk)

    if request.method == "POST":
        bank_branch_name = f"{bank_branch.bank.name} {bank_branch.name}"
        bank_branch.delete()
        messages.success(request, f"銀行支店「{bank_branch_name}」を削除しました。")
        return redirect("master:bank_management")

    context = {
        "bank_branch": bank_branch,
        "title": f"銀行支店削除 - {bank_branch.bank.name} {bank_branch.name}",
    }
    return render(request, "master/bank_branch_delete.html", context)




# 銀行・銀行支店統合管理
@login_required
@permission_required("master.view_bank", raise_exception=True)
def bank_management(request):
    """銀行・銀行支店統合管理画面"""
    selected_bank_id = request.GET.get("bank_id")
    search_query = request.GET.get("search", "")

    # 銀行一覧を取得
    banks = Bank.objects.all()
    if search_query:
        banks = banks.filter(
            Q(name__icontains=search_query) | Q(bank_code__icontains=search_query)
        )
    banks = banks.order_by("bank_code", "name")

    # 選択された銀行の支店一覧を取得
    selected_bank = None
    bank_branches = BankBranch.objects.none()

    if selected_bank_id:
        try:
            selected_bank = Bank.objects.get(pk=selected_bank_id)
            bank_branches = BankBranch.objects.filter(bank=selected_bank).order_by(
                "branch_code", "name"
            )
        except Bank.DoesNotExist:
            pass

    # 変更履歴を取得（最新5件、銀行と銀行支店を統合）
    change_logs = AppLog.objects.filter(
        model_name__in=["Bank", "BankBranch"], action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name__in=["Bank", "BankBranch"], action__in=["create", "update", "delete"]
    ).count()

    context = {
        "banks": banks,
        "selected_bank": selected_bank,
        "bank_branches": bank_branches,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url": "master:bank_management_change_history_list",
    }
    return render(request, "master/bank_management.html", context)


@login_required
@permission_required("master.add_bank", raise_exception=True)
def bank_import(request):
    """銀行・支店CSV取込ページを表示"""
    form = CSVImportForm()
    context = {
        "form": form,
        "title": "銀行・支店CSV取込",
    }
    return render(request, "master/bank_import.html", context)


@login_required
@permission_required("master.add_bank", raise_exception=True)
@require_POST
def bank_import_upload(request):
    """CSVファイルをアップロードしてタスクIDを返す"""
    form = CSVImportForm(request.POST, request.FILES)
    if form.is_valid():
        csv_file = request.FILES["csv_file"]

        # 一時保存ディレクトリを作成
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)

        # ユニークなファイル名を生成
        task_id = str(uuid.uuid4())
        temp_file_path = os.path.join(temp_dir, f"{task_id}.csv")

        # ファイルを一時保存
        with open(temp_file_path, "wb+") as f:
            for chunk in csv_file.chunks():
                f.write(chunk)

        # キャッシュにタスク情報を保存
        cache.set(
            f"import_task_{task_id}",
            {
                "file_path": temp_file_path,
                "status": "uploaded",
                "progress": 0,
                "total": 0,
                "errors": [],
                "start_time": datetime.now(timezone.utc).isoformat(),
                "elapsed_time_seconds": 0,
                "estimated_time_remaining_seconds": 0,
            },
            timeout=3600,
        )

        return JsonResponse({"task_id": task_id})

    return JsonResponse(
        {"error": "CSVファイルのアップロードに失敗しました。"}, status=400
    )


@login_required
@permission_required("master.add_bank", raise_exception=True)
@require_POST
def bank_import_process(request, task_id):
    """CSVファイルのインポート処理を実行"""
    task_info = cache.get(f"import_task_{task_id}")
    if not task_info or task_info["status"] != "uploaded":
        return JsonResponse({"error": "無効なタスクIDです。"}, status=400)

    file_path = task_info["file_path"]
    start_time = datetime.fromisoformat(task_info["start_time"])

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            total_rows = len(rows)

        task_info["total"] = total_rows
        cache.set(f"import_task_{task_id}", task_info, timeout=3600)

        imported_count = 0
        errors = []

        for i, row in enumerate(rows):
            progress = i + 1
            try:
                with transaction.atomic():
                    bank_code = row[0]
                    branch_code = row[1]
                    name = row[3].strip()
                    record_type = row[4]

                    if record_type == Constants.BANK_RECORD_TYPE.BANK:  # 銀行
                        bank, created = Bank.objects.update_or_create(
                            bank_code=bank_code,
                            defaults={"name": name, "is_active": True},
                        )
                        imported_count += 1
                    elif record_type == Constants.BANK_RECORD_TYPE.BRANCH:  # 支店
                        try:
                            bank = Bank.objects.get(bank_code=bank_code)
                            branch, created = BankBranch.objects.update_or_create(
                                bank=bank,
                                branch_code=branch_code,
                                defaults={"name": name, "is_active": True},
                            )
                            imported_count += 1
                        except Bank.DoesNotExist:
                            errors.append(
                                f"{progress}行目: 銀行コード {bank_code} が見つかりません。"
                            )

            except Exception as e:
                errors.append(f"{progress}行目: {e}")

            # 進捗と時間を更新
            now = datetime.now(timezone.utc)
            elapsed_time = now - start_time

            if progress > 0 and total_rows > progress:
                estimated_time_remaining = (elapsed_time / progress) * (
                    total_rows - progress
                )
                task_info["estimated_time_remaining_seconds"] = int(
                    estimated_time_remaining.total_seconds()
                )
            else:
                task_info["estimated_time_remaining_seconds"] = 0

            task_info["progress"] = progress
            task_info["elapsed_time_seconds"] = int(elapsed_time.total_seconds())
            cache.set(f"import_task_{task_id}", task_info, timeout=3600)

        task_info["status"] = "completed"
        task_info["errors"] = errors
        task_info["imported_count"] = imported_count
        cache.set(f"import_task_{task_id}", task_info, timeout=3600)

        return JsonResponse(
            {"status": "completed", "imported_count": imported_count, "errors": errors}
        )

    except Exception as e:
        task_info["status"] = "failed"
        task_info["errors"] = [f"処理中に予期せぬエラーが発生しました: {e}"]
        cache.set(f"import_task_{task_id}", task_info, timeout=3600)
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)


@login_required
@permission_required("master.add_bank", raise_exception=True)
def bank_import_progress(request, task_id):
    """インポートの進捗状況を返す"""
    task_info = cache.get(f"import_task_{task_id}")
    if not task_info:
        return JsonResponse({"error": "無効なタスクIDです。"}, status=404)

    return JsonResponse(task_info)


# 銀行・銀行支店統合変更履歴
@login_required
@permission_required("master.view_bank", raise_exception=True)
def bank_management_change_history_list(request):
    """銀行・銀行支店統合変更履歴一覧"""
    # 銀行・銀行支店の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name__in=["Bank", "BankBranch"], action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "銀行・銀行支店変更履歴",
            "back_url_name": "master:bank_management",
            "model_name": "Bank/BankBranch",
        },
    )
