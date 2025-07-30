from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        # まずallauthのデフォルトの保存処理を実行
        user = super().save_user(request, user, form, commit=False)

        # その後、カスタムフィールドとユーザー名を更新
        user.last_name = form.cleaned_data.get('last_name')
        user.first_name = form.cleaned_data.get('first_name')
        user.username = user.email  # メールアドレスをユーザー名に設定

        if commit:
            user.save()
        return user
