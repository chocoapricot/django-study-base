from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.apps import apps
from .models import (
    Qualification,
    Skill,
    BillPayment,
    BillBank,
    Bank,
    BankBranch,
    Information,
    InformationFile,
    JobCategory,
    StaffAgreement,
    MailTemplate,
    ContractPattern,
    ContractTerms,
)
from .forms import (
    QualificationForm,
    QualificationCategoryForm,
    SkillForm,
    SkillCategoryForm,
    BillPaymentForm,
    BillBankForm,
    BankForm,
    BankBranchForm,
    InformationForm,
    CSVImportForm,
    JobCategoryForm,
    StaffAgreementForm,
    MailTemplateForm,
    ContractPatternForm,
    BaseContractTermsFormSet,
)
from apps.company.models import Company
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from .resources import AgreedStaffResource
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView
import uuid
import os
from django.conf import settings
from datetime import datetime, timezone


# マスタ設定データ
MASTER_CONFIGS = [
    {
        "category": "スタッフ",
        "name": "資格管理",
        "description": "資格・免許・認定等の管理",
        "model": "master.Qualification",
        "url_name": "master:qualification_list",
        "permission": "master.view_qualification",
    },
    {
        "category": "スタッフ",
        "name": "技能管理",
        "description": "スキル・技術・能力等の管理",
        "model": "master.Skill",
        "url_name": "master:skill_list",
        "permission": "master.view_skill",
    },
    {
        "category": "スタッフ",
        "name": "同意文言管理",
        "description": "スタッフ登録時の同意文言を管理",
        "model": "master.StaffAgreement",
        "url_name": "master:staff_agreement_list",
        "permission": "master.view_staffagreement",
    },
    {
        "category": "契約",
        "name": "職種管理",
        "description": "職種情報の管理",
        "model": "master.JobCategory",
        "url_name": "master:job_category_list",
        "permission": "master.view_jobcategory",
    },
    {
        "category": "契約",
        "name": "契約パターン管理",
        "description": "契約パターンと文言の管理",
        "model": "master.ContractPattern",
        "url_name": "master:contract_pattern_list",
        "permission": "master.view_contractpattern",
    },
    {
        "category": "請求",
        "name": "支払条件管理",
        "description": "請求・支払条件の管理",
        "model": "master.BillPayment",
        "url_name": "master:bill_payment_list",
        "permission": "master.view_billpayment",
    },
    {
        "category": "請求",
        "name": "会社銀行管理",
        "description": "会社銀行口座の管理",
        "model": "master.BillBank",
        "url_name": "master:bill_bank_list",
        "permission": "master.view_billbank",
    },
    {
        "category": "請求",
        "name": "銀行・銀行支店管理",
        "description": "銀行と銀行支店の統合管理",
        "model": "master.Bank",
        "url_name": "master:bank_management",
        "permission": "master.view_bank",
    },
    {
        "category": "その他",
        "name": "お知らせ管理",
        "description": "会社・スタッフ・クライアントへのお知らせを管理",
        "model": "master.Information",
        "url_name": "master:information_list",
        "permission": "master.view_information",
    },
    {
        "category": "その他",
        "name": "メールテンプレート管理",
        "description": "各種メールテンプレートを管理します",
        "model": "master.MailTemplate",
        "url_name": "master:mail_template_list",
        "permission": "master.view_mailtemplate",
    },
]


def get_category_count(model_class):
    """カテゴリ数を取得"""
    try:
        if hasattr(model_class, "level"):
            return model_class.objects.filter(level=1, is_active=True).count()
        return 0
    except Exception:
        return 0


def get_data_count(model_class):
    """データ数を取得"""
    try:
        if hasattr(model_class, "level"):
            return model_class.objects.filter(level=2, is_active=True).count()

        # is_active属性があるモデルの場合
        if hasattr(model_class, "is_active"):
            return model_class.objects.filter(is_active=True).count()

        # is_active属性がないモデル（Informationなど）の場合
        return model_class.objects.count()
    except Exception:
        return 0


