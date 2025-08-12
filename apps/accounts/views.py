from allauth.account.views import SignupView, PasswordResetView
from django.shortcuts import render
from .forms import CustomSignupForm, CustomResetPasswordForm

class CustomSignupView(SignupView):
    form_class = CustomSignupForm

class CustomPasswordResetView(PasswordResetView):
    """カスタムパスワードリセットビュー"""
    form_class = CustomResetPasswordForm
    template_name = 'account/password_reset.html'

def terms_of_service(request):
    """利用規約の閲覧専用ページ"""
    return render(request, 'account/terms_of_service.html')