from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from .models import Staff, StaffGrade
from .forms import StaffGradeForm
from apps.master.models_staff import Grade
from datetime import datetime, timedelta

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

@login_required
@permission_required('staff.add_staffgrade', raise_exception=True)
def staff_grade_bulk_change(request):
    """スタッフ等級一括変更"""
    # スタッフ等級が設定されているスタッフを取得
    staff_list = Staff.objects.filter(grades__isnull=False).distinct().order_by('employee_no')

    # 等級マスタを取得
    grade_master = Grade.objects.filter(is_active=True).order_by('display_order', 'code')

    if request.method == 'POST':
        revision_date_str = request.POST.get('revision_date')
        if not revision_date_str:
            messages.error(request, '改定日は必須です。')
        else:
            try:
                revision_date = datetime.strptime(revision_date_str, '%Y-%m-%d').date()
                yesterday = revision_date - timedelta(days=1)

                changed_count = 0
                with transaction.atomic():
                    for staff in staff_list:
                        new_grade_code = request.POST.get(f'grade_{staff.pk}')
                        current_grade_obj = staff.get_current_grade()
                        current_grade_code = current_grade_obj.grade_code if current_grade_obj else None

                        if new_grade_code and new_grade_code != current_grade_code:
                            # 重複する期間のデータを処理
                            # 1. 改定日以降に開始するデータを削除（上書き）
                            StaffGrade.objects.filter(staff=staff, valid_from__gte=revision_date).delete()

                            # 2. 改定日を跨ぐ既存データの終了日を更新
                            StaffGrade.objects.filter(
                                staff=staff,
                                valid_from__lt=revision_date
                            ).filter(
                                Q(valid_to__gte=revision_date) | Q(valid_to__isnull=True)
                            ).update(valid_to=yesterday)

                            # 3. 新規登録
                            StaffGrade.objects.create(
                                staff=staff,
                                grade_code=new_grade_code,
                                valid_from=revision_date,
                                tenant_id=staff.tenant_id
                            )
                            changed_count += 1

                if changed_count > 0:
                    messages.success(request, f'{changed_count}名のスタッフ等級を一括変更しました。')
                else:
                    messages.info(request, '変更されたデータはありませんでした。')
                return redirect('staff:staff_grade_bulk_change')

            except ValueError:
                messages.error(request, '不正な日付形式です。')
            except Exception as e:
                messages.error(request, f'エラーが発生しました: {e}')

    from .utils import get_annotated_staff_queryset, annotate_staff_connection_info
    staff_list = get_annotated_staff_queryset(request.user).filter(grades__isnull=False).distinct().order_by('employee_no')
    annotate_staff_connection_info(staff_list)

    return render(request, 'staff/staff_grade_bulk_change.html', {
        'staff_list': staff_list,
        'grade_master': grade_master,
        'today': datetime.now().date(),
    })