@login_required
@permission_required("master.view_staffagreement", raise_exception=True)
def agreed_staff_export(request, pk):
    """同意済みスタッフデータのエクスポート（CSV/Excel）"""
    agreement = get_object_or_404(StaffAgreement, pk=pk)

    # 同意したスタッフの接続情報を取得
    agreed_connections = ConnectStaffAgree.objects.filter(
        staff_agreement=agreement, is_agreed=True
    )

    # 関連するスタッフのメールアドレスリストを取得
    staff_emails = agreed_connections.values_list("email", flat=True)

    # メールアドレスに紐づくスタッフ情報を取得
    staff_qs = Staff.objects.filter(email__in=staff_emails)

    # フィルタリング
    query = request.GET.get("q", "")
    if query:
        staff_qs = staff_qs.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        )

    # フィルタリング後のメールアドレスリストで再度絞り込み
    filtered_emails = staff_qs.values_list("email", flat=True)
    agreed_connections = agreed_connections.filter(email__in=filtered_emails)

    # 表示用にスタッフ情報と同意日時を結合
    staff_dict = {staff.email: staff for staff in staff_qs}
    agreed_staff_list = []
    for conn in agreed_connections:
        staff = staff_dict.get(conn.email)
        if staff:
            agreed_staff_list.append(
                {
                    "staff": staff,
                    "agreed_at": conn.created_at,
                }
            )

    # ソート
    sort_by = request.GET.get("sort", "agreed_at")
    sort_dir = request.GET.get("dir", "desc")
    reverse_sort = sort_dir == "desc"

    if sort_by == "staff__name":
        agreed_staff_list.sort(
            key=lambda x: (x["staff"].name_last or "", x["staff"].name_first or ""),
            reverse=reverse_sort,
        )
    elif sort_by == "staff__email":
        agreed_staff_list.sort(key=lambda x: x["staff"].email or "", reverse=reverse_sort)
    else:  # agreed_at
        agreed_staff_list.sort(key=lambda x: x["agreed_at"], reverse=reverse_sort)

    # リソースを使ってエクスポート
    resource = AgreedStaffResource()
    dataset = resource.export(agreed_staff_list)

    # ファイル名を生成（日時付き）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    format_type = request.GET.get('format', 'csv')

    if format_type == 'excel':
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="agreed_staff_{pk}_{timestamp}.xlsx"'
    else:  # CSV
        # BOMを追加してExcelで正しく表示されるようにする
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="agreed_staff_{pk}_{timestamp}.csv"'

    return response


@login_required
@permission_required("master.view_qualification", raise_exception=True)
def master_index_list(request):
    """マスタ一覧画面を表示"""
    masters_by_category = {}

    for config in MASTER_CONFIGS:
        # 権限チェック
        if not request.user.has_perm(config["permission"]):
            continue

        try:
            # モデルクラスを動的に取得
            model_class = apps.get_model(config["model"])

            # データ件数を集計
            category_count = get_category_count(model_class)
            data_count = get_data_count(model_class)
            total_count = category_count + data_count

            # URLを生成
            try:
                url = reverse(config["url_name"])
            except Exception:
                url = "#"  # URLが生成できない場合のフォールバック

            # マスタ情報を構築
            master_info = {
                "name": config["name"],
                "description": config["description"],
                "category_count": category_count,
                "data_count": data_count,
                "total_count": total_count,
                "url": url,
            }

            # 分類別に整理
            category = config["category"]
            if category not in masters_by_category:
                masters_by_category[category] = []
            masters_by_category[category].append(master_info)

        except Exception:
            # モデルクラスが存在しない場合などのエラーハンドリング
            continue

    context = {
        "masters_by_category": masters_by_category,
    }
    return render(request, "master/master_index_list.html", context)


# 資格管理ビュー
@login_required
@permission_required("master.view_qualification", raise_exception=True)
def qualification_list(request):
    """資格一覧（階層表示）"""
    from apps.system.logs.models import AppLog

    # 検索機能
    search_query = request.GET.get("q", "")

    # カテゴリフィルタ（親カテゴリ）
    category_filter = request.GET.get("category", "")

    # フィルタ条件に基づいてカテゴリと資格を取得
    categories_query = Qualification.objects.filter(level=1)
    qualifications_query = Qualification.objects.filter(level=2).select_related(
        "parent"
    )

    # 検索条件を適用
    if search_query:
        categories_query = categories_query.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
        qualifications_query = qualifications_query.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(parent__name__icontains=search_query)
        )

    # カテゴリフィルタを適用
    if category_filter:
        categories_query = categories_query.filter(pk=category_filter)
        qualifications_query = qualifications_query.filter(parent_id=category_filter)

    # シンプルな一覧用データを整理
    items = []

    for category in categories_query.filter(is_active=True).order_by(
        "display_order", "name"
    ):
        # カテゴリを追加
        items.append(category)

        # カテゴリに属する資格を追加
        category_qualifications = qualifications_query.filter(
            parent=category, is_active=True
        ).order_by("display_order", "name")
        items.extend(category_qualifications)

    # フィルタ用のカテゴリ一覧
    all_categories = Qualification.get_categories()

    # 検索機能
    search_query = request.GET.get("q", "")

    # カテゴリフィルタ（親カテゴリ）
    category_filter = request.GET.get("category", "")

    # フィルタ条件に基づいてカテゴリと資格を取得
    categories_query = Qualification.objects.filter(level=1)
    qualifications_query = Qualification.objects.filter(level=2).select_related(
        "parent"
    )

    # 検索条件を適用
    if search_query:
        categories_query = categories_query.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
        qualifications_query = qualifications_query.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(parent__name__icontains=search_query)
        )

    # カテゴリフィルタを適用
    if category_filter:
        categories_query = categories_query.filter(pk=category_filter)
        qualifications_query = qualifications_query.filter(parent_id=category_filter)

    # シンプルな一覧用データを整理
    items = []

    for category in categories_query.filter(is_active=True).order_by(
        "display_order", "name"
    ):
        # カテゴリを追加
        items.append(category)

        # カテゴリに属する資格を追加
        category_qualifications = qualifications_query.filter(
            parent=category, is_active=True
        ).order_by("display_order", "name")
        items.extend(category_qualifications)

    # フィルタ用のカテゴリ一覧
    all_categories = Qualification.get_categories()

    # 変更履歴（最新5件）
    change_logs = AppLog.objects.filter(
        model_name="Qualification", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name="Qualification", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "items": items,
        "search_query": search_query,
        "category_filter": category_filter,
        "categories": all_categories,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }

    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name="Qualification", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "items": items,
        "search_query": search_query,
        "category_filter": category_filter,
        "categories": all_categories,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/qualification_list.html", context)


