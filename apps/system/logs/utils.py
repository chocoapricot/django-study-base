from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import MailLog

User = get_user_model()

def log_mail(to_email, subject, body, mail_type='general', from_email=None, 
             recipient_user=None, status='pending', backend=None, message_id=None, 
             error_message=None):
    """
    メール送信ログを記録する関数
    
    Args:
        to_email (str): 受信者メールアドレス
        subject (str): 件名
        body (str): 本文
        mail_type (str): メール種別 ('signup', 'password_reset', 'password_change', 'general')
        from_email (str): 送信者メールアドレス
        recipient_user (User): 受信者ユーザー（特定できる場合）
        status (str): 送信状況 ('sent', 'failed', 'pending')
        backend (str): メールバックエンド
        message_id (str): メッセージID
        error_message (str): エラーメッセージ
    
    Returns:
        MailLog: 作成されたメールログインスタンス
    """
    # 受信者ユーザーを自動検索（指定されていない場合）
    if not recipient_user and to_email:
        try:
            recipient_user = User.objects.get(email__iexact=to_email)
        except User.DoesNotExist:
            recipient_user = None
    
    # デフォルトの送信者メールアドレス
    if not from_email:
        from django.conf import settings
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
    
    # デフォルトのバックエンド
    if not backend:
        backend = 'default'
    
    mail_log = MailLog.objects.create(
        from_email=from_email,
        to_email=to_email,
        recipient_user=recipient_user,
        mail_type=mail_type,
        subject=subject,
        body=body,
        status=status,
        sent_at=timezone.now() if status == 'sent' else None,
        backend=backend,
        message_id=message_id or '',
        error_message=error_message or ''
    )
    
    return mail_log

def update_mail_log_status(mail_log_id, status, error_message=None, message_id=None):
    """
    メール送信ログの状況を更新する関数
    
    Args:
        mail_log_id (int): メールログID
        status (str): 新しい送信状況
        error_message (str): エラーメッセージ（失敗時）
        message_id (str): メッセージID（成功時）
    
    Returns:
        MailLog: 更新されたメールログインスタンス
    """
    try:
        mail_log = MailLog.objects.get(id=mail_log_id)
        mail_log.status = status
        
        if status == 'sent':
            mail_log.sent_at = timezone.now()
            if message_id:
                mail_log.message_id = message_id
        elif status == 'failed':
            if error_message:
                mail_log.error_message = error_message
        
        mail_log.save()
        return mail_log
    except MailLog.DoesNotExist:
        return None

def get_user_mail_logs(user, mail_type=None, limit=None):
    """
    特定ユーザーのメール送信ログを取得する関数
    
    Args:
        user (User): ユーザー
        mail_type (str): メール種別でフィルタ（オプション）
        limit (int): 取得件数制限（オプション）
    
    Returns:
        QuerySet: メールログのクエリセット
    """
    queryset = MailLog.objects.filter(recipient_user=user)
    
    if mail_type:
        queryset = queryset.filter(mail_type=mail_type)
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset

def get_mail_logs_by_email(email, mail_type=None, limit=None):
    """
    メールアドレスでメール送信ログを取得する関数
    
    Args:
        email (str): メールアドレス
        mail_type (str): メール種別でフィルタ（オプション）
        limit (int): 取得件数制限（オプション）
    
    Returns:
        QuerySet: メールログのクエリセット
    """
    queryset = MailLog.objects.filter(to_email__iexact=email)
    
    if mail_type:
        queryset = queryset.filter(mail_type=mail_type)
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset