from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import MyTenantModel
from apps.common.constants import Constants, get_notification_type_choices

User = get_user_model()


class Notification(MyTenantModel):
    """
    ユーザーへの通知を管理するモデル。
    システムからユーザーへの各種通知（お知らせ、アラート等）を記録する。
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='対象ユーザー',
        related_name='notifications',
        help_text='通知を受け取るユーザー'
    )
    
    title = models.CharField(
        '通知タイトル',
        max_length=255,
        help_text='通知の見出し'
    )
    
    message = models.TextField(
        '通知メッセージ',
        help_text='通知の本文'
    )
    
    notification_type = models.CharField(
        '通知種別',
        max_length=20,
        choices=get_notification_type_choices(),
        default=Constants.NOTIFICATION_TYPE.GENERAL,
        help_text='通知の種類'
    )
    
    is_read = models.BooleanField(
        '既読フラグ',
        default=False,
        help_text='ユーザーが通知を読んだかどうか'
    )
    
    link_url = models.CharField(
        'リンクURL',
        max_length=500,
        blank=True,
        null=True,
        help_text='通知に関連するページへのリンク（オプション）'
    )
    
    read_at = models.DateTimeField(
        '既読日時',
        null=True,
        blank=True,
        help_text='ユーザーが通知を読んだ日時'
    )
    
    class Meta:
        db_table = 'apps_system_notification'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        read_status = '既読' if self.is_read else '未読'
        return f"{self.user.username} - {self.title} ({read_status})"
    
    @property
    def notification_type_display_name(self):
        """通知種別の表示名"""
        return dict(get_notification_type_choices()).get(self.notification_type, self.notification_type)
    
    def mark_as_read(self):
        """通知を既読にする"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
