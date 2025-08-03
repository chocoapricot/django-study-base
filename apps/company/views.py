from django.shortcuts import render, redirect, get_object_or_404
from .models import Company
from .forms import CompanyForm
from django.contrib import messages

from django.contrib.auth.decorators import login_required

@login_required
def company_detail(request):
    company = Company.objects.first()
    if not company:
        # レコードが存在しない場合は新規作成
        company = Company.objects.create(name="新規会社") # 仮の会社名
        messages.info(request, '会社情報がまだ登録されていません。基本情報を入力してください。')
        return redirect('company_edit')

    return render(request, 'company/company_detail.html', {'company': company})

from django.contrib.auth.decorators import login_required

# ... (既存のコード)

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
