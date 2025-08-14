from django import forms
from allauth.account.forms import SignupForm, ResetPasswordForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import MyUser

User = get_user_model()

class MySignupForm(SignupForm):
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
        user = super(MySignupForm, self).save(request)
        user.last_name = self.cleaned_data['last_name']
        user.first_name = self.cleaned_data['first_name']
        user.save()
        return user

class MyResetPasswordForm(ResetPasswordForm):
    """カスタムパスワードリセットフォーム"""
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # メールアドレスが登録されているかチェック
            users = User.objects.filter(email__iexact=email)
            if not users.exists():
                # セキュリティのため、エラーメッセージは表示せずに空のユーザーリストを設定
                self.users = User.objects.none()
            else:
                # allauthが期待するusers属性を設定
                self.users = users
        return email
    
    def save(self, request, **kwargs):
        # ユーザーが存在しない場合はメールを送信しない
        if hasattr(self, 'users') and not self.users.exists():
            return
        return super().save(request, **kwargs)

class UserProfileForm(forms.ModelForm):
    password = forms.CharField(
        label='新しいパスワード',
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}),
        required=False
    )
    password_confirm = forms.CharField(
        label='新しいパスワード（確認）',
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}),
        required=False
    )

    class Meta:
        model = MyUser
        fields = ['email', 'first_name', 'last_name', 'phone_number']  # usernameを除外
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # メールアドレス、姓と名を必須にする
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].label = 'メールアドレス'
        self.fields['first_name'].label = '名'
        self.fields['last_name'].label = '姓'

    def clean_email(self):
        """メールアドレスの重複チェック"""
        email = self.cleaned_data.get('email')
        if email:
            # 他のユーザーが同じメールアドレスを使用していないかチェック
            existing_user = MyUser.objects.filter(email=email).exclude(pk=self.instance.pk).first()
            if existing_user:
                raise forms.ValidationError('このメールアドレスは既に他のユーザーによって使用されています。')
        return email

    def clean_password(self):
        """パスワードのバリデーション"""
        password = self.cleaned_data.get('password')
        if password:
            try:
                # Djangoのパスワードバリデーターを使用
                validate_password(password, self.instance)
            except ValidationError as error:
                raise forms.ValidationError(error)
        return password

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pw2 = cleaned_data.get('password_confirm')
        if pw or pw2:
            if pw != pw2:
                self.add_error('password_confirm', 'パスワードが一致しません')
        return cleaned_data
