from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.conf import settings
from django.db import transaction
from datetime import datetime, timezone, timedelta
import uuid
import os
import csv

from apps.common.constants import Constants, get_pay_unit_choices
from .models import (
    Qualification,
    Skill,
    StaffAgreement,
    EmploymentType,
    StaffRegistStatus,
    StaffContactType,
    StaffTag,
    Grade,
)
from .forms import (
    EmploymentTypeForm,
    StaffRegistStatusForm,
    GradeForm,
    CSVImportForm,
    StaffContactTypeForm,
    StaffTagForm,
    QualificationForm,
    QualificationCategoryForm,
    SkillForm,
    SkillCategoryForm,
    StaffAgreementForm,
)
from apps.staff.models import Staff
from apps.connect.models import ConnectStaffAgree
from .resources import AgreedStaffResource
from apps.system.logs.models import AppLog
from apps.company.models import Company


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

# 資格管理ビュー
@login_required
@permission_required("master.view_qualification", raise_exception=True)
def qualification_list(request):
    """資格一覧（階層表示）"""
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

# 変更履歴ビュー
@login_required
@permission_required("master.view_qualification", raise_exception=True)
def qualification_change_history_list(request):
    """資格マスタ変更履歴一覧"""
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
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "資格マスタ変更履歴",
            "back_url_name": "master:qualification_list",
            "model_name": "Qualification",
        },
    )

# 雇用形態管理ビュー
@login_required
@permission_required("master.view_employmenttype", raise_exception=True)
def employment_type_list(request):
    """雇用形態一覧"""
    search_query = request.GET.get("search", "")
    items = EmploymentType.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="EmploymentType", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="EmploymentType", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:employment_type_change_history_list",
    }
    return render(request, "master/employment_type_list.html", context)


@login_required
@permission_required("master.add_employmenttype", raise_exception=True)
def employment_type_create(request):
    """雇用形態作成"""
    if request.method == "POST":
        form = EmploymentTypeForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"雇用形態「{item.name}」を作成しました。")
            return redirect("master:employment_type_list")
    else:
        form = EmploymentTypeForm()
    context = {"form": form, "title": "雇用形態作成"}
    return render(request, "master/employment_type_form.html", context)


@login_required
@permission_required("master.change_employmenttype", raise_exception=True)
def employment_type_update(request, pk):
    """雇用形態編集"""
    item = get_object_or_404(EmploymentType, pk=pk)
    if request.method == "POST":
        form = EmploymentTypeForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"雇用形態「{item.name}」を更新しました。")
            return redirect("master:employment_type_list")
    else:
        form = EmploymentTypeForm(instance=item)
    context = {"form": form, "item": item, "title": f"雇用形態編集"}
    return render(request, "master/employment_type_form.html", context)


@login_required
@permission_required("master.delete_employmenttype", raise_exception=True)
def employment_type_delete(request, pk):
    """雇用形態削除"""
    item = get_object_or_404(EmploymentType, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"雇用形態「{item_name}」を削除しました。")
        return redirect("master:employment_type_list")
    context = {"item": item, "title": f"雇用形態削除"}
    return render(request, "master/employment_type_delete.html", context)


