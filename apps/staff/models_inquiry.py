from django.db import models
from django.contrib.auth import get_user_model
from ..common.models import MyModel

User = get_user_model()

class StaffInquiry(MyModel):
    """
    スタッフからの問い合わせを管理するモデル。
    """
    STATUS_CHOICES = [
        ('open', '受付中'),
        ('completed', '完了'),
    ]
    INQUIRY_FROM_CHOICES = [
        ('staff', 'スタッフ'),
        ('company', '会社'),
    ]
    inquiry_from = models.CharField(
        '問い合わせ元',
        max_length=10,
        choices=INQUIRY_FROM_CHOICES,
        default='staff',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='staff_inquiries',
        verbose_name='ユーザー'
    )
    corporate_number = models.CharField(
        'あて先法人番号',
        max_length=13,
        help_text='接続承認済みクライアントの法人番号'
    )
    subject = models.CharField(
        '件名',
        max_length=200
    )
    content = models.TextField(
        '内容'
    )
    attachment = models.FileField(
        '添付ファイル',
        upload_to='inquiry_attachments/%Y/%m/%d/',
        null=True,
        blank=True
    )
    status = models.CharField(
        'ステータス',
        max_length=10,
        choices=STATUS_CHOICES,
        default='open',
    )

    class Meta:
        db_table = 'apps_staff_inquiry'
        verbose_name = 'スタッフ問い合わせ・ご連絡'
        verbose_name_plural = 'スタッフ問い合わせ・ご連絡'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.corporate_number})"

class StaffInquiryMessage(MyModel):
    """
    スタッフ問い合わせに対する個別のメッセージ（チャット形式）
    """
    inquiry = models.ForeignKey(
        StaffInquiry,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='問い合わせ'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inquiry_messages',
        verbose_name='投稿者'
    )
    content = models.TextField(
        'メッセージ内容'
    )
    is_hidden = models.BooleanField(
        '非表示',
        default=False,
        help_text='チェックを入れるとスタッフに表示されません（社内メモ用）'
    )
    read_at = models.DateTimeField(
        '既読日時',
        null=True,
        blank=True,
    )
    attachment = models.FileField(
        '添付ファイル',
        upload_to='inquiry_attachments/%Y/%m/%d/',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'apps_staff_inquiry_message'
        verbose_name = 'スタッフ問い合わせメッセージ'
        verbose_name_plural = 'スタッフ問い合わせメッセージ'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.inquiry.subject} - {self.user.username}"