@login_required
@permission_required("master.view_qualification", raise_exception=True)
def qualification_detail(request, pk):
    """資格詳細"""
    qualification = get_object_or_404(Qualification, pk=pk)
    context = {
        "qualification": qualification,
    }
    return render(request, "master/qualification_detail.html", context)


@login_required
@permission_required("master.add_qualification", raise_exception=True)
def qualification_category_create(request):
    """資格カテゴリ作成"""
    if request.method == "POST":
        form = QualificationCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"カテゴリ「{category.name}」を作成しました。")
            return redirect("master:qualification_detail", pk=category.pk)
    else:
        form = QualificationCategoryForm()

    context = {
        "form": form,
        "title": "カテゴリ作成",
    }
    return render(request, "master/qualification_category_form.html", context)


@login_required
@permission_required("master.add_qualification", raise_exception=True)
def qualification_create(request):
    """資格作成"""
    if request.method == "POST":
        form = QualificationForm(request.POST)
        if form.is_valid():
            qualification = form.save()
            messages.success(request, f"資格「{qualification.name}」を作成しました。")
            return redirect("master:qualification_detail", pk=qualification.pk)
    else:
        form = QualificationForm()

    context = {
        "form": form,
        "title": "資格作成",
    }
    return render(request, "master/qualification_form.html", context)


@login_required
@permission_required("master.change_qualification", raise_exception=True)
def qualification_update(request, pk):
    """資格更新"""
    qualification = get_object_or_404(Qualification, pk=pk)

    # カテゴリか資格かによってフォームを切り替え
    if qualification.is_category:
        form_class = QualificationCategoryForm
        template_name = "master/qualification_category_form.html"
        title = "カテゴリ編集"
    else:
        form_class = QualificationForm
        template_name = "master/qualification_form.html"
        title = "資格編集"

    if request.method == "POST":
        form = form_class(request.POST, instance=qualification)
        if form.is_valid():
            qualification = form.save()
            messages.success(request, f"「{qualification.name}」を更新しました。")
            return redirect("master:qualification_detail", pk=qualification.pk)
    else:
        form = form_class(instance=qualification)

    context = {
        "form": form,
        "qualification": qualification,
        "title": title,
    }
    return render(request, template_name, context)


@login_required
@permission_required("master.delete_qualification", raise_exception=True)
def qualification_delete(request, pk):
    """資格削除"""
    qualification = get_object_or_404(Qualification, pk=pk)

    if request.method == "POST":
        qualification_name = qualification.name
        qualification.delete()
        messages.success(request, f"資格「{qualification_name}」を削除しました。")
        return redirect("master:qualification_list")

    context = {
        "qualification": qualification,
    }
    return render(request, "master/qualification_delete.html", context)


# 技能管理ビュー
@login_required
@permission_required("master.view_skill", raise_exception=True)
def skill_list(request):
    """技能一覧（階層表示）"""
    from apps.system.logs.models import AppLog

    # 検索機能
    search_query = request.GET.get("q", "")

    # カテゴリフィルタ（親カテゴリ）
    category_filter = request.GET.get("category", "")

    # フィルタ条件に基づいてカテゴリと技能を取得
    categories_query = Skill.objects.filter(level=1)
    skills_query = Skill.objects.filter(level=2).select_related("parent")

    # 検索条件を適用
    if search_query:
        categories_query = categories_query.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
        skills_query = skills_query.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(parent__name__icontains=search_query)
        )

    # カテゴリフィルタを適用
    if category_filter:
        categories_query = categories_query.filter(pk=category_filter)
        skills_query = skills_query.filter(parent_id=category_filter)

    # シンプルな一覧用データを整理
    items = []

    for category in categories_query.filter(is_active=True).order_by(
        "display_order", "name"
    ):
        # カテゴリを追加
        items.append(category)

        # カテゴリに属する技能を追加
        category_skills = skills_query.filter(parent=category, is_active=True).order_by(
            "display_order", "name"
        )
        items.extend(category_skills)

    # フィルタ用のカテゴリ一覧
    all_categories = Skill.get_categories()

    # 変更履歴（最新5件）
    change_logs = AppLog.objects.filter(
        model_name="Skill", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name="Skill", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "items": items,
        "search_query": search_query,
        "category_filter": category_filter,
        "categories": all_categories,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/skill_list.html", context)


@login_required
@permission_required("master.view_skill", raise_exception=True)
def skill_detail(request, pk):
    """技能詳細"""
    skill = get_object_or_404(Skill, pk=pk)
    context = {
        "skill": skill,
    }
    return render(request, "master/skill_detail.html", context)


@login_required
@permission_required("master.add_skill", raise_exception=True)
def skill_category_create(request):
    """技能カテゴリ作成"""
    if request.method == "POST":
        form = SkillCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"カテゴリ「{category.name}」を作成しました。")
            return redirect("master:skill_detail", pk=category.pk)
    else:
        form = SkillCategoryForm()

    context = {
        "form": form,
        "title": "カテゴリ作成",
    }
    return render(request, "master/skill_category_form.html", context)


