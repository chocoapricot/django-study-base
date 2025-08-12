
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import UserProfileForm
from apps.system.logs.models import AppLog

@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            obj = form.save(commit=False)
            pw = form.cleaned_data.get('password')
            if pw:
                obj.set_password(pw)
            obj.save()
            if pw:
                update_session_auth_hash(request, obj)
            messages.info(request, 'ユーザ情報を保存しました。')
            return redirect('useradmin:profile')
    else:
        form = UserProfileForm(instance=user)
    
    # AppLogからログイン履歴を取得（直近10件まで）
    login_history = AppLog.objects.filter(
        user=user,
        action='login'
    ).order_by('-timestamp')[:10]
    
    return render(request, 'account/profile.html', {
        'form': form,
        'login_history': login_history
    })
