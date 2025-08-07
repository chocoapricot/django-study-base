from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Qualification, Skill
from .forms import QualificationForm, SkillForm


# 資格管理ビュー
@login_required
@permission_required('master.view_qualification', raise_exception=True)
def qualification_list(request):
    """資格一覧"""
    qualifications = Qualification.objects.all()
    
    # 検索機能
    search_query = request.GET.get('q', '')
    if search_query:
        qualifications = qualifications.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # カテゴリフィルタ
    category_filter = request.GET.get('category', '')
    if category_filter:
        qualifications = qualifications.filter(category=category_filter)
    
    # アクティブフィルタ
    is_active_filter = request.GET.get('is_active', '')
    if is_active_filter:
        qualifications = qualifications.filter(is_active=is_active_filter == 'true')
    
    # ページネーション
    paginator = Paginator(qualifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'is_active_filter': is_active_filter,
        'category_choices': Qualification.CATEGORY_CHOICES,
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
    
    if request.method == 'POST':
        form = QualificationForm(request.POST, instance=qualification)
        if form.is_valid():
            qualification = form.save(commit=False)
            qualification.updated_by = request.user
            qualification.save()
            messages.success(request, f'資格「{qualification.name}」を更新しました。')
            return redirect('master:qualification_detail', pk=qualification.pk)
    else:
        form = QualificationForm(instance=qualification)
    
    context = {
        'form': form,
        'qualification': qualification,
        'title': '資格編集',
    }
    return render(request, 'master/qualification_form.html', context)


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
    """技能一覧"""
    skills = Skill.objects.all()
    
    # 検索機能
    search_query = request.GET.get('q', '')
    if search_query:
        skills = skills.filter(
            Q(name__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # カテゴリフィルタ
    category_filter = request.GET.get('category', '')
    if category_filter:
        skills = skills.filter(category=category_filter)
    

    
    # アクティブフィルタ
    is_active_filter = request.GET.get('is_active', '')
    if is_active_filter:
        skills = skills.filter(is_active=is_active_filter == 'true')
    
    # ページネーション
    paginator = Paginator(skills, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # カテゴリ一覧を取得（フィルタ用）
    categories = Skill.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True).exclude(category='')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'is_active_filter': is_active_filter,
        'categories': categories,
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
    
    if request.method == 'POST':
        form = SkillForm(request.POST, instance=skill)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.updated_by = request.user
            skill.save()
            messages.success(request, f'技能「{skill.name}」を更新しました。')
            return redirect('master:skill_detail', pk=skill.pk)
    else:
        form = SkillForm(instance=skill)
    
    context = {
        'form': form,
        'skill': skill,
        'title': '技能編集',
    }
    return render(request, 'master/skill_form.html', context)


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