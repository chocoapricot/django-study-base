from django.shortcuts import render, redirect, get_object_or_404
from .models import Company, CompanyDepartment
from .forms import CompanyForm, CompanyDepartmentForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.system.logs.models import AppLog
from apps.system.logs.utils import log_view_detail, log_model_action
from django.db.models import Q

@login_required
def company_detail(request):
    company = Company.objects.first()
    if not company:
        # レコードが存在しない場合は新規作成
        company = Company.objects.create(name="新規会社") # 仮の会社名
        log_model_action(request.user, 'create', company)
        messages.info(request, '会社情報がまだ登録されていません。基本情報を入力してください。')
        return redirect('company:company_edit')

    # 詳細画面アクセスをログに記録
    log_view_detail(request.user, company)

    # 部署一覧も取得（最新5件）
    departments = CompanyDepartment.objects.all().order_by('-created_at')[:5]
    
    # 会社と部署の変更履歴を統合して取得（最新10件）
    company_logs = AppLog.objects.filter(
        model_name='Company', 
        object_id=str(company.pk), 
        action__in=['create', 'update']
    )
    
    department_logs = AppLog.objects.filter(
        model_name='CompanyDepartment',
        action__in=['create', 'update', 'delete']
    )
    
    # 両方のログを統合してタイムスタンプ順にソート
    change_logs = (company_logs | department_logs).order_by('-timestamp')[:5]
    change_logs_count = (company_logs | department_logs).count()
    
    return render(request, 'company/company_detail.html', {
        'company': company,
        'departments': departments,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count
    })

@login_required
def company_edit(request):
    company = Company.objects.first()
    if not company:
        # レコードが存在しない場合は新規作成
        company = Company.objects.create(name="新規会社") # 仮の会社名
        log_model_action(request.user, 'create', company)

    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            # 変更があったかどうかをチェック
            if form.has_changed():
                form.save()
                log_model_action(request.user, 'update', company)
                messages.success(request, '会社情報が更新されました。')
            else:
                messages.info(request, '変更はありませんでした。')
            return redirect('company:company_detail') # 更新後、参照ページにリダイレクト
    else:
        form = CompanyForm(instance=company)

    return render(request, 'company/company_edit.html', {'form': form})

# 部署管理のビュー
@login_required
def department_list(request):
    departments = CompanyDepartment.objects.all().order_by('name')
    return render(request, 'company/department_list.html', {'departments': departments})

@login_required
def department_detail(request, pk):
    department = get_object_or_404(CompanyDepartment, pk=pk)
    log_view_detail(request.user, department)
    return render(request, 'company/department_detail.html', {'department': department})

@login_required
def department_create(request):
    if request.method == 'POST':
        form = CompanyDepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            log_model_action(request.user, 'create', department)
            messages.success(request, '部署が作成されました。')
            return redirect('company:department_list')
    else:
        form = CompanyDepartmentForm()
    
    return render(request, 'company/department_form.html', {'form': form, 'title': '部署作成'})

@login_required
def department_edit(request, pk):
    department = get_object_or_404(CompanyDepartment, pk=pk)
    if request.method == 'POST':
        form = CompanyDepartmentForm(request.POST, instance=department)
        if form.is_valid():
            # 変更があったかどうかをチェック
            if form.has_changed():
                form.save()
                log_model_action(request.user, 'update', department)
                messages.success(request, '部署情報が更新されました。')
            else:
                messages.info(request, '変更はありませんでした。')
            return redirect('company:department_detail', pk=department.pk)
    else:
        form = CompanyDepartmentForm(instance=department)
    
    return render(request, 'company/department_form.html', {'form': form, 'department': department, 'title': '部署編集'})

@login_required
def department_delete(request, pk):
    department = get_object_or_404(CompanyDepartment, pk=pk)
    if request.method == 'POST':
        log_model_action(request.user, 'delete', department)
        department.delete()
        messages.success(request, '部署が削除されました。')
        return redirect('company:department_list')
    
    return render(request, 'company/department_confirm_delete.html', {'department': department})

@login_required
def change_history_list(request):
    """会社と部署の変更履歴一覧"""
    company = Company.objects.first()
    if not company:
        messages.error(request, '会社情報が見つかりません。')
        return redirect('company:company_detail')
    
    # 会社と部署の変更履歴を統合して取得
    company_logs = AppLog.objects.filter(
        model_name='Company', 
        object_id=str(company.pk), 
        action__in=['create', 'update']
    )
    
    department_logs = AppLog.objects.filter(
        model_name='CompanyDepartment',
        action__in=['create', 'update', 'delete']
    )
    
    # 両方のログを統合してタイムスタンプ順にソート
    change_logs = (company_logs | department_logs).order_by('-timestamp')
    
    return render(request, 'company/change_history_list.html', {
        'change_logs': change_logs,
        'company': company
    })
