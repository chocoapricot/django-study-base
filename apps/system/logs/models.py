from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import MyModel

User = get_user_model()

class MailLog(MyModel):
    """
    システムから送信されるメールのログを管理するモデル。
    送信日時、宛先、件名、本文、送信ステータスなどを記録する。
    """
    
    MAIL_TYPE_CHOICES = [
        ('signup', 'サインアップ確認'),
        ('password_reset', 'パスワードリセット'),
        ('password_change', 'パスワード変更通知'),
        ('general', '一般'),
    ]
    
    STATUS_CHOICES = [
        ('sent', '送信成功'),
        ('failed', '送信失敗'),
        ('pending', '送信待ち'),
    ]
    
    # 送信者情報
    from_email = models.EmailField('送信者メールアドレス', max_length=255)
    
    # 受信者情報
    to_email = models.EmailField('受信者メールアドレス', max_length=255)
    recipient_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='受信者ユーザー',
        help_text='ユーザーが特定できる場合のみ'
    )
    
    # メール内容
    mail_type = models.CharField(
        'メール種別', 
        max_length=20, 
        choices=MAIL_TYPE_CHOICES, 
        default='general'
    )
    subject = models.CharField('件名', max_length=255)
    body = models.TextField('本文')
    
    # 送信状況
    status = models.CharField(
        '送信状況', 
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    sent_at = models.DateTimeField('送信日時', null=True, blank=True)
    error_message = models.TextField('エラーメッセージ', blank=True, null=True)
    
    # 追加情報
    backend = models.CharField('メールバックエンド', max_length=100, blank=True, null=True)
    message_id = models.CharField('メッセージID', max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'apps_system_mail_log'
        verbose_name = 'メール送信ログ'
        verbose_name_plural = 'メール送信ログ'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['to_email']),
            models.Index(fields=['mail_type']),
            models.Index(fields=['status']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"{self.mail_type} - {self.to_email} ({self.status})"
    
    @property
    def is_successful(self):
        """送信成功かどうか"""
        return self.status == 'sent'
    
    @property
    def mail_type_display_name(self):
        """メール種別の表示名"""
        return dict(self.MAIL_TYPE_CHOICES).get(self.mail_type, self.mail_type)
    
    @property
    def status_display_name(self):
        """送信状況の表示名"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


# アプリケーション操作ログ
class AppLog(models.Model):
    """
    アプリケーション内での主要な操作（作成、更新、削除、ログインなど）のログを管理するモデル。
    誰が、いつ、どのオブジェクトに対して何をしたかを記録する。
    """
    
    ACTION_CHOICES = [
        ('create', '作成'),
        ('update', '編集'),
        ('delete', '削除'),
        ('login', 'ログイン'),
        ('logout', 'ログアウト'),
        ('view', '閲覧'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='ユーザー',
        related_name='system_app_logs'
    )
    action = models.CharField('操作', max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField('モデル名', max_length=100)
    object_id = models.CharField('オブジェクトID', max_length=100)
    object_repr = models.TextField('オブジェクト表現')
    version = models.IntegerField('バージョン', null=True, blank=True)
    timestamp = models.DateTimeField('タイムスタンプ', auto_now_add=True)

    class Meta:
        db_table = 'apps_system_app_log'
        verbose_name = 'アプリケーション操作ログ'
        verbose_name_plural = 'アプリケーション操作ログ'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['model_name']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.timestamp} {self.user} {self.action} {self.model_name} {self.object_repr}"

    @property
    def action_display_name(self):
        """操作の表示名"""
        return dict(self.ACTION_CHOICES).get(self.action, self.action)
