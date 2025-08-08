from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.apps import apps
from .models import Qualification, Skill
from .forms import QualificationForm, QualificationCategoryForm, SkillForm, SkillCategoryForm


# マスタ設定データ
MASTER_CONFIGS = [
    {
        'name': '資格管理',
        'description': '資格・免許・認定等の管理',
        'model': 'master.Qualification',
        'url_name': 'master:qualification_list',
        'icon': 'bi-award',
        'permission': 'master.view_qualification'
    },
    {
        'name': '技能管理', 
        'description': 'スキル・技術・能力等の管理',
        'model': 'master.Skill',
        'url_name': 'master:skill_list',
        'icon': 'bi-tools',
        'permission': 'master.view_skill'
    }
]


def get_category_count(model_class):
    """レベル1（カテゴリ）のデータ数を取得"""
    try:
        return model_class.objects.filter(level=1, is_active=True).count()
    except Exception:
        return 0


def get_data_count(model_class):
    """レベル2（データ）のデータ数を取得"""
    try:
        return model_class.objects.filter(level=2, is_active=True).count()
    except Exception:
        return 0


@login_required
@permission_required('master.view_qualification', raise_exception=True)
def master_index_list(request):
    """マスタ一覧画面を表示"""
    masters = []
    
    for config in MASTER_CONFIGS:
        # 権限チェック
        if not request.user.has_perm(config['permission']):
            continue
            
        try:
            # モデルクラスを動的に取得
            model_class = apps.get_model(config['model'])
            
            # データ件数を集計
            category_count = get_category_count(model_class)
            data_count = get_data_count(model_class)
            total_count = category_count + data_count
            
            # URLを生成
            try:
                url = reverse(config['url_name'])
            except Exception:
                url = '#'  # URLが生成できない場合のフォールバック
            
            # マスタ情報を構築
            master_info = {
                'name': config['name'],
                'description': config['description'],
                'category_count': category_count,
                'data_count': data_count,
                'total_count': total_count,
                'url': url,
                'icon': config['icon']
            }
            
            masters.append(master_info)
            
        except Exception:
            # モデルクラスが存在しない場合などのエラーハンドリング
            continue
    
    context = {
        'masters': masters,
    }
    return render(request, 'master/master_index_list.html', context)


# 資格管理ビュー
@login_required
@permission_required('master.view_qualification', raise_exception=True)
def qualification_list(request):
    """資格一覧（階層表示）"""
    from apps.system.logs.models import AppLog
    
    # 検索機能
    search_query = request.GET.get('q', '')
    
    # レベルフィルタ
    level_filter = request.GET.get('level', '')
    
    # カテゴリフィルタ（親カテゴリ）
    category_filter = request.GET.get('category', '')
    
    # アクティブフィルタ
    is_active_filter = request.GET.get('is_active', '')
    
    # フィルタ条件に基づいてカテゴリと資格を取得
    categories_query = Qualification.objects.filter(level=1)
    qualifications_query = Qualification.objects.filter(level=2).select_related('parent')
    
    # 検索条件を適用
    if search_query:
        categories_query = categories_query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
        qualifications_query = qualifications_query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(parent__name__icontains=search_query)
        )
    
    # アクティブフィルタを適用
    if is_active_filter:
        is_active = is_active_filter == 'true'
        categories_query = categories_query.filter(is_active=is_active)
        qualifications_query = qualifications_query.filter(is_active=is_active)
    
    # カテゴリフィルタを適用
    if category_filter:
        categories_query = categories_query.filter(pk=category_filter)
        qualifications_query = qualifications_query.filter(parent_id=category_filter)
    
    # レベルフィルタを適用
    if level_filter == '1':
        # カテゴリのみ表示
        qualifications_query = Qualification.objects.none()
    elif level_filter == '2':
        # 資格のみ表示 - カテゴリは表示しないが、資格は表示する
        categories_query = Qualification.objects.none()
    
    # シンプルな一覧用データを整理
    items = []
    
    if level_filter == '2':
        # 資格のみ表示の場合は、資格を直接追加
        items.extend(qualifications_query.filter(is_active=True).order_by('display_order', 'name'))
    else:
        # 通常の表示（カテゴリと資格、またはカテゴリのみ）
        for category in categories_query.filter(is_active=True).order_by('display_order', 'name'):
            # カテゴリを追加
            items.append(category)
            
            # カテゴリに属する資格を追加
            category_qualifications = qualifications_query.filter(parent=category, is_active=True).order_by('display_order', 'name')
            items.extend(category_qualifications)
    
    # フィルタ用のカテゴリ一覧
    all_categories = Qualification.get_categories()
    
    # 変更履歴（最新5件）
    change_logs = AppLog.objects.filter(
        model_name='Qualification',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]
    
    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name='Qualification',
        action__in=['create', 'update', 'delete']
    ).count()
    
    context = {
        'items': items,
        'search_query': search_query,
        'level_filter': level_filter,
        'category_filter': category_filter,
        'is_active_filter': is_active_filter,
        'categories': all_categories,
        'level_choices': Qualification.LEVEL_CHOICES,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    }
    return render(request, 'master/qualification_list.html', context)


