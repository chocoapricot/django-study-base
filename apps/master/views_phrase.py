from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models_phrase import PhraseTemplate
from .forms_phrase import PhraseTemplateForm


@login_required
@permission_required('master.view_phrasetemplate', raise_exception=True)
def phrase_template_list(request):
    """汎用文言テンプレート一覧"""
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')

    phrases = PhraseTemplate.objects.all()

    # 検索条件を適用
    if search_query:
        phrases = phrases.filter(
            Q(content__icontains=search_query)
        )

    # 分類フィルタを適用
    if category_filter:
        phrases = phrases.filter(category=category_filter)

    # 状態フィルタを適用
    if status_filter:
        if status_filter == 'active':
            phrases = phrases.filter(is_active=True)
        elif status_filter == 'inactive':
            phrases = phrases.filter(is_active=False)

    phrases = phrases.order_by('category', 'display_order', 'id')

    # ページネーション
    paginator = Paginator(phrases, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 分類の選択肢を取得
    category_choices = PhraseTemplate.CATEGORY_CHOICES

    # 変更履歴を取得
    from apps.system.logs.models import AppLog
    change_logs = AppLog.objects.filter(
        model_name='PhraseTemplate',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]
    change_logs_count = AppLog.objects.filter(
        model_name='PhraseTemplate',
        action__in=['create', 'update', 'delete']
    ).count()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'category_choices': category_choices,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    }
    return render(request, 'master/phrase_template_list.html', context)



@login_required
@permission_required('master.add_phrasetemplate', raise_exception=True)
def phrase_template_create(request):
    """汎用文言テンプレート作成"""
    if request.method == 'POST':
        form = PhraseTemplateForm(request.POST)
        if form.is_valid():
            phrase = form.save()
            messages.success(request, f'汎用文言テンプレート「{phrase.get_category_display()}」を作成しました。')
            return redirect('master:phrase_template_list')
    else:
        form = PhraseTemplateForm()

    context = {
        'form': form,
        'title': '汎用文言テンプレート作成',
    }
    return render(request, 'master/phrase_template_form.html', context)


@login_required
@permission_required('master.change_phrasetemplate', raise_exception=True)
def phrase_template_update(request, pk):
    """汎用文言テンプレート更新"""
    phrase = get_object_or_404(PhraseTemplate, pk=pk)
    
    if request.method == 'POST':
        form = PhraseTemplateForm(request.POST, instance=phrase)
        if form.is_valid():
            phrase = form.save()
            messages.success(request, f'汎用文言テンプレート「{phrase.get_category_display()}」を更新しました。')
            return redirect('master:phrase_template_list')
    else:
        form = PhraseTemplateForm(instance=phrase)

    context = {
        'form': form,
        'phrase': phrase,
        'title': '汎用文言テンプレート編集',
    }
    return render(request, 'master/phrase_template_form.html', context)


@login_required
@permission_required('master.delete_phrasetemplate', raise_exception=True)
def phrase_template_delete(request, pk):
    """汎用文言テンプレート削除"""
    phrase = get_object_or_404(PhraseTemplate, pk=pk)
    
    if request.method == 'POST':
        category_display = phrase.get_category_display()
        phrase.delete()
        messages.success(request, f'汎用文言テンプレート「{category_display}」を削除しました。')
        return redirect('master:phrase_template_list')

    context = {
        'phrase': phrase,
        'title': '汎用文言テンプレート削除',
    }
    return render(request, 'master/phrase_template_delete.html', context)


@login_required
@permission_required('master.view_phrasetemplate', raise_exception=True)
def phrase_template_change_history_list(request):
    """汎用文言テンプレート変更履歴一覧"""
    from apps.system.logs.models import AppLog
    
    # AppLogから履歴を取得
    change_logs = AppLog.objects.filter(
        model_name='PhraseTemplate',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(change_logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'title': '汎用文言テンプレート変更履歴',
        'model_name': 'PhraseTemplate',
        'list_url': 'master:phrase_template_list',
    }
    return render(request, 'common/change_history_list.html', context)