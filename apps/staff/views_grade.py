from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Staff, StaffGrade
from .forms import StaffGradeForm

@login_required
@permission_required('staff.view_staffgrade', raise_exception=True)
def staff_grade_list(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    grades = StaffGrade.objects.filter(staff=staff).order_by('-valid_from')
    return render(request, 'staff/staff_grade_list.html', {
        'staff': staff,
        'grades': grades,
    })

@login_required
@permission_required('staff.add_staffgrade', raise_exception=True)
def staff_grade_create(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        form = StaffGradeForm(request.POST)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.staff = staff
            try:
                grade.save()
                messages.success(request, '等級を登録しました。')
                return redirect('staff:staff_detail', pk=staff.pk)
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, msgs in e.message_dict.items():
                        for msg in msgs:
                            form.add_error(field, msg)
                else:
                    for msg in e.messages:
                        form.add_error(None, msg)
    else:
        from django.utils import timezone
        form = StaffGradeForm(initial={'valid_from': timezone.localdate()})
    
    grades = StaffGrade.objects.filter(staff=staff).order_by('-valid_from')
    return render(request, 'staff/staff_grade_form.html', {
        'form': form, 
        'staff': staff,
        'grades': grades,
    })

@login_required
@permission_required('staff.change_staffgrade', raise_exception=True)
def staff_grade_update(request, pk):
    grade = get_object_or_404(StaffGrade, pk=pk)
    staff = grade.staff
    if request.method == 'POST':
        form = StaffGradeForm(request.POST, instance=grade)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '等級を更新しました。')
                return redirect('staff:staff_detail', pk=staff.pk)
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, msgs in e.message_dict.items():
                        for msg in msgs:
                            form.add_error(field, msg)
                else:
                    for msg in e.messages:
                        form.add_error(None, msg)
    else:
        form = StaffGradeForm(instance=grade)
    
    grades = StaffGrade.objects.filter(staff=staff).order_by('-valid_from')
    return render(request, 'staff/staff_grade_form.html', {
        'form': form, 
        'staff': staff, 
        'grade': grade,
        'grades': grades,
    })

@login_required
@permission_required('staff.delete_staffgrade', raise_exception=True)
def staff_grade_delete(request, pk):
    grade = get_object_or_404(StaffGrade, pk=pk)
    staff = grade.staff
    if request.method == 'POST':
        grade.delete()
        messages.success(request, '等級を削除しました。')
        return redirect('staff:staff_detail', pk=staff.pk)
    
    return render(request, 'staff/staff_grade_confirm_delete.html', {'grade': grade, 'staff': staff})
