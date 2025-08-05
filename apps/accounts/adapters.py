from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from apps.system.logs.utils import log_mail
from allauth.account.models import EmailAddress
class CustomAccountAdapter(DefaultAccountAdapter):
    def is_login_by_code_enabled(self):
        """ログインコード機能を完全に無効化"""
        return False
    
    def can_send_login_code(self, request, user):
        """ログインコードの送信を無効化"""
        return False
    
    def should_send_login_code(self, request, user):
        """ログインコードの送信判定を無効化"""
        return False
    
    def pre_authenticate(self, request, **credentials):
        """認証前の処理でログインコード機能を回避"""
        return None
    
    def authenticate(self, request, **credentials):
        """通常の認証のみを使用"""
        return super().authenticate(request, **credentials)
    
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
    
    def send_mail(self, template_prefix, email, context):
        """メール送信時にログを記録"""
        try:
            # メール送信前にログを記録
            mail_type = 'general'
            if 'signup' in template_prefix:
                mail_type = 'signup'
            elif 'password_reset' in template_prefix:
                mail_type = 'password_reset'
            elif 'password_change' in template_prefix:
                mail_type = 'password_change'
            
            # メール内容を取得（render_mailはEmailMultiAlternativesオブジェクトを返す）
            msg = self.render_mail(template_prefix, email, context)
            subject = msg.subject
            body = msg.body
            
            # ログを記録
            mail_log = log_mail(
                to_email=email,
                subject=subject,
                body=body,
                mail_type=mail_type,
                recipient_user=context.get('user'),
                backend=getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'),
                status='pending'
            )
            
            # 実際のメール送信
            result = super().send_mail(template_prefix, email, context)
            
            # 送信成功時にログを更新
            from apps.system.logs.utils import update_mail_log_status
            update_mail_log_status(mail_log.id, 'sent')
            
            return result
            
        except Exception as e:
            # 送信失敗時にログを更新
            if 'mail_log' in locals():
                from apps.system.logs.utils import update_mail_log_status
                update_mail_log_status(mail_log.id, 'failed', error_message=str(e))
            raise
