from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponseRedirect, JsonResponse
from urllib.parse import urlencode
from datetime import date
from itertools import chain

from .models import (
    JobCategory,
    ContractPattern,
    ContractTerms,
    MinimumPay,
    OvertimePattern,
)
from .forms import (
    JobCategoryForm,
    ContractPatternForm,
    ContractTermForm,
    MinimumPayForm,
)
from apps.system.logs.models import AppLog
from apps.system.settings.models import Dropdowns

# 職種管理ビュー
@login_required
@permission_required("master.view_jobcategory", raise_exception=True)
def job_category_list(request):
    """職種一覧"""
    search_query = request.GET.get("search", "")

    job_categories = JobCategory.objects.all()

    if search_query:
        job_categories = job_categories.filter(Q(name__icontains=search_query))

    # 利用件数を事前に計算してアノテーション
    job_categories = job_categories.annotate(
        usage_count=Count("clientcontract", distinct=True) + Count("staffcontract", distinct=True)
    )

    job_categories = job_categories.order_by("display_order", "name")

    paginator = Paginator(job_categories, 20)
    page = request.GET.get("page")
    job_categories_page = paginator.get_page(page)

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


@login_required
@permission_required("master.view_jobcategory", raise_exception=True)
def job_category_change_history_list(request):
    """職種マスタ変更履歴一覧"""
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
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "職種マスタ変更履歴",
            "back_url_name": "master:job_category_list",
            "model_name": "JobCategory",
        },
    )

@login_required
@permission_required("master.view_contractpattern", raise_exception=True)
def contract_pattern_list(request):
    """契約書パターン一覧"""
    search_query = request.GET.get("search", "")
    patterns = ContractPattern.objects.all()
    if search_query:
        patterns = patterns.filter(name__icontains=search_query)

    # 利用件数を事前に計算してアノテーション
    patterns = patterns.annotate(
        usage_count=Count("clientcontract", distinct=True) + Count("staffcontract", distinct=True)
    )

    patterns = patterns.order_by('domain', 'display_order')

    paginator = Paginator(patterns, 20)
    page = request.GET.get("page")
    patterns_page = paginator.get_page(page)

    change_logs = AppLog.objects.filter(
        model_name__in=["ContractPattern", "ContractTerms"], action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name__in=["ContractPattern", "ContractTerms"], action__in=["create", "update", "delete"]
    ).count()

    context = {
        'patterns': patterns_page,
        'search_query': search_query,
        'title': '契約書パターン管理',
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    }
    return render(request, 'master/contract_pattern_list.html', context)


@login_required
@permission_required("master.add_contractpattern", raise_exception=True)
def contract_pattern_create(request):
    """契約書パターン作成"""
    if request.method == 'POST':
        form = ContractPatternForm(request.POST)
        if form.is_valid():
            pattern = form.save()
            messages.success(request, f"契約書パターン「{pattern.name}」を作成しました。")
            return redirect('master:contract_pattern_list')
    else:
        form = ContractPatternForm()

    context = {
        'form': form,
        'title': '契約書パターン作成',
    }
    return render(request, 'master/contract_pattern_form.html', context)


@login_required
@permission_required("master.add_contractpattern", raise_exception=True)
def contract_pattern_copy(request, pk):
    """契約書パターンをコピーして新規作成"""
    original_pattern = get_object_or_404(ContractPattern, pk=pk)

    if request.method == 'POST':
        form = ContractPatternForm(request.POST)
        if form.is_valid():
            # 新しい契約書パターンを作成
            new_pattern = form.save()

            # 元の契約書パターンの契約文言をコピー
            original_terms = original_pattern.terms.all()
            for term in original_terms:
                ContractTerms.objects.create(
                    contract_pattern=new_pattern,
                    contract_clause=term.contract_clause,
                    contract_terms=term.contract_terms,
                    memo=term.memo,
                    display_order=term.display_order,
                )

            messages.success(request, f"契約書パターン「{original_pattern.name}」をコピーして「{new_pattern.name}」を作成しました。")
            return redirect('master:contract_pattern_list')
    else:
        # GETリクエストの場合、元のデータでフォームを初期化
        initial_data = {
            'name': f"{original_pattern.name}のコピー",
            'domain': original_pattern.domain,
            'display_order': original_pattern.display_order,
            'is_active': original_pattern.is_active,
        }
        form = ContractPatternForm(initial=initial_data)

    context = {
        'form': form,
        'title': '契約書パターンコピー作成',
        'is_copy': True,
        'original_id': pk,
    }
    return render(request, 'master/contract_pattern_form.html', context)


