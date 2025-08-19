from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import MyModel

User = get_user_model()


class ConnectStaff(MyModel):
    """
    外部のスタッフがシステムにアクセスするための接続申請を管理するモデル。
    法人番号とメールアドレスをキーに、承認ステータスを管理する。
    """
    
    STATUS_CHOICES = [
        ('pending', '未承認'),
        ('approved', '承認済み'),
    ]
    
    corporate_number = models.CharField('法人番号', max_length=13, help_text='会社の法人番号')
    email = models.EmailField('メールアドレス', help_text='スタッフのメールアドレス')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField('承認日時', null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='approved_staff_connections', verbose_name='承認者')
    
    class Meta:
        db_table = 'apps_connect_staff'
        verbose_name = 'スタッフ接続'
        verbose_name_plural = 'スタッフ接続'
        unique_together = ['corporate_number', 'email']  # 同じ法人番号とメールアドレスの組み合わせは一意
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.corporate_number} - {self.email} ({self.get_status_display()})"
    
    @property
    def is_approved(self):
        """承認済みかどうか"""
        return self.status == 'approved'
    
    def approve(self, user):
        """承認する"""
        from django.utils import timezone
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save()
    
    def unapprove(self):
        """未承認に戻す"""
        self.status = 'pending'
        self.approved_at = None
        self.approved_by = None
        self.save()


class ConnectClient(MyModel):
    """
    外部のクライアント担当者がシステムにアクセスするための接続申請を管理するモデル。
    現在は将来の拡張用として準備されている。
    """
    
    STATUS_CHOICES = [
        ('pending', '未承認'),
        ('approved', '承認済み'),
    ]
    
    corporate_number = models.CharField('法人番号', max_length=13, help_text='会社の法人番号')
    email = models.EmailField('メールアドレス', help_text='クライアントのメールアドレス')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField('承認日時', null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='approved_client_connections', verbose_name='承認者')
    
    class Meta:
        db_table = 'apps_connect_client'
        verbose_name = 'クライアント接続'
        verbose_name_plural = 'クライアント接続'
        unique_together = ['corporate_number', 'email']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.corporate_number} - {self.email} ({self.get_status_display()})"
    
    @property
    def is_approved(self):
        """承認済みかどうか"""
        return self.status == 'approved'
    
    def approve(self, user):
        """承認する"""
        from django.utils import timezone
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save()
    
    def unapprove(self):
        """未承認に戻す"""
        self.status = 'pending'
        self.approved_at = None
        self.approved_by = None
        self.save()