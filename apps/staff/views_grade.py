from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import Staff, StaffGrade
from .forms import StaffGradeForm

@login_required
@permission_required('staff.add_staffgrade', raise_exception=True)
def staff_grade_create(request, staff_pk):
    staff = get_object_or_404(Staff, pk=staff_pk)
    if request.method == 'POST':
        form = StaffGradeForm(request.POST)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.staff = staff
            grade.save()
            messages.success(request, '等級を登録しました。')
            return redirect('staff:staff_detail', pk=staff.pk)
    else:
        from django.utils import timezone
        form = StaffGradeForm(initial={'valid_from': timezone.localdate()})
    
    return render(request, 'staff/staff_grade_form.html', {'form': form, 'staff': staff})
