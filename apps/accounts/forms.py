from django import forms
from allauth.account.forms import SignupForm, ResetPasswordForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSignupForm(SignupForm):
    last_name = forms.CharField(max_length=30, label='姓')
    first_name = forms.CharField(max_length=30, label='名')

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.last_name = self.cleaned_data['last_name']
        user.first_name = self.cleaned_data['first_name']
        user.save()
        return user

class CustomResetPasswordForm(ResetPasswordForm):
    """カスタムパスワードリセットフォーム"""
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # メールアドレスが登録されているかチェック
            users = User.objects.filter(email__iexact=email)
            if not users.exists():
                raise forms.ValidationError(
                    "このメールアドレスは登録されていません。"
                )
            # allauthが期待するusers属性を設定
            self.users = users
        return email