@login_required
@permission_required("master.view_employmenttype", raise_exception=True)
def employment_type_change_history_list(request):
    """雇用形態変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="EmploymentType", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "雇用形態変更履歴",
            "back_url_name": "master:employment_type_list",
            "model_name": "EmploymentType",
        },
    )


@login_required
@permission_required("master.view_skill", raise_exception=True)
def skill_change_history_list(request):
    """技能マスタ変更履歴一覧"""
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
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "技能マスタ変更履歴",
            "back_url_name": "master:skill_list",
            "model_name": "Skill",
        },
    )

# スタッフ同意文言管理
@login_required
@permission_required("master.view_staffagreement", raise_exception=True)
def staff_agreement_list(request):
    """スタッフ同意文言一覧"""
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
    logs = AppLog.objects.filter(
        model_name="StaffAgreement", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "common/common_change_history_list.html",
                {
                    "change_logs": logs_page,
                    "page_title": "スタッフ同意文言変更履歴",
                    "back_url_name": "master:staff_agreement_list",
                    "model_name": "StaffAgreement",
                },    )

# スタッフ登録状況管理ビュー
@login_required
@permission_required("master.view_staffregiststatus", raise_exception=True)
def staff_regist_status_list(request):
    """スタッフ登録状況一覧"""
    search_query = request.GET.get("search", "")
    items = StaffRegistStatus.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="StaffRegistStatus", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="StaffRegistStatus", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:staff_regist_status_change_history_list",
    }
    return render(request, "master/staff_regist_status_list.html", context)


@login_required
@permission_required("master.add_staffregiststatus", raise_exception=True)
def staff_regist_status_create(request):
    """スタッフ登録状況作成"""
    if request.method == "POST":
        form = StaffRegistStatusForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフ登録状況「{item.name}」を作成しました。")
            return redirect("master:staff_regist_status_list")
    else:
        form = StaffRegistStatusForm()
    context = {"form": form, "title": "スタッフ登録状況作成"}
    return render(request, "master/staff_regist_status_form.html", context)


@login_required
@permission_required("master.change_staffregiststatus", raise_exception=True)
def staff_regist_status_update(request, pk):
    """スタッフ登録状況編集"""
    item = get_object_or_404(StaffRegistStatus, pk=pk)
    if request.method == "POST":
        form = StaffRegistStatusForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフ登録状況「{item.name}」を更新しました。")
            return redirect("master:staff_regist_status_list")
    else:
        form = StaffRegistStatusForm(instance=item)
    context = {"form": form, "item": item, "title": f"スタッフ登録状況編集"}
    return render(request, "master/staff_regist_status_form.html", context)


@login_required
@permission_required("master.delete_staffregiststatus", raise_exception=True)
def staff_regist_status_delete(request, pk):
    """スタッフ登録状況削除"""
    item = get_object_or_404(StaffRegistStatus, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"スタッフ登録状況「{item_name}」を削除しました。")
        return redirect("master:staff_regist_status_list")
    context = {"item": item, "title": f"スタッフ登録状況削除"}
    return render(request, "master/staff_regist_status_delete.html", context)


@login_required
@permission_required("master.view_staffregiststatus", raise_exception=True)
def staff_regist_status_change_history_list(request):
    """スタッフ登録状況変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="StaffRegistStatus", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "スタッフ登録状況変更履歴",
            "back_url_name": "master:staff_regist_status_list",
            "model_name": "StaffRegistStatus",
        },
    )

# スタッフ連絡種別管理ビュー
@login_required
@permission_required("master.view_staffcontacttype", raise_exception=True)
def staff_contact_type_list(request):
    """スタッフ連絡種別一覧"""
    search_query = request.GET.get("search", "")
    items = StaffContactType.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="StaffContactType", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="StaffContactType", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:staff_contact_type_change_history_list",
    }
    return render(request, "master/staff_contact_type_list.html", context)


@login_required
@permission_required("master.add_staffcontacttype", raise_exception=True)
def staff_contact_type_create(request):
    """スタッフ連絡種別作成"""
    if request.method == "POST":
        form = StaffContactTypeForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフ連絡種別「{item.name}」を作成しました。")
            return redirect("master:staff_contact_type_list")
    else:
        form = StaffContactTypeForm()
    context = {"form": form, "title": "スタッフ連絡種別作成"}
    return render(request, "master/staff_contact_type_form.html", context)


@login_required
@permission_required("master.change_staffcontacttype", raise_exception=True)
def staff_contact_type_update(request, pk):
    """スタッフ連絡種別編集"""
    item = get_object_or_404(StaffContactType, pk=pk)
    if request.method == "POST":
        form = StaffContactTypeForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフ連絡種別「{item.name}」を更新しました。")
            return redirect("master:staff_contact_type_list")
    else:
        form = StaffContactTypeForm(instance=item)
    context = {"form": form, "item": item, "title": "スタッフ連絡種別編集"}
    return render(request, "master/staff_contact_type_form.html", context)


@login_required
@permission_required("master.delete_staffcontacttype", raise_exception=True)
def staff_contact_type_delete(request, pk):
    """スタッフ連絡種別削除"""
    item = get_object_or_404(StaffContactType, pk=pk)
    if item.display_order == 50:
        messages.error(request, "表示順50のデータは削除できません。")
        return redirect("master:staff_contact_type_list")

    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"スタッフ連絡種別「{item_name}」を削除しました。")
        return redirect("master:staff_contact_type_list")
    context = {"item": item, "title": "スタッフ連絡種別削除"}
    return render(request, "master/staff_contact_type_delete.html", context)