@login_required
@permission_required("master.add_skill", raise_exception=True)
def skill_create(request):
    """技能作成"""
    if request.method == "POST":
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save()
            messages.success(request, f"技能「{skill.name}」を作成しました。")
            return redirect("master:skill_detail", pk=skill.pk)
    else:
        form = SkillForm()

    context = {
        "form": form,
        "title": "技能作成",
    }
    return render(request, "master/skill_form.html", context)


@login_required
@permission_required("master.change_skill", raise_exception=True)
def skill_update(request, pk):
    """技能更新"""
    skill = get_object_or_404(Skill, pk=pk)

    # カテゴリか技能かによってフォームを切り替え
    if skill.is_category:
        form_class = SkillCategoryForm
        template_name = "master/skill_category_form.html"
        title = "カテゴリ編集"
    else:
        form_class = SkillForm
        template_name = "master/skill_form.html"
        title = "技能編集"

    if request.method == "POST":
        form = form_class(request.POST, instance=skill)
        if form.is_valid():
            skill = form.save()
            messages.success(request, f"「{skill.name}」を更新しました。")
            return redirect("master:skill_detail", pk=skill.pk)
    else:
        form = form_class(instance=skill)

    context = {
        "form": form,
        "skill": skill,
        "title": title,
    }
    return render(request, template_name, context)


@login_required
@permission_required("master.delete_skill", raise_exception=True)
def skill_delete(request, pk):
    """技能削除"""
    skill = get_object_or_404(Skill, pk=pk)

    if request.method == "POST":
        skill_name = skill.name
        skill.delete()
        messages.success(request, f"技能「{skill_name}」を削除しました。")
        return redirect("master:skill_list")

    context = {
        "skill": skill,
    }
    return render(request, "master/skill_delete.html", context)


