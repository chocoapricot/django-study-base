from django import forms
from allauth.account.forms import SignupForm, ResetPasswordForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSignupForm(SignupForm):
    last_name = forms.CharField(max_length=30, label='姓', required=True)
    first_name = forms.CharField(max_length=30, label='名', required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # フィールドラベルの設定
        if 'email' in self.fields:
            self.fields['email'].label = 'メールアドレス'
        if 'password1' in self.fields:
            self.fields['password1'].label = 'パスワード'
        if 'password2' in self.fields:
            self.fields['password2'].label = 'パスワード（確認）'
        
        # フィールドの順序を設定（存在するフィールドのみ）
        available_fields = list(self.fields.keys())
        desired_order = ['email', 'last_name', 'first_name', 'password1', 'password2']
        field_order = [field for field in desired_order if field in available_fields]
        self.order_fields(field_order)

    def clean(self):
        cleaned_data = super().clean()
        # 利用規約の同意チェックをここで行う（必要に応じて）
        return cleaned_data

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
