from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models_phrase import PhraseTemplate, PhraseTemplateTitle
from .forms_phrase import PhraseTemplateForm


@login_required
@permission_required('master.view_phrasetemplate', raise_exception=True)
def phrase_template_list(request):
    """汎用文言テンプレート一覧"""
    search_query = request.GET.get('q', '')
    title_filter = request.GET.get('title', '')
    status_filter = request.GET.get('status', '')

    # PhraseTemplateTitleの一覧を取得
    phrase_titles = PhraseTemplateTitle.get_active_list()
    
    # 選択されたタイトルを取得
    selected_title = None
    if title_filter:
        try:
            selected_title = PhraseTemplateTitle.objects.get(pk=title_filter, is_active=True)
        except PhraseTemplateTitle.DoesNotExist:
            pass

    phrases = PhraseTemplate.objects.select_related('title')

    # 検索条件を適用
    if search_query:
        phrases = phrases.filter(
            Q(content__icontains=search_query)
        )

    # タイトルフィルタを適用
    if selected_title:
        phrases = phrases.filter(title=selected_title)

    # 状態フィルタを適用
    if status_filter:
        if status_filter == 'active':
            phrases = phrases.filter(is_active=True)
        elif status_filter == 'inactive':
            phrases = phrases.filter(is_active=False)

    phrases = phrases.order_by('title__display_order', 'display_order', 'id')

    # ページネーション
    paginator = Paginator(phrases, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
        'title_filter': title_filter,
        'status_filter': status_filter,
        'phrase_titles': phrase_titles,
        'selected_title': selected_title,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    }
    return render(request, 'master/phrase_template_list.html', context)



@login_required
@permission_required('master.add_phrasetemplate', raise_exception=True)
def phrase_template_create(request):
    """汎用文言テンプレート作成"""
    title_id = request.GET.get('title')
    selected_title = None
    
    if title_id:
        try:
            selected_title = PhraseTemplateTitle.objects.get(pk=title_id, is_active=True)
        except PhraseTemplateTitle.DoesNotExist:
            messages.error(request, '指定された文言タイトルが見つかりません。')
            return redirect('master:phrase_template_list')
    else:
        messages.error(request, '文言タイトルを選択してください。')
        return redirect('master:phrase_template_list')
    
    if request.method == 'POST':
        form = PhraseTemplateForm(request.POST, selected_title=selected_title)
        if form.is_valid():
            phrase = form.save()
            messages.success(request, f'汎用文言テンプレート「{phrase.title.name}」を作成しました。')
            return HttpResponseRedirect(reverse('master:phrase_template_list') + f'?title={selected_title.pk}')
    else:
        form = PhraseTemplateForm(selected_title=selected_title)

    context = {
        'form': form,
        'selected_title': selected_title,
        'title': '汎用文言テンプレート作成',
    }
    return render(request, 'master/phrase_template_form.html', context)


@login_required
@permission_required('master.change_phrasetemplate', raise_exception=True)
def phrase_template_update(request, pk):
    """汎用文言テンプレート更新"""
    phrase = get_object_or_404(PhraseTemplate, pk=pk)
    
    if request.method == 'POST':
        form = PhraseTemplateForm(request.POST, instance=phrase, selected_title=phrase.title)
        if form.is_valid():
            phrase = form.save()
            messages.success(request, f'汎用文言テンプレート「{phrase.title.name}」を更新しました。')
            return HttpResponseRedirect(reverse('master:phrase_template_list') + f'?title={phrase.title.pk}')
    else:
        form = PhraseTemplateForm(instance=phrase, selected_title=phrase.title)

    context = {
        'form': form,
        'phrase': phrase,
        'selected_title': phrase.title,
        'title': '汎用文言テンプレート編集',
    }
    return render(request, 'master/phrase_template_form.html', context)


@login_required
@permission_required('master.delete_phrasetemplate', raise_exception=True)
def phrase_template_delete(request, pk):
    """汎用文言テンプレート削除"""
    phrase = get_object_or_404(PhraseTemplate, pk=pk)
    
    if request.method == 'POST':
        title_name = phrase.title.name
        title_pk = phrase.title.pk
        phrase.delete()
        messages.success(request, f'汎用文言テンプレート「{title_name}」を削除しました。')
        return HttpResponseRedirect(reverse('master:phrase_template_list') + f'?title={title_pk}')

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