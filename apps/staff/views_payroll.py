from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import Staff, StaffPayroll
from .forms_payroll import StaffPayrollForm

@login_required
@permission_required('staff.view_staffpayroll', raise_exception=True)
def staff_payroll_detail(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    payroll = get_object_or_404(StaffPayroll, staff=staff)
    return render(request, 'staff/staff_payroll_detail.html', {'staff': staff, 'payroll': payroll})

@login_required
@permission_required('staff.add_staffpayroll', raise_exception=True)
def staff_payroll_create(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    if hasattr(staff, 'payroll'):
        return redirect('staff:staff_payroll_edit', staff_id=staff.id)
    if request.method == 'POST':
        form = StaffPayrollForm(request.POST)
        if form.is_valid():
            payroll = form.save(commit=False)
            payroll.staff = staff
            payroll.save()
            messages.success(request, '給与情報を登録しました。')
            return redirect('staff:staff_detail', pk=staff.id)
    else:
        form = StaffPayrollForm()
    return render(request, 'staff/staff_payroll_form.html', {'form': form, 'staff': staff})

@login_required
@permission_required('staff.change_staffpayroll', raise_exception=True)
def staff_payroll_edit(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    payroll = get_object_or_404(StaffPayroll, staff=staff)
    if request.method == 'POST':
        form = StaffPayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            form.save()
            messages.success(request, '給与情報を更新しました。')
            return redirect('staff:staff_detail', pk=staff.id)
    else:
        form = StaffPayrollForm(instance=payroll)
    return render(request, 'staff/staff_payroll_form.html', {'form': form, 'staff': staff})

@login_required
@permission_required('staff.delete_staffpayroll', raise_exception=True)
def staff_payroll_delete(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    payroll = get_object_or_404(StaffPayroll, staff=staff)
    if request.method == 'POST':
        payroll.delete()
        messages.success(request, '給与情報を削除しました。')
        return redirect('staff:staff_detail', pk=staff.id)
    return render(request, 'staff/staff_payroll_confirm_delete.html', {'staff': staff, 'payroll': payroll})