# 職種管理ビュー
@login_required
@permission_required("master.view_jobcategory", raise_exception=True)
def job_category_list(request):
    """職種一覧"""
    search_query = request.GET.get("search", "")

    job_categories = JobCategory.objects.all()

    if search_query:
        job_categories = job_categories.filter(Q(name__icontains=search_query))

    job_categories = job_categories.order_by("display_order", "name")

    paginator = Paginator(job_categories, 20)
    page = request.GET.get("page")
    job_categories_page = paginator.get_page(page)

    from apps.system.logs.models import AppLog

    change_logs = AppLog.objects.filter(
        model_name="JobCategory", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="JobCategory", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "job_categories": job_categories_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/job_category_list.html", context)


@login_required
@permission_required("master.add_jobcategory", raise_exception=True)
def job_category_create(request):
    """職種作成"""
    if request.method == "POST":
        form = JobCategoryForm(request.POST)
        if form.is_valid():
            job_category = form.save()
            messages.success(request, f"職種「{job_category.name}」を作成しました。")
            return redirect("master:job_category_list")
    else:
        form = JobCategoryForm()

    context = {
        "form": form,
        "title": "職種作成",
    }
    return render(request, "master/job_category_form.html", context)


@login_required
@permission_required("master.change_jobcategory", raise_exception=True)
def job_category_update(request, pk):
    """職種編集"""
    job_category = get_object_or_404(JobCategory, pk=pk)

    if request.method == "POST":
        form = JobCategoryForm(request.POST, instance=job_category)
        if form.is_valid():
            job_category = form.save()
            messages.success(request, f"職種「{job_category.name}」を更新しました。")
            return redirect("master:job_category_list")
    else:
        form = JobCategoryForm(instance=job_category)

    context = {
        "form": form,
        "job_category": job_category,
        "title": f"職種編集 - {job_category.name}",
    }
    return render(request, "master/job_category_form.html", context)


@login_required
@permission_required("master.delete_jobcategory", raise_exception=True)
def job_category_delete(request, pk):
    """職種削除"""
    job_category = get_object_or_404(JobCategory, pk=pk)

    if request.method == "POST":
        job_category_name = job_category.name
        job_category.delete()
        messages.success(request, f"職種「{job_category_name}」を削除しました。")
        return redirect("master:job_category_list")

    context = {
        "job_category": job_category,
        "title": f"職種削除 - {job_category.name}",
    }
    return render(request, "master/job_category_delete.html", context)


# 変更履歴ビュー
@login_required
@permission_required("master.view_qualification", raise_exception=True)
def qualification_change_history_list(request):
    """資格マスタ変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

    # 資格マスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="Qualification", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "資格マスタ変更履歴",
            "list_url": "master:qualification_list",
            "model_name": "Qualification",
        },
    )


# メールテンプレート管理ビュー
@login_required
@permission_required("master.view_mailtemplate", raise_exception=True)
def mail_template_list(request):
    """メールテンプレート一覧"""
    from apps.system.logs.models import AppLog
    search_query = request.GET.get("search", "")

    mail_templates = MailTemplate.objects.all()

    if search_query:
        mail_templates = mail_templates.filter(
            Q(name__icontains=search_query)
            | Q(template_key__icontains=search_query)
            | Q(subject__icontains=search_query)
            | Q(body__icontains=search_query)
        )

    mail_templates = mail_templates.order_by("template_key")

    paginator = Paginator(mail_templates, 20)
    page = request.GET.get("page")
    mail_templates_page = paginator.get_page(page)

    change_logs = AppLog.objects.filter(
        model_name="MailTemplate", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="MailTemplate", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "mail_templates": mail_templates_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:mail_template_change_history_list",
    }
    return render(request, "master/mail_template_list.html", context)


@login_required
@permission_required("master.view_mailtemplate", raise_exception=True)
def mail_template_detail(request, pk):
    """メールテンプレート詳細"""
    mail_template = get_object_or_404(MailTemplate, pk=pk)
    context = {"mail_template": mail_template}
    return render(request, "master/mail_template_detail.html", context)


@login_required
@permission_required("master.change_mailtemplate", raise_exception=True)
def mail_template_update(request, pk):
    """メールテンプレート編集"""
    mail_template = get_object_or_404(MailTemplate, pk=pk)

    if request.method == "POST":
        form = MailTemplateForm(request.POST, instance=mail_template)
        if form.is_valid():
            mail_template = form.save()
            messages.success(
                request, f"メールテンプレート「{mail_template.name}」を更新しました。"
            )
            return redirect("master:mail_template_list")
    else:
        form = MailTemplateForm(instance=mail_template)

    context = {
        "form": form,
        "mail_template": mail_template,
        "title": f"メールテンプレート編集 - {mail_template.name}",
    }
    return render(request, "master/mail_template_form.html", context)


@login_required
@permission_required("master.view_mailtemplate", raise_exception=True)
def mail_template_change_history_list(request):
    """メールテンプレート変更履歴一覧"""
    from apps.system.logs.models import AppLog

    logs = AppLog.objects.filter(
        model_name="MailTemplate", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "メールテンプレート変更履歴",
            "list_url": "master:mail_template_list",
            "model_name": "MailTemplate",
        },
    )


@login_required
@permission_required("master.view_skill", raise_exception=True)
def skill_change_history_list(request):
    """技能マスタ変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

    # 技能マスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="Skill", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "技能マスタ変更履歴",
            "list_url": "master:skill_list",
            "model_name": "Skill",
        },
    )


@login_required
@permission_required("master.view_jobcategory", raise_exception=True)
def job_category_change_history_list(request):
    """職種マスタ変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

    # 職種マスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="JobCategory", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "職種マスタ変更履歴",
            "list_url": "master:job_category_list",
            "model_name": "JobCategory",
        },
    )


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
    from django.db.models import Count, Q as DjangoQ
    from apps.client.models import Client
    from apps.contract.models import ClientContract

    bill_payments = bill_payments.annotate(
        client_usage_count=Count("client", distinct=True),
        contract_usage_count=Count("clientcontract", distinct=True),
    )

    # ページネーション
    paginator = Paginator(bill_payments, 20)
    page = request.GET.get("page")
    bill_payments_page = paginator.get_page(page)

    # 変更履歴を取得（最新5件）
    from apps.system.logs.models import AppLog

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
    from apps.system.logs.models import AppLog

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
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

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
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "支払条件変更履歴",
            "list_url": "master:bill_payment_list",
            "model_name": "BillPayment",
        },
    )


# 会社銀行変更履歴
@login_required
@permission_required("master.view_billbank", raise_exception=True)
def bill_bank_change_history_list(request):
    """会社銀行変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

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
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "会社銀行変更履歴",
            "list_url": "master:bill_bank_list",
            "model_name": "BillBank",
        },
    )