@login_required
@permission_required('master.view_qualification', raise_exception=True)
def qualification_detail(request, pk):
    """資格詳細"""
    qualification = get_object_or_404(Qualification, pk=pk)
    context = {
        'qualification': qualification,
    }
    return render(request, 'master/qualification_detail.html', context)


@login_required
@permission_required('master.add_qualification', raise_exception=True)
def qualification_category_create(request):
    """資格カテゴリ作成"""
    if request.method == 'POST':
        form = QualificationCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.updated_by = request.user
            category.save()
            messages.success(request, f'カテゴリ「{category.name}」を作成しました。')
            return redirect('master:qualification_detail', pk=category.pk)
    else:
        form = QualificationCategoryForm()
    
    context = {
        'form': form,
        'title': 'カテゴリ作成',
    }
    return render(request, 'master/qualification_category_form.html', context)


@login_required
@permission_required('master.add_qualification', raise_exception=True)
def qualification_create(request):
    """資格作成"""
    if request.method == 'POST':
        form = QualificationForm(request.POST)
        if form.is_valid():
            qualification = form.save(commit=False)
            qualification.created_by = request.user
            qualification.updated_by = request.user
            qualification.save()
            messages.success(request, f'資格「{qualification.name}」を作成しました。')
            return redirect('master:qualification_detail', pk=qualification.pk)
    else:
        form = QualificationForm()
    
    context = {
        'form': form,
        'title': '資格作成',
    }
    return render(request, 'master/qualification_form.html', context)


@login_required
@permission_required('master.change_qualification', raise_exception=True)
def qualification_update(request, pk):
    """資格更新"""
    qualification = get_object_or_404(Qualification, pk=pk)
    
    # カテゴリか資格かによってフォームを切り替え
    if qualification.is_category:
        form_class = QualificationCategoryForm
        template_name = 'master/qualification_category_form.html'
        title = 'カテゴリ編集'
    else:
        form_class = QualificationForm
        template_name = 'master/qualification_form.html'
        title = '資格編集'
    
    if request.method == 'POST':
        form = form_class(request.POST, instance=qualification)
        if form.is_valid():
            qualification = form.save(commit=False)
            qualification.updated_by = request.user
            qualification.save()
            messages.success(request, f'「{qualification.name}」を更新しました。')
            return redirect('master:qualification_detail', pk=qualification.pk)
    else:
        form = form_class(instance=qualification)
    
    context = {
        'form': form,
        'qualification': qualification,
        'title': title,
    }
    return render(request, template_name, context)


@login_required
@permission_required('master.delete_qualification', raise_exception=True)
def qualification_delete(request, pk):
    """資格削除"""
    qualification = get_object_or_404(Qualification, pk=pk)
    
    if request.method == 'POST':
        qualification_name = qualification.name
        qualification.delete()
        messages.success(request, f'資格「{qualification_name}」を削除しました。')
        return redirect('master:qualification_list')
    
    context = {
        'qualification': qualification,
    }
    return render(request, 'master/qualification_delete.html', context)


# 技能管理ビュー
@login_required
@permission_required('master.view_skill', raise_exception=True)
def skill_list(request):
    """技能一覧（階層表示）"""
    from apps.system.logs.models import AppLog
    
    # 検索機能
    search_query = request.GET.get('q', '')
    
    # レベルフィルタ
    level_filter = request.GET.get('level', '')
    
    # カテゴリフィルタ（親カテゴリ）
    category_filter = request.GET.get('category', '')
    
    # アクティブフィルタ
    is_active_filter = request.GET.get('is_active', '')
    
    # フィルタ条件に基づいてカテゴリと技能を取得
    categories_query = Skill.objects.filter(level=1)
    skills_query = Skill.objects.filter(level=2).select_related('parent')
    
    # 検索条件を適用
    if search_query:
        categories_query = categories_query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
        skills_query = skills_query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(parent__name__icontains=search_query)
        )
    
    # アクティブフィルタを適用
    if is_active_filter:
        is_active = is_active_filter == 'true'
        categories_query = categories_query.filter(is_active=is_active)
        skills_query = skills_query.filter(is_active=is_active)
    
    # カテゴリフィルタを適用
    if category_filter:
        categories_query = categories_query.filter(pk=category_filter)
        skills_query = skills_query.filter(parent_id=category_filter)
    
    # レベルフィルタを適用
    if level_filter == '1':
        # カテゴリのみ表示
        skills_query = Skill.objects.none()
    elif level_filter == '2':
        # 技能のみ表示
        categories_query = Skill.objects.none()
    
    # シンプルな一覧用データを整理
    items = []
    
    if level_filter == '2':
        # 技能のみ表示の場合は、技能を直接追加
        items.extend(skills_query.filter(is_active=True).order_by('display_order', 'name'))
    else:
        # 通常の表示（カテゴリと技能、またはカテゴリのみ）
        for category in categories_query.filter(is_active=True).order_by('display_order', 'name'):
            # カテゴリを追加
            items.append(category)
            
            # カテゴリに属する技能を追加
            category_skills = skills_query.filter(parent=category, is_active=True).order_by('display_order', 'name')
            items.extend(category_skills)
    
    # フィルタ用のカテゴリ一覧
    all_categories = Skill.get_categories()
    
    # 変更履歴（最新5件）
    change_logs = AppLog.objects.filter(
        model_name='Skill',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]
    
    # 変更履歴の総件数
    change_logs_count = AppLog.objects.filter(
        model_name='Skill',
        action__in=['create', 'update', 'delete']
    ).count()
    
    context = {
        'items': items,
        'search_query': search_query,
        'level_filter': level_filter,
        'category_filter': category_filter,
        'is_active_filter': is_active_filter,
        'categories': all_categories,
        'level_choices': Skill.LEVEL_CHOICES,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    }
    return render(request, 'master/skill_list.html', context)


