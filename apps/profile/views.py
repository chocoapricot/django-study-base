from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.urls import reverse
from .models import StaffProfile, ProfileMynumber, StaffProfileInternational
from .forms import StaffProfileForm, ProfileMynumberForm, StaffProfileInternationalForm


@login_required
@permission_required('profile.view_staffprofile', raise_exception=True)
def profile_detail(request):
    """プロフィール詳細表示"""
    try:
        profile = StaffProfile.objects.get(user=request.user)
    except StaffProfile.DoesNotExist:
        profile = None
    
    context = {
        'profile': profile,
    }
    return render(request, 'profile/profile_detail.html', context)


@login_required
@permission_required('profile.add_staffprofile', raise_exception=True)
@permission_required('profile.change_staffprofile', raise_exception=True)
def profile_edit(request):
    """プロフィール編集"""
    try:
        profile = StaffProfile.objects.get(user=request.user)
        is_new = False
    except StaffProfile.DoesNotExist:
        profile = None
        is_new = True

    if request.method == 'POST':
        form = StaffProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.email = request.user.email
            profile.save()
            
            if is_new:
                messages.success(request, 'プロフィールを作成しました。')
            else:
                messages.success(request, 'プロフィールを更新しました。')
            
            return redirect('profile:detail')
    else:
        if profile is None:
            # 新規作成時はUserの姓・名を初期値にセット
            initial = {
                'name_last': request.user.last_name,
                'name_first': request.user.first_name,
            }
            form = StaffProfileForm(instance=profile, initial=initial)
        else:
            form = StaffProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
        'is_new': is_new,
        'user_email': request.user.email,
    }
    return render(request, 'profile/profile_form.html', context)


@login_required
@permission_required('profile.delete_staffprofile', raise_exception=True)
def profile_delete(request):
    """プロフィール削除確認"""
    profile = get_object_or_404(StaffProfile, user=request.user)
    
    if request.method == 'POST':
        profile.delete()
        messages.success(request, 'プロフィールを削除しました。')
        return redirect('profile:detail')
    
    context = {
        'profile': profile,
    }
    return render(request, 'profile/profile_delete.html', context)


@login_required
@permission_required('profile.view_profilemynumber', raise_exception=True)
def mynumber_detail(request):
    """マイナンバー詳細表示"""
    try:
        mynumber = ProfileMynumber.objects.get(user=request.user)
    except ProfileMynumber.DoesNotExist:
        mynumber = None
    
    context = {
        'mynumber': mynumber,
    }
    return render(request, 'profile/mynumber_detail.html', context)


@login_required
@permission_required('profile.add_profilemynumber', raise_exception=True)
@permission_required('profile.change_profilemynumber', raise_exception=True)
def mynumber_edit(request):
    """マイナンバー編集"""
    try:
        mynumber = ProfileMynumber.objects.get(user=request.user)
        is_new = False
    except ProfileMynumber.DoesNotExist:
        mynumber = None
        is_new = True

    if request.method == 'POST':
        form = ProfileMynumberForm(request.POST, instance=mynumber)
        if form.is_valid():
            mynumber = form.save(commit=False)
            mynumber.user = request.user
            mynumber.email = request.user.email
            mynumber.save()
            
            if is_new:
                messages.success(request, 'マイナンバーを登録しました。')
            else:
                messages.success(request, 'マイナンバーを更新しました。')
            
            return redirect('profile:mynumber_detail')
    else:
        form = ProfileMynumberForm(instance=mynumber)
    
    context = {
        'form': form,
        'mynumber': mynumber,
        'is_new': is_new,
        'user_email': request.user.email,
    }
    return render(request, 'profile/mynumber_form.html', context)


@login_required
@permission_required('profile.delete_profilemynumber', raise_exception=True)
def mynumber_delete(request):
    """マイナンバー削除確認"""
    mynumber = get_object_or_404(ProfileMynumber, user=request.user)
    
    if request.method == 'POST':
        mynumber.delete()
        messages.success(request, 'マイナンバーを削除しました。')
        return redirect('profile:mynumber_detail')
    
    context = {
        'mynumber': mynumber,
    }
    return render(request, 'profile/mynumber_delete.html', context)


@login_required
@permission_required('profile.add_staffprofileinternational', raise_exception=True)
@permission_required('profile.change_staffprofileinternational', raise_exception=True)
def international_edit(request):
    """外国籍情報登録・編集"""
    # スタッフプロフィールを取得
    try:
        staff_profile = StaffProfile.objects.get(user=request.user)
    except StaffProfile.DoesNotExist:
        messages.error(request, 'プロフィールを先に登録してください。')
        return redirect('profile:edit')

    # 既存の外国籍情報を確認
    try:
        international_profile = StaffProfileInternational.objects.get(staff_profile=staff_profile)
        is_new = False
    except StaffProfileInternational.DoesNotExist:
        international_profile = None
        is_new = True
    
    if request.method == 'POST':
        form = StaffProfileInternationalForm(request.POST, instance=international_profile)
        if form.is_valid():
            # 外国籍情報を保存
            international_profile = form.save(commit=False)
            international_profile.staff_profile = staff_profile
            international_profile.save()
            
            if is_new:
                messages.success(request, '外国籍情報を登録しました。')
            else:
                messages.success(request, '外国籍情報を更新しました。')
            
            return redirect('profile:international_detail')
    else:
        form = StaffProfileInternationalForm(instance=international_profile)
    
    context = {
        'form': form,
        'international_profile': international_profile,
        'is_new': is_new,
    }
    return render(request, 'profile/international_form.html', context)


@login_required
@permission_required('profile.view_staffprofileinternational', raise_exception=True)
def international_detail(request):
    """外国籍情報詳細表示"""
    # 外国籍情報を取得
    international = None
    try:
        staff_profile = StaffProfile.objects.get(user=request.user)
        try:
            international = StaffProfileInternational.objects.get(staff_profile=staff_profile)
        except StaffProfileInternational.DoesNotExist:
            pass
    except StaffProfile.DoesNotExist:
        pass
    
    context = {
        'international': international,
    }
    return render(request, 'profile/international_detail.html', context)


@login_required
@permission_required('profile.delete_staffprofileinternational', raise_exception=True)
def international_delete(request):
    """外国籍情報削除確認"""
    # 外国籍情報を取得
    try:
        staff_profile = StaffProfile.objects.get(user=request.user)
        international = get_object_or_404(StaffProfileInternational, staff_profile=staff_profile)
    except StaffProfile.DoesNotExist:
        messages.error(request, '外国籍情報が見つかりません。')
        return redirect('/')
    
    if request.method == 'POST':
        international.delete()
        messages.success(request, '外国籍情報を削除しました。')
        return redirect('profile:international_detail')
    
    context = {
        'international': international,
    }
    return render(request, 'profile/international_delete.html', context)