@login_required
@permission_required("master.change_contractpattern", raise_exception=True)
def contract_pattern_update(request, pk):
    """契約書パターン編集"""
    pattern = get_object_or_404(ContractPattern, pk=pk)
    if request.method == 'POST':
        form = ContractPatternForm(request.POST, instance=pattern)
        if form.is_valid():
            pattern = form.save()
            messages.success(request, f"契約書パターン「{pattern.name}」を更新しました。")
            return redirect('master:contract_pattern_list')
    else:
        form = ContractPatternForm(instance=pattern)

    context = {
        'form': form,
        'pattern': pattern,
        'title': f'契約書パターン編集 - {pattern.name}',
    }
    return render(request, 'master/contract_pattern_form.html', context)

@login_required
@permission_required("master.view_contractpattern", raise_exception=True)
def contract_pattern_detail(request, pk):
    """契約書パターン詳細"""
    pattern = get_object_or_404(ContractPattern, pk=pk)
    terms = pattern.terms.all()

    # 契約書パターンの変更履歴
    pattern_logs = AppLog.objects.filter(
        model_name='ContractPattern',
        object_id=str(pattern.pk)
    )

    # 関連する契約文言の変更履歴
    term_ids = [str(term.pk) for term in terms]
    terms_logs = AppLog.objects.filter(
        model_name='ContractTerms',
        object_id__in=term_ids
    )

    # 履歴を結合してソート
    change_logs = sorted(
        chain(pattern_logs, terms_logs),
        key=lambda log: log.timestamp,
        reverse=True
    )

    context = {
        'pattern': pattern,
        'terms': terms,
        'title': f'契約書パターン詳細 - {pattern.name}',
        'change_logs': change_logs[:20],  # ページネーションは一旦省略し、最新20件を表示
        'change_logs_count': len(change_logs),
    }
    return render(request, 'master/contract_pattern_detail.html', context)


@login_required
@permission_required("master.delete_contractpattern", raise_exception=True)
def contract_pattern_delete(request, pk):
    """契約書パターン削除"""
    pattern = get_object_or_404(ContractPattern, pk=pk)
    if request.method == 'POST':
        pattern_name = pattern.name
        pattern.delete()
        messages.success(request, f"契約書パターン「{pattern_name}」を削除しました。")
        return redirect('master:contract_pattern_list')

    context = {
        'pattern': pattern,
        'title': f'契約書パターン削除 - {pattern.name}'
    }
    return render(request, 'master/contract_pattern_confirm_delete.html', context)


@login_required
@permission_required("master.view_contractpattern", raise_exception=True)
def contract_pattern_change_history_list(request):
    """契約書パターン変更履歴一覧"""
    logs = AppLog.objects.filter(
        model_name__in=["ContractPattern", "ContractTerms"], action__in=["create", "update", "delete"]
    ).order_by("-timestamp")

    paginator = Paginator(logs, 20)
    page = request.GET.get("page")
    logs_page = paginator.get_page(page)

    return render(
        request,
        "common/common_change_history_list.html",
        {
            "change_logs": logs_page,
            "page_title": "契約書パターン変更履歴",
            "back_url_name": "master:contract_pattern_list",
            "model_name": "ContractPattern",
        },
    )


