from allauth.account.views import SignupView, PasswordResetView
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import MySignupForm, MyResetPasswordForm, UserProfileForm
from apps.system.logs.models import AppLog

class MySignupView(SignupView):
    form_class = MySignupForm

class MyPasswordResetView(PasswordResetView):
    """カスタムパスワードリセットビュー"""
    form_class = MyResetPasswordForm
    template_name = 'account/password_reset.html'

def terms_of_service(request):
    """利用規約の閲覧専用ページ"""
    return render(request, 'account/terms_of_service.html')

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
            messages.success(request, 'プロフィールを更新しました。')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)
    
   # AppLogからログイン履歴を取得（直近20件まで）
    login_history = AppLog.objects.filter(
        user=user,
        action__in=['login', 'login_failed']
    ).order_by('-timestamp')[:20]
    
    return render(request, 'account/profile.html', {
        'form': form,
        'login_history': login_history
    })