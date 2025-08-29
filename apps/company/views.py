from django.shortcuts import render, redirect, get_object_or_404
from .models import Company, CompanyDepartment, CompanyUser
from .forms import CompanyForm, CompanyDepartmentForm, CompanyUserForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from apps.system.logs.models import AppLog
from apps.system.logs.utils import log_view_detail, log_model_action
from django.db.models import Q

@login_required
@permission_required('company.view_company', raise_exception=True)
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

    # 部署一覧も取得（表示順で最新5件）
    departments = CompanyDepartment.objects.all().order_by('display_order', 'name')[:5]

    # 担当者一覧も取得
    company_users = CompanyUser.objects.filter(company=company)

    # 会社、部署、担当者の変更履歴を統合して取得
    company_logs = AppLog.objects.filter(
        model_name='Company',
        object_id=str(company.pk),
        action__in=['create', 'update']
    )
    department_logs = AppLog.objects.filter(
        model_name='CompanyDepartment',
        action__in=['create', 'update', 'delete']
    )
    company_user_ids = [str(user.pk) for user in company_users]
    company_user_logs = AppLog.objects.filter(
        model_name='CompanyUser',
        object_id__in=company_user_ids,
        action__in=['create', 'update', 'delete']
    )
    
    # 全てのログを統合してタイムスタンプ順にソート
    all_logs = (company_logs | department_logs | company_user_logs)
    change_logs = all_logs.order_by('-timestamp')[:5]
    change_logs_count = all_logs.count()
    
    return render(request, 'company/company_detail.html', {
        'company': company,
        'departments': departments,
        'company_users': company_users,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count
    })

@login_required
@permission_required('company.change_company', raise_exception=True)
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
@permission_required('company.view_companydepartment', raise_exception=True)
def department_detail(request, pk):
    department = get_object_or_404(CompanyDepartment, pk=pk)
    log_view_detail(request.user, department)
    company = Company.objects.first()
    
    # 全部署一覧を取得
    departments = CompanyDepartment.objects.all().order_by('display_order', 'name')
    
    return render(request, 'company/company_department_detail.html', {
        'department': department,
        'departments': departments,
        'current_department': department,
        'company': company,
    })

@login_required
@permission_required('company.add_companydepartment', raise_exception=True)
def department_create(request):
    company = Company.objects.first()
    if request.method == 'POST':
        form = CompanyDepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            log_model_action(request.user, 'create', department)
            messages.success(request, '部署が作成されました。')
            return redirect('company:company_detail')
    else:
        form = CompanyDepartmentForm()
    
    departments = CompanyDepartment.objects.all().order_by('display_order', 'name')

    return render(request, 'company/company_department_form.html', {
        'form': form,
        'title': '部署作成',
        'departments': departments,
        'company': company,
    })

@login_required
@permission_required('company.change_companydepartment', raise_exception=True)
def department_edit(request, pk):
    department = get_object_or_404(CompanyDepartment, pk=pk)
    company = Company.objects.first()
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
    
    # 全部署一覧を取得
    departments = CompanyDepartment.objects.all().order_by('display_order', 'name')
    
    return render(request, 'company/company_department_form.html', {
        'form': form, 
        'department': department, 
        'title': '部署編集',
        'departments': departments,
        'current_department': department,
        'company': company,
    })

@login_required
@permission_required('company.delete_companydepartment', raise_exception=True)
def department_delete(request, pk):
    department = get_object_or_404(CompanyDepartment, pk=pk)
    company = Company.objects.first()
    if request.method == 'POST':
        log_model_action(request.user, 'delete', department)
        department.delete()
        messages.success(request, '部署が削除されました。')
        return redirect('company:company_detail')
    
    return render(request, 'company/company_department_confirm_delete.html', {
        'department': department,
        'company': company,
    })

@login_required
@permission_required('company.view_company', raise_exception=True)
def change_history_list(request):
    """会社、部署、担当者の変更履歴一覧"""
    company = Company.objects.first()
    if not company:
        messages.error(request, '会社情報が見つかりません。')
        return redirect('company:company_detail')

    # 会社、部署、担当者の変更履歴を統合して取得
    company_logs = AppLog.objects.filter(
        model_name='Company',
        object_id=str(company.pk),
        action__in=['create', 'update']
    )
    department_logs = AppLog.objects.filter(
        model_name='CompanyDepartment',
        action__in=['create', 'update', 'delete']
    )
    
    company_users = CompanyUser.objects.filter(company=company)
    company_user_ids = [str(user.pk) for user in company_users]
    company_user_logs = AppLog.objects.filter(
        model_name='CompanyUser',
        object_id__in=company_user_ids,
        action__in=['create', 'update', 'delete']
    )

    # 全てのログを統合してタイムスタンプ順にソート
    change_logs = (company_logs | department_logs | company_user_logs).order_by('-timestamp')

    return render(request, 'company/company_change_history_list.html', {
        'change_logs': change_logs,
        'company': company
    })


# Company User CRUD
@login_required
@permission_required('company.add_companyuser', raise_exception=True)
def company_user_create(request):
    company = Company.objects.first()
    if not company:
        messages.error(request, '会社情報が見つかりません。')
        return redirect('company:company_detail')

    if request.method == 'POST':
        form = CompanyUserForm(request.POST)
        if form.is_valid():
            company_user = form.save(commit=False)
            company_user.company = company
            company_user.save()
            log_model_action(request.user, 'create', company_user)
            messages.success(request, '担当者を作成しました。')
            return redirect('company:company_detail')
    else:
        form = CompanyUserForm()

    company_users = CompanyUser.objects.filter(company=company)
    return render(request, 'company/company_user_form.html', {
        'form': form,
        'company': company,
        'title': '担当者作成',
        'company_users': company_users
    })

@login_required
@permission_required('company.change_companyuser', raise_exception=True)
def company_user_edit(request, pk):
    company_user = get_object_or_404(CompanyUser, pk=pk)
    company = company_user.company

    if request.method == 'POST':
        form = CompanyUserForm(request.POST, instance=company_user)
        if form.is_valid():
            form.save()
            log_model_action(request.user, 'update', company_user)
            messages.success(request, '担当者情報を更新しました。')
            return redirect('company:company_detail')
    else:
        form = CompanyUserForm(instance=company_user)

    company_users = CompanyUser.objects.filter(company=company)
    return render(request, 'company/company_user_form.html', {
        'form': form,
        'company': company,
        'title': '担当者編集',
        'company_users': company_users
    })

@login_required
@permission_required('company.delete_companyuser', raise_exception=True)
def company_user_delete(request, pk):
    company_user = get_object_or_404(CompanyUser, pk=pk)
    if request.method == 'POST':
        log_model_action(request.user, 'delete', company_user)
        company_user.delete()
        messages.success(request, '担当者を削除しました。')
        return redirect('company:company_detail')

    return render(request, 'company/company_user_confirm_delete.html', {
        'company_user': company_user,
        'company': company_user.company,
    })


@login_required
@permission_required('company.view_companyuser', raise_exception=True)
def company_user_detail(request, pk):
    company_user = get_object_or_404(CompanyUser, pk=pk)
    log_view_detail(request.user, company_user)
    company_users = CompanyUser.objects.filter(company=company_user.company)
    return render(request, 'company/company_user_detail.html', {
        'object': company_user,
        'company_users': company_users,
        'company': company_user.company,
    })