# 銀行マスタ
@login_required
@permission_required("master.view_bank", raise_exception=True)
def bank_list(request):
    """銀行一覧"""
    search_query = request.GET.get("search", "")

    banks = Bank.objects.all()

    if search_query:
        banks = banks.filter(
            Q(name__icontains=search_query)
            | Q(bank_code__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    banks = banks.order_by("name")

    # ページネーション
    paginator = Paginator(banks, 20)
    page = request.GET.get("page")
    banks_page = paginator.get_page(page)

    # 変更履歴を取得（最新5件）
    from apps.system.logs.models import AppLog

    change_logs = AppLog.objects.filter(
        model_name="Bank", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="Bank", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "banks": banks_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/bank_list.html", context)


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


# 銀行変更履歴
@login_required
@permission_required("master.view_bank", raise_exception=True)
def bank_change_history_list(request):
    """銀行変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

    # 銀行の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="Bank", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "銀行変更履歴",
            "list_url": "master:bank_management",
            "model_name": "Bank",
        },
    )


# 銀行支店マスタ
@login_required
@permission_required("master.view_bankbranch", raise_exception=True)
def bank_branch_list(request):
    """銀行支店一覧"""
    search_query = request.GET.get("search", "")
    bank_filter = request.GET.get("bank", "")

    bank_branches = BankBranch.objects.select_related("bank")

    if search_query:
        bank_branches = bank_branches.filter(
            Q(name__icontains=search_query)
            | Q(branch_code__icontains=search_query)
            | Q(bank__name__icontains=search_query)
        )

    if bank_filter:
        bank_branches = bank_branches.filter(bank_id=bank_filter)

    bank_branches = bank_branches.order_by(
        "bank__bank_code", "bank__name", "branch_code", "name"
    )

    # ページネーション
    paginator = Paginator(bank_branches, 20)
    page = request.GET.get("page")
    bank_branches_page = paginator.get_page(page)

    # フィルタ用の銀行一覧
    banks = Bank.objects.filter(is_active=True).order_by("bank_code", "name")

    # 変更履歴を取得（最新5件）
    from apps.system.logs.models import AppLog

    change_logs = AppLog.objects.filter(
        model_name="BankBranch", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="BankBranch", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "bank_branches": bank_branches_page,
        "search_query": search_query,
        "bank_filter": bank_filter,
        "banks": banks,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/bank_branch_list.html", context)


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


# 銀行支店変更履歴
@login_required
@permission_required("master.view_bankbranch", raise_exception=True)
def bank_branch_change_history_list(request):
    """銀行支店変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

    # 銀行支店の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="BankBranch", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "銀行支店変更履歴",
            "list_url": "master:bank_management",
            "model_name": "BankBranch",
        },
    )


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
    from apps.system.logs.models import AppLog

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


import csv
import io
from django.db import transaction


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

                    if record_type == "1":  # 銀行
                        bank, created = Bank.objects.update_or_create(
                            bank_code=bank_code,
                            defaults={"name": name, "is_active": True},
                        )
                        imported_count += 1
                    elif record_type == "2":  # 支店
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
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator

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
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "銀行・銀行支店変更履歴",
            "list_url": "master:bank_management",
            "model_name": "Bank/BankBranch",
        },
    )


# お知らせ管理ビュー
@login_required
@permission_required("master.view_information", raise_exception=True)
def information_list(request):
    """お知らせ一覧"""
    from apps.system.logs.models import AppLog

    search_query = request.GET.get("search", "")

    information_list = Information.objects.all()

    if search_query:
        information_list = information_list.filter(
            Q(subject__icontains=search_query) | Q(content__icontains=search_query)
        )

    information_list = information_list.order_by("-start_date")

    paginator = Paginator(information_list, 20)
    page = request.GET.get("page")
    information_page = paginator.get_page(page)

    # 変更履歴（最新5件）
    change_logs = AppLog.objects.filter(
        model_name="Information", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name="Information", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "information_list": information_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
    }
    return render(request, "master/information_list.html", context)


@login_required
@permission_required("master.view_information", raise_exception=True)
def information_detail(request, pk):
    """お知らせ詳細"""
    information = get_object_or_404(Information, pk=pk)
    context = {
        "information": information,
    }
    return render(request, "master/information_detail.html", context)


@login_required
@permission_required("master.add_information", raise_exception=True)
def information_create(request):
    """お知らせ作成"""
    company = Company.objects.first()
    if request.method == "POST":
        form = InformationForm(request.POST, request.FILES)
        if form.is_valid():
            information = form.save(commit=False)
            if company:
                information.corporation_number = company.corporate_number
            information.save()

            # Handle file uploads
            for f in request.FILES.getlist("attachments"):
                InformationFile.objects.create(information=information, file=f)

            messages.success(
                request, f"お知らせ「{information.subject}」を作成しました。"
            )
            return redirect("master:information_list")
    else:
        form = InformationForm()

    context = {
        "form": form,
        "title": "お知らせ作成",
    }
    return render(request, "master/information_form.html", context)


@login_required
@permission_required("master.change_information", raise_exception=True)
def information_update(request, pk):
    """お知らせ編集"""
    information = get_object_or_404(Information, pk=pk)

    if request.method == "POST":
        form = InformationForm(request.POST, request.FILES, instance=information)
        if form.is_valid():
            # Handle file deletion
            delete_ids = request.POST.getlist("delete_attachments")
            if delete_ids:
                files_to_delete = InformationFile.objects.filter(
                    pk__in=delete_ids, information=information
                )
                for f in files_to_delete:
                    f.delete()

            information = form.save()

            # Handle new file uploads
            for f in request.FILES.getlist("attachments"):
                InformationFile.objects.create(information=information, file=f)

            messages.success(
                request, f"お知らせ「{information.subject}」を更新しました。"
            )
            return redirect("master:information_list")
    else:
        form = InformationForm(instance=information)

    context = {
        "form": form,
        "information": information,
        "title": f"お知らせ編集 - {information.subject}",
    }
    return render(request, "master/information_form.html", context)


