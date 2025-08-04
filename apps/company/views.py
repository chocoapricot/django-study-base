from django.shortcuts import render, redirect, get_object_or_404
from .models import Company, CompanyDepartment
from .forms import CompanyForm, CompanyDepartmentForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def company_detail(request):
    company = Company.objects.first()
    if not company:
        # レコードが存在しない場合は新規作成
        company = Company.objects.create(name="新規会社") # 仮の会社名
        messages.info(request, '会社情報がまだ登録されていません。基本情報を入力してください。')
        return redirect('company:company_edit')

    return render(request, 'company/company_detail.html', {'company': company})

@login_required
def company_edit(request):
    company = Company.objects.first()
    if not company:
        # レコードが存在しない場合は新規作成
        company = Company.objects.create(name="新規会社") # 仮の会社名

    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, '会社情報が更新されました。')
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
    return render(request, 'company/department_detail.html', {'department': department})

@login_required
def department_create(request):
    if request.method == 'POST':
        form = CompanyDepartmentForm(request.POST)
        if form.is_valid():
            form.save()
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
            form.save()
            messages.success(request, '部署情報が更新されました。')
            return redirect('company:department_detail', pk=department.pk)
    else:
        form = CompanyDepartmentForm(instance=department)
    
    return render(request, 'company/department_form.html', {'form': form, 'department': department, 'title': '部署編集'})

@login_required
def department_delete(request, pk):
    department = get_object_or_404(CompanyDepartment, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, '部署が削除されました。')
        return redirect('company:department_list')
    
    return render(request, 'company/department_confirm_delete.html', {'department': department})
