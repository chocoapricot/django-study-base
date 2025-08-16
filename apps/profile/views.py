from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import StaffProfile
from .forms import StaffProfileForm


@login_required
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
            profile.email = request.user.email  # ユーザーのメールアドレスを設定
            profile.save()
            
            if is_new:
                messages.success(request, 'プロフィールを作成しました。')
            else:
                messages.success(request, 'プロフィールを更新しました。')
            
            return redirect('profile:detail')
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