@login_required
@permission_required("master.delete_information", raise_exception=True)
def information_delete(request, pk):
    """お知らせ削除"""
    information = get_object_or_404(Information, pk=pk)

    if request.method == "POST":
        information_subject = information.subject
        information.delete()
        messages.success(request, f"お知らせ「{information_subject}」を削除しました。")
        return redirect("master:information_list")

    context = {
        "information": information,
        "title": f"お知らせ削除 - {information.subject}",
    }
    return render(request, "master/information_confirm_delete.html", context)


@login_required
@permission_required("master.view_information", raise_exception=True)
def information_all_change_history_list(request):
    """お知らせマスタ全体の変更履歴一覧"""

    # お知らせマスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="Information", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    # ページネーション
    paginator = Paginator(logs, 20)  # 1ページあたり20件
    page_number = request.GET.get("page")
    logs = paginator.get_page(page_number)

    context = {
        "logs": logs,
        "model_name": "Information",
        "title": "お知らせマスタ変更履歴",
        "list_url": "master:information_list",
    }
    return render(request, "master/master_change_history_list.html", context)


# スタッフ同意文言管理
@login_required
@permission_required("master.view_staffagreement", raise_exception=True)
def staff_agreement_list(request):
    """スタッフ同意文言一覧"""
    from apps.system.logs.models import AppLog

    search_query = request.GET.get("search", "")
    agreements = StaffAgreement.objects.all()
    if search_query:
        agreements = agreements.filter(name__icontains=search_query)

    agreements = agreements.order_by("display_order", "name")

    paginator = Paginator(agreements, 20)
    page = request.GET.get("page")
    agreements_page = paginator.get_page(page)

    change_logs = AppLog.objects.filter(
        model_name="StaffAgreement", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="StaffAgreement", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "agreements": agreements_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:staff_agreement_change_history_list",
    }
    return render(request, "master/staffagreement_list.html", context)


from apps.staff.models import Staff
from apps.connect.models import ConnectStaffAgree


@login_required
@permission_required("master.view_staffagreement", raise_exception=True)
def staff_agreement_detail(request, pk):
    """スタッフ同意文言詳細"""
    agreement = get_object_or_404(StaffAgreement, pk=pk)

    # 同意したスタッフの接続情報を取得
    agreed_connections = ConnectStaffAgree.objects.filter(
        staff_agreement=agreement, is_agreed=True
    )

    # 関連するスタッフのメールアドレスリストを取得
    staff_emails = agreed_connections.values_list("email", flat=True)

    # メールアドレスに紐づくスタッフ情報を取得
    staff_qs = Staff.objects.filter(email__in=staff_emails)

    # フィルタリング
    query = request.GET.get("q", "")
    if query:
        staff_qs = staff_qs.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        )

    # フィルタリング後のメールアドレスリストで再度絞り込み
    filtered_emails = staff_qs.values_list("email", flat=True)
    agreed_connections = agreed_connections.filter(email__in=filtered_emails)

    # 表示用にスタッフ情報と同意日時を結合
    staff_dict = {staff.email: staff for staff in staff_qs}
    agreed_staff_list = []
    for conn in agreed_connections:
        staff = staff_dict.get(conn.email)
        if staff:
            agreed_staff_list.append(
                {
                    "staff": staff,
                    "agreed_at": conn.created_at,
                }
            )

    # ソート
    sort_by = request.GET.get("sort", "agreed_at")
    sort_dir = request.GET.get("dir", "desc")

    reverse_sort = sort_dir == "desc"

    if sort_by == "staff__name":
        agreed_staff_list.sort(
            key=lambda x: (x["staff"].name_last or "", x["staff"].name_first or ""),
            reverse=reverse_sort,
        )
    elif sort_by == "staff__email":
        agreed_staff_list.sort(
            key=lambda x: x["staff"].email or "", reverse=reverse_sort
        )
    else:  # agreed_at
        agreed_staff_list.sort(key=lambda x: x["agreed_at"], reverse=reverse_sort)

    context = {
        "object": agreement,
        "agreement": agreement,
        "agreed_staff_list": agreed_staff_list,
        "query": query,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "opposite_dir": "asc" if sort_dir == "desc" else "desc",
    }
    return render(request, "master/staffagreement_detail.html", context)


