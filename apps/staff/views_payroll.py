from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import Staff, StaffPayroll
from .forms_payroll import StaffPayrollForm

@login_required
@permission_required('staff.view_staffpayroll', raise_exception=True)
def staff_payroll_detail(request, staff_pk):
    """スタッフの給与情報詳細表示"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    try:
        payroll = StaffPayroll.objects.get(staff=staff)
    except StaffPayroll.DoesNotExist:
        # 未登録の場合は登録画面へリダイレクト
        return redirect('staff:staff_payroll_create', staff_pk=staff.pk)
    
    context = {
        'staff': staff,
        'payroll': payroll,
    }
    return render(request, 'staff/staff_payroll_detail.html', context)

@login_required
@permission_required('staff.add_staffpayroll', raise_exception=True)
def staff_payroll_create(request, staff_pk):
    """スタッフの給与情報登録"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    # 既に登録済みの場合は編集画面へリダイレクト
    if hasattr(staff, 'payroll'):
        return redirect('staff:staff_payroll_edit', staff_pk=staff.pk)
    
    if request.method == 'POST':
        form = StaffPayrollForm(request.POST)
        if form.is_valid():
            payroll = form.save(commit=False)
            payroll.staff = staff
            payroll.save()
            messages.success(request, '給与情報を登録しました。')
            return redirect('staff:staff_payroll_detail', staff_pk=staff.pk)
    else:
        form = StaffPayrollForm()
    
    context = {
        'form': form,
        'staff': staff,
        'is_new': True,
    }
    return render(request, 'staff/staff_payroll_form.html', context)

@login_required
@permission_required('staff.change_staffpayroll', raise_exception=True)
def staff_payroll_edit(request, staff_pk):
    """スタッフの給与情報編集"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    payroll = get_object_or_404(StaffPayroll, staff=staff)
    
    if request.method == 'POST':
        form = StaffPayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            form.save()
            messages.success(request, '給与情報を更新しました。')
            return redirect('staff:staff_payroll_detail', staff_pk=staff.pk)
    else:
        form = StaffPayrollForm(instance=payroll)
    
    context = {
        'form': form,
        'staff': staff,
        'is_new': False,
    }
    return render(request, 'staff/staff_payroll_form.html', context)

@login_required
@permission_required('staff.delete_staffpayroll', raise_exception=True)
def staff_payroll_delete(request, staff_pk):
    """スタッフの給与情報削除"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    payroll = get_object_or_404(StaffPayroll, staff=staff)
    
    if request.method == 'POST':
        payroll.delete()
        messages.success(request, '給与情報を削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)
    
    context = {
        'staff': staff,
        'payroll': payroll,
    }
    return render(request, 'staff/staff_payroll_confirm_delete.html', context)
