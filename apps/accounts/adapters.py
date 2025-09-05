from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from apps.system.logs.utils import log_mail
from allauth.account.models import EmailAddress
from apps.master.models import MailTemplate
from django.template import Context, Template
from django.core.mail import send_mail

class MyAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        # まずallauthのデフォルトの保存処理を実行
        user = super().save_user(request, user, form, commit=False)

        # その後、カスタムフィールドとユーザー名を更新
        user.last_name = form.cleaned_data.get('last_name')
        user.first_name = form.cleaned_data.get('first_name')
        user.username = user.email  # メールアドレスをユーザー名に設定

        if commit:
            user.save()
            
            # アカウント作成時に接続申請があるかチェックして権限を付与
            from apps.connect.utils import check_and_grant_permissions_for_email
            check_and_grant_permissions_for_email(user.email)
            
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

            if mail_type == 'password_reset':
                try:
                    mail_template = MailTemplate.objects.get(template_key='password_reset_key')

                    # コンテキストにユーザー情報を追加
                    user = context.get('user')
                    if user:
                        context['user_name'] = user.get_full_name() or user.username

                    ctx = Context(context)
                    subject = Template(mail_template.subject).render(ctx)
                    body = Template(mail_template.body).render(ctx)

                except MailTemplate.DoesNotExist:
                    # テンプレートが見つからない場合はデフォルトの動作にフォールバック
                    return super().send_mail(template_prefix, email, context)
            else:
                # 他のメールタイプはデフォルトの動作
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
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            # 送信成功時にログを更新
            from apps.system.logs.utils import update_mail_log_status
            update_mail_log_status(mail_log.id, 'sent')
            
        except Exception as e:
            # 送信失敗時にログを更新
            if 'mail_log' in locals():
                from apps.system.logs.utils import update_mail_log_status
                update_mail_log_status(mail_log.id, 'failed', error_message=str(e))
            raise