@login_required
@permission_required('master.view_skill', raise_exception=True)
def skill_detail(request, pk):
    """技能詳細"""
    skill = get_object_or_404(Skill, pk=pk)
    context = {
        'skill': skill,
    }
    return render(request, 'master/skill_detail.html', context)


@login_required
@permission_required('master.add_skill', raise_exception=True)
def skill_category_create(request):
    """技能カテゴリ作成"""
    if request.method == 'POST':
        form = SkillCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.updated_by = request.user
            category.save()
            messages.success(request, f'カテゴリ「{category.name}」を作成しました。')
            return redirect('master:skill_detail', pk=category.pk)
    else:
        form = SkillCategoryForm()
    
    context = {
        'form': form,
        'title': 'カテゴリ作成',
    }
    return render(request, 'master/skill_category_form.html', context)


@login_required
@permission_required('master.add_skill', raise_exception=True)
def skill_create(request):
    """技能作成"""
    if request.method == 'POST':
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.created_by = request.user
            skill.updated_by = request.user
            skill.save()
            messages.success(request, f'技能「{skill.name}」を作成しました。')
            return redirect('master:skill_detail', pk=skill.pk)
    else:
        form = SkillForm()
    
    context = {
        'form': form,
        'title': '技能作成',
    }
    return render(request, 'master/skill_form.html', context)


@login_required
@permission_required('master.change_skill', raise_exception=True)
def skill_update(request, pk):
    """技能更新"""
    skill = get_object_or_404(Skill, pk=pk)
    
    # カテゴリか技能かによってフォームを切り替え
    if skill.is_category:
        form_class = SkillCategoryForm
        template_name = 'master/skill_category_form.html'
        title = 'カテゴリ編集'
    else:
        form_class = SkillForm
        template_name = 'master/skill_form.html'
        title = '技能編集'
    
    if request.method == 'POST':
        form = form_class(request.POST, instance=skill)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.updated_by = request.user
            skill.save()
            messages.success(request, f'「{skill.name}」を更新しました。')
            return redirect('master:skill_detail', pk=skill.pk)
    else:
        form = form_class(instance=skill)
    
    context = {
        'form': form,
        'skill': skill,
        'title': title,
    }
    return render(request, template_name, context)


@login_required
@permission_required('master.delete_skill', raise_exception=True)
def skill_delete(request, pk):
    """技能削除"""
    skill = get_object_or_404(Skill, pk=pk)
    
    if request.method == 'POST':
        skill_name = skill.name
        skill.delete()
        messages.success(request, f'技能「{skill_name}」を削除しました。')
        return redirect('master:skill_list')
    
    context = {
        'skill': skill,
    }
    return render(request, 'master/skill_delete.html', context)

# 変更履歴ビュー
@login_required
@permission_required('master.view_qualification', raise_exception=True)
def qualification_change_history_list(request):
    """資格マスタ変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    
    # 資格マスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name='Qualification',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    return render(request, 'master/qualification_change_history_list.html', {
        'logs': logs_page,
        'title': '資格マスタ変更履歴'
    })


@login_required
@permission_required('master.view_skill', raise_exception=True)
def skill_change_history_list(request):
    """技能マスタ変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    
    # 技能マスタの変更履歴を取得
    logs = AppLog.objects.filter(
        model_name='Skill',
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    return render(request, 'master/skill_change_history_list.html', {
        'logs': logs_page,
        'title': '技能マスタ変更履歴'
    })