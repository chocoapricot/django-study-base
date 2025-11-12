# -*- coding: utf-8 -*-
"""
ログ関連のユーティリティ関数
"""

from .models import AppLog, MailLog


from apps.common.constants import Constants


def log_mail(to_email, subject, body, mail_type=None, recipient_user=None, 
             from_email=None, status=None, backend=None, message_id=None, error_message=None):
    """
    メール送信ログを記録
    
    Args:
        to_email: 受信者メールアドレス
        subject: 件名
        body: 本文
        mail_type: メール種別
        recipient_user: 受信者ユーザー（オプション）
        from_email: 送信者メールアドレス（オプション）
        status: 送信状況
        backend: メールバックエンド（オプション）
        message_id: メッセージID（オプション）
        error_message: エラーメッセージ（オプション）
    
    Returns:
        MailLog: 作成されたMailLogインスタンス
    """
    from django.conf import settings
    
    if not from_email:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
    
    if mail_type is None:
        mail_type = Constants.MAIL_TYPE.GENERAL
    
    if status is None:
        status = Constants.MAIL_STATUS.PENDING
    
    return MailLog.objects.create(
        to_email=to_email,
        subject=subject,
        body=body,
        mail_type=mail_type,
        recipient_user=recipient_user,
        from_email=from_email,
        status=status,
        backend=backend,
        message_id=message_id,
        error_message=error_message
    )


def update_mail_log_status(mail_log_id, status, error_message=None, message_id=None):
    """
    メール送信ログのステータスを更新
    
    Args:
        mail_log_id: MailLogのID
        status: 新しいステータス ('sent', 'failed', 'pending')
        error_message: エラーメッセージ（オプション）
        message_id: メッセージID（オプション）
    """
    from django.utils import timezone
    
    try:
        mail_log = MailLog.objects.get(id=mail_log_id)
        mail_log.status = status
        
        if status == Constants.MAIL_STATUS.SENT:
            mail_log.sent_at = timezone.now()
        
        if error_message:
            mail_log.error_message = error_message
            
        if message_id:
            mail_log.message_id = message_id
            
        mail_log.save()
        return mail_log
        
    except MailLog.DoesNotExist:
        pass  # ログが見つからない場合は何もしない


def log_view_detail(user, instance):
    """
    詳細画面アクセス時のログ記録
    
    Args:
        user: ログインユーザー
        instance: 閲覧対象のモデルインスタンス
    """
    AppLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=Constants.APP_ACTION.VIEW,
        model_name=instance.__class__.__name__,
        object_id=str(getattr(instance, 'pk', '')),
        object_repr=f"{instance} の詳細画面を閲覧"
    )


def log_model_action(user, action, instance, version=None):
    """
    モデル操作のログ記録
    
    Args:
        user: 操作ユーザー
        action: 操作種別 ('create', 'update', 'delete', 'login', 'logout', 'view')
        instance: 操作対象のモデルインスタンス
        version: バージョン番号（オプション）
    """
    AppLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(getattr(instance, 'pk', '')),
        object_repr=str(instance),
        version=version
    )


def log_user_action(user, action, description):
    """
    ユーザー操作のログ記録
    
    Args:
        user: 操作ユーザー
        action: 操作種別
        description: 操作の説明
    """
    AppLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name='User',
        object_id=str(getattr(user, 'pk', '')) if user else '',
        object_repr=description
    )