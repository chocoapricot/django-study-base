from allauth.account.views import SignupView, PasswordResetView
from django.shortcuts import render
from .forms import MySignupForm, MyResetPasswordForm

class MySignupView(SignupView):
    form_class = MySignupForm

class MyPasswordResetView(PasswordResetView):
    """カスタムパスワードリセットビュー"""
    form_class = MyResetPasswordForm
    template_name = 'account/password_reset.html'

def terms_of_service(request):
    """利用規約の閲覧専用ページ"""
    return render(request, 'account/terms_of_service.html')