@login_required
@permission_required("master.add_staffagreement", raise_exception=True)
def staff_agreement_create(request):
    """スタッフ同意文言作成"""
    company = Company.objects.first()
    if request.method == "POST":
        form = StaffAgreementForm(request.POST)
        if form.is_valid():
            agreement = form.save(commit=False)
            if company:
                agreement.corporation_number = company.corporate_number
            agreement.save()
            messages.success(request, f"同意文言「{agreement.name}」を作成しました。")
            return redirect("master:staff_agreement_list")
    else:
        form = StaffAgreementForm()

    context = {
        "form": form,
        "title": "同意文言作成",
    }
    return render(request, "master/staffagreement_form.html", context)


@login_required
@permission_required("master.change_staffagreement", raise_exception=True)
def staff_agreement_update(request, pk):
    """スタッフ同意文言編集"""
    agreement = get_object_or_404(StaffAgreement, pk=pk)
    if request.method == "POST":
        form = StaffAgreementForm(request.POST, instance=agreement)
        if form.is_valid():
            agreement = form.save()
            messages.success(request, f"同意文言「{agreement.name}」を更新しました。")
            return redirect("master:staff_agreement_list")
    else:
        form = StaffAgreementForm(instance=agreement)

    context = {
        "form": form,
        "agreement": agreement,
        "title": f"同意文言編集 - {agreement.name}",
    }
    return render(request, "master/staffagreement_form.html", context)


@login_required
@permission_required("master.delete_staffagreement", raise_exception=True)
def staff_agreement_delete(request, pk):
    """スタッフ同意文言削除"""
    agreement = get_object_or_404(StaffAgreement, pk=pk)
    if request.method == "POST":
        agreement_name = agreement.name
        agreement.delete()
        messages.success(request, f"同意文言「{agreement_name}」を削除しました。")
        return redirect("master:staff_agreement_list")

    context = {
        "agreement": agreement,
        "title": f"同意文言削除 - {agreement.name}",
    }
    return render(request, "master/staffagreement_confirm_delete.html", context)


@login_required
@permission_required("master.view_staffagreement", raise_exception=True)
def staff_agreement_change_history_list(request):
    """スタッフ同意文言変更履歴一覧"""
    from apps.system.logs.models import AppLog

    logs = AppLog.objects.filter(
        model_name="StaffAgreement", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "master/master_change_history_list.html",
        {
            "logs": logs_page,
            "title": "スタッフ同意文言変更履歴",
            "list_url": "master:staff_agreement_list",
            "model_name": "StaffAgreement",
        },
    )


@login_required
@permission_required("master.view_contractpattern", raise_exception=True)
def contract_pattern_list(request):
    """契約パターン一覧"""
    search_query = request.GET.get("search", "")
    patterns = ContractPattern.objects.all()
    if search_query:
        patterns = patterns.filter(name__icontains=search_query)

    patterns = patterns.order_by('display_order', 'name')

    context = {
        'patterns': patterns,
        'search_query': search_query,
        'title': '契約パターン管理'
    }
    return render(request, 'master/contract_pattern_list.html', context)


@login_required
@permission_required("master.add_contractpattern", raise_exception=True)
def contract_pattern_create(request):
    """契約パターン作成"""
    if request.method == 'POST':
        form = ContractPatternForm(request.POST)
        formset = BaseContractTermsFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            pattern = form.save()
            formset.instance = pattern
            formset.save()
            messages.success(request, f"契約パターン「{pattern.name}」を作成しました。")
            return redirect('master:contract_pattern_list')
    else:
        form = ContractPatternForm()
        formset = BaseContractTermsFormSet()

    context = {
        'form': form,
        'formset': formset,
        'title': '契約パターン作成'
    }
    return render(request, 'master/contract_pattern_form.html', context)


@login_required
@permission_required("master.change_contractpattern", raise_exception=True)
def contract_pattern_update(request, pk):
    """契約パターン編集"""
    pattern = get_object_or_404(ContractPattern, pk=pk)
    if request.method == 'POST':
        form = ContractPatternForm(request.POST, instance=pattern)
        formset = BaseContractTermsFormSet(request.POST, instance=pattern)
        if form.is_valid() and formset.is_valid():
            pattern = form.save()
            formset.instance = pattern
            formset.save()
            messages.success(request, f"契約パターン「{pattern.name}」を更新しました。")
            return redirect('master:contract_pattern_list')
    else:
        form = ContractPatternForm(instance=pattern)
        formset = BaseContractTermsFormSet(instance=pattern)

    context = {
        'form': form,
        'formset': formset,
        'pattern': pattern,
        'title': f'契約パターン編集 - {pattern.name}'
    }
    return render(request, 'master/contract_pattern_form.html', context)


@login_required
@permission_required("master.delete_contractpattern", raise_exception=True)
def contract_pattern_delete(request, pk):
    """契約パターン削除"""
    pattern = get_object_or_404(ContractPattern, pk=pk)
    if request.method == 'POST':
        pattern_name = pattern.name
        pattern.delete()
        messages.success(request, f"契約パターン「{pattern_name}」を削除しました。")
        return redirect('master:contract_pattern_list')

    context = {
        'pattern': pattern,
        'title': f'契約パターン削除 - {pattern.name}'
    }
    return render(request, 'master/contract_pattern_confirm_delete.html', context)