@login_required
@permission_required("master.view_staffcontacttype", raise_exception=True)
def staff_contact_type_change_history_list(request):
    """スタッフ連絡種別変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="StaffContactType", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "スタッフ連絡種別変更履歴",
            "back_url_name": "master:staff_contact_type_list",
            "model_name": "StaffContactType",
        },
    )

# スタッフタグ管理ビュー
@login_required
@permission_required("master.view_stafftag", raise_exception=True)
def staff_tag_list(request):
    """スタッフタグ一覧"""
    search_query = request.GET.get("search", "")
    items = StaffTag.objects.all()
    if search_query:
        items = items.filter(name__icontains=search_query)
    items = items.order_by("display_order")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="StaffTag", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="StaffTag", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:staff_tag_change_history_list",
    }
    return render(request, "master/staff_tag_list.html", context)


@login_required
@permission_required("master.add_stafftag", raise_exception=True)
def staff_tag_create(request):
    """スタッフタグ作成"""
    if request.method == "POST":
        form = StaffTagForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフタグ「{item.name}」を作成しました。")
            return redirect("master:staff_tag_list")
    else:
        form = StaffTagForm()
    context = {"form": form, "title": "スタッフタグ作成"}
    return render(request, "master/staff_tag_form.html", context)


@login_required
@permission_required("master.change_stafftag", raise_exception=True)
def staff_tag_update(request, pk):
    """スタッフタグ編集"""
    item = get_object_or_404(StaffTag, pk=pk)
    if request.method == "POST":
        form = StaffTagForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフタグ「{item.name}」を更新しました。")
            return redirect("master:staff_tag_list")
    else:
        form = StaffTagForm(instance=item)
    context = {"form": form, "item": item, "title": "スタッフタグ編集"}
    return render(request, "master/staff_tag_form.html", context)


@login_required
@permission_required("master.delete_stafftag", raise_exception=True)
def staff_tag_delete(request, pk):
    """スタッフタグ削除"""
    item = get_object_or_404(StaffTag, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"スタッフタグ「{item_name}」を削除しました。")
        return redirect("master:staff_tag_list")
    context = {"item": item, "title": "スタッフタグ削除"}
    return render(request, "master/staff_tag_delete.html", context)


@login_required
@permission_required("master.view_stafftag", raise_exception=True)
def staff_tag_change_history_list(request):
    """スタッフタグ変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="StaffTag", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "スタッフタグ変更履歴",
            "back_url_name": "master:staff_tag_list",
            "model_name": "StaffTag",
        },
    )

# スタッフ等級管理ビュー
@login_required
@permission_required("master.view_grade", raise_exception=True)
def grade_list(request):
    """スタッフ等級一覧"""
    search_query = request.GET.get("search", "")
    items = Grade.objects.all()
    if search_query:
        items = items.filter(Q(name__icontains=search_query) | Q(code__icontains=search_query))
    items = items.order_by("display_order", "code")
    paginator = Paginator(items, 20)
    page = request.GET.get("page")
    items_page = paginator.get_page(page)
    change_logs = AppLog.objects.filter(model_name="Grade", action__in=["create", "update", "delete"]).order_by("-timestamp")[:5]
    change_logs_count = AppLog.objects.filter(model_name="Grade", action__in=["create", "update", "delete"]).count()
    context = {
        "items": items_page,
        "search_query": search_query,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:grade_change_history_list",
    }
    return render(request, "master/grade_list.html", context)


@login_required
@permission_required("master.add_grade", raise_exception=True)
def grade_create(request):
    """スタッフ等級作成"""
    if request.method == "POST":
        form = GradeForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフ等級「{item.name}」を作成しました。")
            return redirect("master:grade_list")
    else:
        form = GradeForm()
    context = {"form": form, "title": "スタッフ等級作成"}
    return render(request, "master/grade_form.html", context)


@login_required
@permission_required("master.change_grade", raise_exception=True)
def grade_update(request, pk):
    """スタッフ等級編集"""
    item = get_object_or_404(Grade, pk=pk)
    if request.method == "POST":
        form = GradeForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"スタッフ等級「{item.name}」を更新しました。")
            return redirect("master:grade_list")
    else:
        form = GradeForm(instance=item)
    context = {"form": form, "item": item, "title": "スタッフ等級編集"}
    return render(request, "master/grade_form.html", context)


@login_required
@permission_required("master.delete_grade", raise_exception=True)
def grade_delete(request, pk):
    """スタッフ等級削除"""
    item = get_object_or_404(Grade, pk=pk)
    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"スタッフ等級「{item_name}」を削除しました。")
        return redirect("master:grade_list")
    context = {"item": item, "title": "スタッフ等級削除"}
    return render(request, "master/grade_delete.html", context)


@login_required
@permission_required("master.view_grade", raise_exception=True)
def grade_change_history_list(request):
    """スタッフ等級変更履歴一覧"""
    logs = AppLog.objects.filter(model_name="Grade", action__in=["create", "update", "delete"]).order_by("-timestamp")
    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)
    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "スタッフ等級変更履歴",
            "back_url_name": "master:grade_list",
            "model_name": "Grade",
        },
    )


