from django import forms
from .models import MyUser

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

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pw2 = cleaned_data.get('password_confirm')
        if pw or pw2:
            if pw != pw2:
                self.add_error('password_confirm', 'パスワードが一致しません')
        return cleaned_data