@login_required
@permission_required("master.add_contractterms", raise_exception=True)
def contract_term_create(request, pattern_pk):
    """契約文言作成"""
    pattern = get_object_or_404(ContractPattern, pk=pattern_pk)
    if request.method == 'POST':
        form = ContractTermForm(request.POST, contract_pattern=pattern)
        if form.is_valid():
            term = form.save(commit=False)
            term.contract_pattern = pattern
            term.save()
            messages.success(request, "契約文言を作成しました。")
            return redirect('master:contract_pattern_detail', pk=pattern_pk)
    else:
        form = ContractTermForm(contract_pattern=pattern)

    context = {
        'form': form,
        'pattern': pattern,
        'title': '契約文言作成'
    }
    return render(request, 'master/contract_term_form.html', context)


@login_required
@permission_required("master.change_contractterms", raise_exception=True)
def contract_term_update(request, pk):
    """契約文言編集"""
    term = get_object_or_404(ContractTerms, pk=pk)
    pattern = term.contract_pattern
    if request.method == 'POST':
        form = ContractTermForm(request.POST, instance=term)
        if form.is_valid():
            form.save()
            messages.success(request, "契約文言を更新しました。")
            return redirect('master:contract_pattern_detail', pk=pattern.pk)
    else:
        form = ContractTermForm(instance=term)

    context = {
        'form': form,
        'term': term,
        'pattern': pattern,
        'title': '契約文言編集'
    }
    return render(request, 'master/contract_term_form.html', context)


@login_required
@permission_required("master.delete_contractterms", raise_exception=True)
def contract_term_delete(request, pk):
    """契約文言削除"""
    term = get_object_or_404(ContractTerms, pk=pk)
    pattern_pk = term.contract_pattern.pk
    if request.method == 'POST':
        term.delete()
        messages.success(request, "契約文言を削除しました。")
        return redirect('master:contract_pattern_detail', pk=pattern_pk)

    context = {
        'term': term,
        'title': '契約文言削除'
    }
    return render(request, 'master/contract_term_confirm_delete.html', context)


# 最低賃金管理ビュー
@login_required
@permission_required("master.view_minimumpay", raise_exception=True)
def minimum_pay_list(request):
    """最低賃金一覧"""
    search_query = request.GET.get("search", "")
    pref_filter = request.GET.get("pref", "")
    date_filter = request.GET.get("date_filter", "")
    sort_by = request.GET.get("sort", "display_order")
    order = request.GET.get("order", "asc")

    # /master/ からの遷移の場合、デフォルトで「現在以降」を選択してリダイレクト
    referer = request.META.get('HTTP_REFERER')
    if referer and referer.endswith('/master/') and not any(key in request.GET for key in ['search', 'pref', 'date_filter']):
        params = {
            'sort': sort_by,
            'order': order,
            'search': '',
            'pref': '',
            'date_filter': 'future'
        }
        # pageパラメータがある場合は保持
        if 'page' in request.GET:
            params['page'] = request.GET.get('page')

        query_string = urlencode(params)
        return HttpResponseRedirect(f"{request.path}?{query_string}")

    minimum_pays_query = MinimumPay.objects.all()

    if search_query:
        minimum_pays_query = minimum_pays_query.filter(
            Q(hourly_wage__icontains=search_query)
        )

    if pref_filter:
        minimum_pays_query = minimum_pays_query.filter(pref=pref_filter)

    if date_filter == 'future':
        today = date.today()

        # 1. 未来のレコードのPKを取得
        future_pks = set(minimum_pays_query.filter(start_date__gt=today).values_list('pk', flat=True))

        # 2. 各都道府県の現在有効な最新レコードのPKを取得
        past_records = minimum_pays_query.filter(start_date__lte=today).order_by('pref', '-start_date')

        latest_past_pks = []
        seen_prefs = set()
        for record in past_records:
            if record.pref not in seen_prefs:
                latest_past_pks.append(record.pk)
                seen_prefs.add(record.pref)

        # 3. PKを結合してフィルタリング
        combined_pks = future_pks.union(set(latest_past_pks))
        minimum_pays = MinimumPay.objects.filter(pk__in=combined_pks)
    else:
        minimum_pays = minimum_pays_query

    # ソート処理
    valid_sort_fields = {
        'pref': 'pref',
        'start_date': 'start_date',
        'hourly_wage': 'hourly_wage',
        'display_order': 'display_order'
    }

    if sort_by in valid_sort_fields:
        sort_field = valid_sort_fields[sort_by]
        if order == 'desc':
            sort_field = f'-{sort_field}'
        minimum_pays = minimum_pays.order_by(sort_field, "pref", "-start_date")
    else:
        minimum_pays = minimum_pays.order_by("display_order", "pref", "-start_date")

    paginator = Paginator(minimum_pays, 20)
    page = request.GET.get("page")
    minimum_pays_page = paginator.get_page(page)

    pref_choices = Dropdowns.objects.filter(category='pref', active=True).order_by('disp_seq')

    change_logs = AppLog.objects.filter(
        model_name="MinimumPay", action__in=["create", "update", "delete"]
    ).order_by("-timestamp")[:5]

    change_logs_count = AppLog.objects.filter(
        model_name="MinimumPay", action__in=["create", "update", "delete"]
    ).count()

    context = {
        "minimum_pays": minimum_pays_page,
        "search_query": search_query,
        "pref_filter": pref_filter,
        "date_filter": date_filter,
        "sort_by": sort_by,
        "order": order,
        "pref_choices": pref_choices,
        "change_logs": change_logs,
        "change_logs_count": change_logs_count,
        "history_url_name": "master:minimum_pay_change_history_list",
    }
    return render(request, "master/minimum_pay_list.html", context)


