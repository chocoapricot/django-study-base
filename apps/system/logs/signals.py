from django.dispatch import receiver
from django.contrib.auth import get_user_model
from allauth.account.signals import email_confirmed, user_signed_up
from .utils import log_mail

User = get_user_model()

@receiver(user_signed_up)
def log_signup_email(sender, request, user, **kwargs):
    """サインアップ時のメール送信をログに記録"""
    if user.email:
        # サインアップ確認メールのログを記録
        # 実際のメール送信はallauthが行うため、ここでは予備ログとして記録
        log_mail(
            to_email=user.email,
            subject='アカウント確認のお願い',  # 実際の件名は後で更新される
            body='サインアップ確認メール',  # 実際の本文は後で更新される
            mail_type='signup',
            recipient_user=user,
            status='pending'
        )

@receiver(email_confirmed)
def log_email_confirmation(sender, request, email_address, **kwargs):
    """メール確認完了時のログ"""
    # 確認完了の記録（必要に応じて）
    pass