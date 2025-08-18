from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import StaffProfile, StaffProfileQualification, StaffProfileSkill
from .forms_profile import StaffProfileQualificationForm, StaffProfileSkillForm

@login_required
def profile_qualification_list(request):
    profile = get_object_or_404(StaffProfile, user=request.user)
    qualifications = profile.qualifications.all()
    return render(request, 'profile/profile_qualification_list.html', {
        'profile': profile,
        'qualifications': qualifications,
    })

@login_required
def profile_qualification_create(request):
    profile = get_object_or_404(StaffProfile, user=request.user)
    if request.method == 'POST':
        form = StaffProfileQualificationForm(request.POST, staff_profile=profile)
        if form.is_valid():
            qualification = form.save(commit=False)
            qualification.staff_profile = profile
            qualification.save()
            messages.success(request, '資格を追加しました。')
            return redirect('profile:qualification_list')
    else:
        form = StaffProfileQualificationForm(staff_profile=profile)
    return render(request, 'profile/profile_qualification_form.html', {
        'form': form,
        'profile': profile,
    })

@login_required
def profile_qualification_update(request, pk):
    profile = get_object_or_404(StaffProfile, user=request.user)
    qualification = get_object_or_404(StaffProfileQualification, pk=pk, staff_profile=profile)
    if request.method == 'POST':
        form = StaffProfileQualificationForm(request.POST, instance=qualification, staff_profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, '資格を更新しました。')
            return redirect('profile:qualification_list')
    else:
        form = StaffProfileQualificationForm(instance=qualification, staff_profile=profile)
    return render(request, 'profile/profile_qualification_form.html', {
        'form': form,
        'profile': profile,
        'qualification': qualification,
    })

@login_required
def profile_qualification_delete(request, pk):
    profile = get_object_or_404(StaffProfile, user=request.user)
    qualification = get_object_or_404(StaffProfileQualification, pk=pk, staff_profile=profile)
    if request.method == 'POST':
        qualification.delete()
        messages.success(request, '資格を削除しました。')
        return redirect('profile:qualification_list')
    return render(request, 'profile/profile_qualification_delete.html', {
        'profile': profile,
        'qualification': qualification,
    })

@login_required
def profile_skill_list(request):
    profile = get_object_or_404(StaffProfile, user=request.user)
    skills = profile.skills.all()
    return render(request, 'profile/profile_skill_list.html', {
        'profile': profile,
        'skills': skills,
    })

@login_required
def profile_skill_create(request):
    profile = get_object_or_404(StaffProfile, user=request.user)
    if request.method == 'POST':
        form = StaffProfileSkillForm(request.POST, staff_profile=profile)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.staff_profile = profile
            skill.save()
            messages.success(request, '技能を追加しました。')
            return redirect('profile:skill_list')
    else:
        form = StaffProfileSkillForm(staff_profile=profile)
    return render(request, 'profile/profile_skill_form.html', {
        'form': form,
        'profile': profile,
    })

@login_required
def profile_skill_update(request, pk):
    profile = get_object_or_404(StaffProfile, user=request.user)
    skill = get_object_or_404(StaffProfileSkill, pk=pk, staff_profile=profile)
    if request.method == 'POST':
        form = StaffProfileSkillForm(request.POST, instance=skill, staff_profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, '技能を更新しました。')
            return redirect('profile:skill_list')
    else:
        form = StaffProfileSkillForm(instance=skill, staff_profile=profile)
    return render(request, 'profile/profile_skill_form.html', {
        'form': form,
        'profile': profile,
        'skill': skill,
    })

@login_required
def profile_skill_delete(request, pk):
    profile = get_object_or_404(StaffProfile, user=request.user)
    skill = get_object_or_404(StaffProfileSkill, pk=pk, staff_profile=profile)
    if request.method == 'POST':
        skill.delete()
        messages.success(request, '技能を削除しました。')
        return redirect('profile:skill_list')
    return render(request, 'profile/profile_skill_delete.html', {
        'profile': profile,
        'skill': skill,
    })