@login_required
@permission_required("master.view_grade", raise_exception=True)
def grade_export(request):
    """スタッフ等級データをCSVでエクスポート"""
    # アクティブな等級データを取得
    grades = Grade.objects.filter(is_active=True).order_by("display_order", "code")

    # 給与種別のラベルマップを作成
    pay_unit_map = {code: label for code, label in get_pay_unit_choices()}

    # レスポンスの設定
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="grade_master_{timestamp}.csv"'

    # BOMを追加
    response.write("\ufeff".encode("utf-8"))

    writer = csv.writer(response)
    for grade in grades:
        writer.writerow([
            grade.start_date.strftime("%Y/%m/%d") if grade.start_date else "",
            grade.code,
            grade.name,
            pay_unit_map.get(grade.salary_type, ""),
            grade.amount,
        ])

    return response


@login_required
@permission_required("master.add_grade", raise_exception=True)
def grade_import(request):
    """スタッフ等級CSV取込ページを表示"""
    form = CSVImportForm()
    context = {
        "form": form,
        "title": "スタッフ等級CSV取込",
    }
    return render(request, "master/grade_import.html", context)


@login_required
@permission_required("master.add_grade", raise_exception=True)
@require_POST
def grade_import_upload(request):
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
@permission_required("master.add_grade", raise_exception=True)
@require_POST
def grade_import_process(request, task_id):
    """CSVファイルのインポート処理を実行"""
    task_info = cache.get(f"import_task_{task_id}")
    if not task_info or task_info["status"] != "uploaded":
        return JsonResponse({"error": "無効なタスクIDです。"}, status=400)

    file_path = task_info["file_path"]
    start_time = datetime.fromisoformat(task_info["start_time"])

    try:
        # ファイルのエンコーディングを確認（BOM付きUTF-8に対応するため）
        with open(file_path, "rb") as f:
            content = f.read()
            if content.startswith(b"\xef\xbb\xbf"):
                decoded_content = content.decode("utf-8-sig")
            else:
                decoded_content = content.decode("utf-8")

        reader = csv.reader(decoded_content.splitlines())
        rows = [row for row in reader if row]
        total_rows = len(rows)

        task_info["total"] = total_rows
        cache.set(f"import_task_{task_id}", task_info, timeout=3600)

        imported_count = 0
        errors = []

        # 給与種別の逆引きマップ
        pay_unit_map = {label: code for code, label in get_pay_unit_choices()}

        for i, row in enumerate(rows):
            progress = i + 1
            try:
                if len(row) < 5:
                    raise ValueError("項目数が不足しています。")

                start_date_str = row[0].strip()
                code = row[1].strip()
                name = row[2].strip()
                salary_type_label = row[3].strip()
                amount_str = row[4].strip()

                if not start_date_str or not code or not name or not salary_type_label or not amount_str:
                    raise ValueError("必須項目が空です。")

                # バリデーションと変換
                try:
                    start_date = datetime.strptime(start_date_str, "%Y/%m/%d").date()
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        raise ValueError(f"有効期間開始日の形式が正しくありません: {start_date_str}")

                salary_type = pay_unit_map.get(salary_type_label)
                if not salary_type:
                    raise ValueError(f"不正な給与種別です: {salary_type_label}")

                try:
                    amount = int(amount_str)
                except ValueError:
                    raise ValueError(f"金額が数値ではありません: {amount_str}")

                with transaction.atomic():
                    # 同じコードで、開始日時点で有効なデータがある場合、既存データの終了日を更新
                    overlap_grades = Grade.objects.filter(
                        code=code,
                        is_active=True,
                    ).filter(
                        Q(end_date__isnull=True) | Q(end_date__gte=start_date)
                    ).filter(start_date__lte=start_date)

                    yesterday = start_date - timedelta(days=1)

                    for old_grade in overlap_grades:
                        old_grade.end_date = yesterday
                        # もし開始日より前になってしまったら無効化すべきか？
                        # とりあえず終了日を更新
                        old_grade.save()

                    # 新規登録
                    Grade.objects.create(
                        code=code,
                        name=name,
                        salary_type=salary_type,
                        amount=amount,
                        start_date=start_date,
                        is_active=True,
                    )
                    imported_count += 1

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
        task_info = cache.get(f"import_task_{task_id}") or {}
        task_info["status"] = "failed"
        task_info["errors"] = [f"処理中に予期せぬエラーが発生しました: {e}"]
        cache.set(f"import_task_{task_id}", task_info, timeout=3600)
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)


@login_required
@permission_required("master.add_grade", raise_exception=True)
def grade_import_progress(request, task_id):
    """インポートの進捗状況を返す"""
    task_info = cache.get(f"import_task_{task_id}")
    if not task_info:
        return JsonResponse({"error": "無効なタスクIDです。"}, status=404)

    return JsonResponse(task_info)