@login_required
@permission_required("master.add_minimumpay", raise_exception=True)
def minimum_pay_create(request):
    """最低賃金作成"""
    if request.method == "POST":
        form = MinimumPayForm(request.POST)
        if form.is_valid():
            minimum_pay = form.save()
            messages.success(request, f"最低賃金「{minimum_pay}」を作成しました。")
            return redirect("master:minimum_pay_list")
    else:
        form = MinimumPayForm()

    context = {
        "form": form,
        "title": "最低賃金作成",
    }
    return render(request, "master/minimum_pay_form.html", context)


@login_required
@permission_required("master.change_minimumpay", raise_exception=True)
def minimum_pay_update(request, pk):
    """最低賃金編集"""
    minimum_pay = get_object_or_404(MinimumPay, pk=pk)

    if request.method == "POST":
        form = MinimumPayForm(request.POST, instance=minimum_pay)
        if form.is_valid():
            minimum_pay = form.save()
            messages.success(request, f"最低賃金「{minimum_pay}」を更新しました。")
            return redirect("master:minimum_pay_list")
    else:
        form = MinimumPayForm(instance=minimum_pay)

    context = {
        "form": form,
        "minimum_pay": minimum_pay,
        "title": f"最低賃金編集 - {minimum_pay}",
    }
    return render(request, "master/minimum_pay_form.html", context)


@login_required
@permission_required("master.delete_minimumpay", raise_exception=True)
def minimum_pay_delete(request, pk):
    """最低賃金削除"""
    minimum_pay = get_object_or_404(MinimumPay, pk=pk)

    if request.method == "POST":
        minimum_pay_name = str(minimum_pay)
        minimum_pay.delete()
        messages.success(request, f"最低賃金「{minimum_pay_name}」を削除しました。")
        return redirect("master:minimum_pay_list")

    context = {
        "object": minimum_pay,
        "title": f"最低賃金削除 - {minimum_pay}",
    }
    return render(request, "master/minimum_pay_confirm_delete.html", context)


@login_required
@permission_required("master.view_minimumpay", raise_exception=True)
def minimum_pay_change_history_list(request):
    """最低賃金マスタ変更履歴一覧"""
    # 最低賃金マスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name="MinimumPay", action__in=["create", "update", "delete"]
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
            "page_title": "最低賃金マスタ変更履歴",
            "back_url_name": "master:minimum_pay_list",
            "model_name": "MinimumPay",
        },
    )







