from django.db import models
from apps.common.models import MyModel
from apps.client.models import Client
from apps.staff.models import Staff


class ClientContract(MyModel):
    """クライアント契約"""
    
    CONTRACT_TYPE_CHOICES = [
        ('service', 'サービス契約'),
        ('maintenance', '保守契約'),
        ('development', '開発契約'),
        ('consulting', 'コンサルティング契約'),
        ('other', 'その他'),
    ]
    
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name='クライアント'
    )
    contract_name = models.CharField('契約名', max_length=200)
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)
    contract_type = models.CharField('契約種別', max_length=20, choices=CONTRACT_TYPE_CHOICES, default='service')
    start_date = models.DateField('契約開始日')
    end_date = models.DateField('契約終了日', blank=True, null=True)
    contract_amount = models.DecimalField('契約金額', max_digits=12, decimal_places=0, blank=True, null=True)
    payment_terms = models.CharField('支払条件', max_length=200, blank=True, null=True)
    description = models.TextField('契約内容', blank=True, null=True)
    notes = models.TextField('備考', blank=True, null=True)
    auto_renewal = models.BooleanField('自動更新', default=False)
    is_active = models.BooleanField('有効', default=True)
    
    class Meta:
        db_table = 'apps_contract_client'
        verbose_name = 'クライアント契約'
        verbose_name_plural = 'クライアント契約'
        ordering = ['-start_date', 'client__name']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.client.name} - {self.contract_name}"
    
    @property
    def is_current(self):
        """現在有効な契約かどうか"""
        from django.utils import timezone
        today = timezone.now().date()
        if not self.is_active:
            return False
        if not self.end_date:  # 無期限契約
            return today >= self.start_date
        return self.start_date <= today <= self.end_date
    
    @property
    def is_future(self):
        """開始前の契約かどうか"""
        from django.utils import timezone
        today = timezone.now().date()
        return today < self.start_date and self.is_active
    
    @property
    def is_expired(self):
        """期限切れの契約かどうか"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.end_date and today > self.end_date
    
    @property
    def status(self):
        """契約状況"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.is_active:
            return "無効"
        elif today < self.start_date:
            return "開始前"
        elif self.end_date and today > self.end_date:
            return "終了"
        else:
            return "有効"
    
    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('契約開始日は終了日より前の日付を入力してください。')


class StaffContract(MyModel):
    """スタッフ契約"""
    
    CONTRACT_TYPE_CHOICES = [
        ('full_time', '正社員'),
        ('part_time', 'パートタイム'),
        ('contract', '契約社員'),
        ('freelance', 'フリーランス'),
        ('intern', 'インターン'),
        ('other', 'その他'),
    ]
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name='スタッフ'
    )
    contract_name = models.CharField('契約名', max_length=200)
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)
    contract_type = models.CharField('契約種別', max_length=20, choices=CONTRACT_TYPE_CHOICES, default='full_time')
    start_date = models.DateField('契約開始日')
    end_date = models.DateField('契約終了日', blank=True, null=True)
    contract_amount = models.DecimalField('契約金額', max_digits=10, decimal_places=0, blank=True, null=True)
    payment_terms = models.CharField('支払条件', max_length=200, blank=True, null=True)
    description = models.TextField('契約内容', blank=True, null=True)
    notes = models.TextField('備考', blank=True, null=True)
    auto_renewal = models.BooleanField('自動更新', default=False)
    is_active = models.BooleanField('有効', default=True)
    
    class Meta:
        db_table = 'apps_contract_staff'
        verbose_name = 'スタッフ契約'
        verbose_name_plural = 'スタッフ契約'
        ordering = ['-start_date', 'staff__name_last', 'staff__name_first']
        indexes = [
            models.Index(fields=['staff']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.staff.name_last} {self.staff.name_first} - {self.contract_name}"
    
    @property
    def is_current(self):
        """現在有効な契約かどうか"""
        from django.utils import timezone
        today = timezone.now().date()
        if not self.is_active:
            return False
        if not self.end_date:  # 無期限契約
            return today >= self.start_date
        return self.start_date <= today <= self.end_date
    
    @property
    def is_future(self):
        """開始前の契約かどうか"""
        from django.utils import timezone
        today = timezone.now().date()
        return today < self.start_date and self.is_active
    
    @property
    def is_expired(self):
        """期限切れの契約かどうか"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.end_date and today > self.end_date
    
    @property
    def status(self):
        """契約状況"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.is_active:
            return "無効"
        elif today < self.start_date:
            return "開始前"
        elif self.end_date and today > self.end_date:
            return "終了"
        else:
            return "有効"
    
    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('契約開始日は終了日より前の日付を入力してください。')