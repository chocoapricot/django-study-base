from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Staff, StaffQualification, StaffSkill
from .forms_qualification import StaffQualificationForm, StaffSkillForm


# スタッフ資格管理
@login_required
@permission_required('staff.view_staffqualification', raise_exception=True)
def staff_qualification_list(request, staff_pk):
    """スタッフ資格一覧"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    qualifications = StaffQualification.objects.filter(staff=staff)
    
    context = {
        'staff': staff,
        'qualifications': qualifications,
    }
    return render(request, 'staff/staff_qualification_list.html', context)

@login_required
@permission_required('staff.add_staffqualification', raise_exception=True)
def staff_qualification_create(request, staff_pk):
    """スタッフ資格作成"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    
    if request.method == 'POST':
        form = StaffQualificationForm(request.POST, staff=staff)
        if form.is_valid():
            staff_qualification = form.save(commit=False)
            staff_qualification.staff = staff
            staff_qualification.created_by = request.user
            staff_qualification.updated_by = request.user
            staff_qualification.save()
            messages.success(request, f'資格「{staff_qualification.qualification.name}」を追加しました。')
            return redirect('staff:staff_qualification_list', staff_pk=staff.pk)
    else:
        form = StaffQualificationForm(staff=staff)
    
    context = {
        'form': form,
        'staff': staff,
        'title': '資格追加',
    }
    return render(request, 'staff/staff_qualification_form.html', context)


@login_required
@permission_required('staff.delete_staffqualification', raise_exception=True)
def staff_qualification_delete(request, pk):
    """スタッフ資格削除"""
    staff_qualification = get_object_or_404(StaffQualification, pk=pk)
    
    if request.method == 'POST':
        staff = staff_qualification.staff
        qualification_name = staff_qualification.qualification.name
        staff_qualification.delete()
        messages.success(request, f'資格「{qualification_name}」を削除しました。')
        return redirect('staff:staff_qualification_list', staff_pk=staff.pk)
    
    context = {
        'staff_qualification': staff_qualification,
        'staff': staff_qualification.staff,
    }
    return render(request, 'staff/staff_qualification_delete.html', context)


# スタッフ技能管理
@login_required
@permission_required('staff.view_staffskill', raise_exception=True)
def staff_skill_list(request, staff_pk):
    """スタッフ技能一覧"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    skills = StaffSkill.objects.filter(staff=staff)
    
    context = {
        'staff': staff,
        'skills': skills,
    }
    return render(request, 'staff/staff_skill_list.html', context)




@login_required
@permission_required('staff.add_staffskill', raise_exception=True)
def staff_skill_create(request, staff_pk):
    """スタッフ技能作成"""
    staff = get_object_or_404(Staff, pk=staff_pk)
    
    if request.method == 'POST':
        form = StaffSkillForm(request.POST, staff=staff)
        if form.is_valid():
            staff_skill = form.save(commit=False)
            staff_skill.staff = staff
            staff_skill.created_by = request.user
            staff_skill.updated_by = request.user
            staff_skill.save()
            messages.success(request, f'技能「{staff_skill.skill.name}」を追加しました。')
            return redirect('staff:staff_skill_list', staff_pk=staff.pk)
    else:
        form = StaffSkillForm(staff=staff)
    
    context = {
        'form': form,
        'staff': staff,
        'title': '技能追加',
    }
    return render(request, 'staff/staff_skill_form.html', context)



@login_required
@permission_required('staff.delete_staffskill', raise_exception=True)
def staff_skill_delete(request, pk):
    """スタッフ技能削除"""
    staff_skill = get_object_or_404(StaffSkill, pk=pk)
    
    if request.method == 'POST':
        staff = staff_skill.staff
        skill_name = staff_skill.skill.name
        staff_skill.delete()
        messages.success(request, f'技能「{skill_name}」を削除しました。')
        return redirect('staff:staff_skill_list', staff_pk=staff.pk)
    
    context = {
        'staff_skill': staff_skill,
        'staff': staff_skill.staff,
    }
    return render(request, 'staff/staff_skill_delete.html', context)