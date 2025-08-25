from django.db import models
from django.core.validators import RegexValidator
from ..common.models import MyModel
from .models import StaffProfile

class StaffBankProfile(MyModel):
    """
    スタッフの銀行プロフィール情報を管理するモデル。
    StaffProfileと1対1で連携し、振込先銀行情報を保存する。
    """

    staff_profile = models.OneToOneField(
        StaffProfile,
        on_delete=models.CASCADE,
        verbose_name='スタッフプロフィール',
        related_name='bank_profile'
    )
    bank_code = models.CharField(
        max_length=4,
        verbose_name='銀行コード',
        help_text='4桁の数字で入力（任意）',
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\d{4}$',
                message='銀行コードは4桁の数字で入力してください'
            )
        ]
    )
    branch_code = models.CharField(
        max_length=3,
        verbose_name='支店コード',
        help_text='3桁の数字で入力（任意）',
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\d{3}$',
                message='支店コードは3桁の数字で入力してください'
            )
        ]
    )
    account_type = models.CharField(
        max_length=10,
        verbose_name='口座種別',
        help_text='普通、当座など'
    )
    account_number = models.CharField(
        max_length=8,
        verbose_name='口座番号',
        help_text='1-8桁の数字で入力',
        validators=[
            RegexValidator(
                regex=r'^\d{1,8}$',
                message='口座番号は1-8桁の数字で入力してください'
            )
        ]
    )
    account_holder = models.CharField(
        max_length=100,
        verbose_name='口座名義',
        help_text='口座名義人の名前'
    )

    class Meta:
        verbose_name = 'スタッフ銀行プロフィール'
        verbose_name_plural = 'スタッフ銀行プロフィール'
        db_table = 'apps_profile_staff_bank'

    def __str__(self):
        return f"{self.staff_profile} - 銀行情報"

    @property
    def bank_name(self):
        """銀行名を取得"""
        if not self.bank_code:
            return ''
        try:
            from apps.master.models import Bank
            bank = Bank.objects.get(bank_code=self.bank_code, is_active=True)
            return bank.name
        except Bank.DoesNotExist:
            return f'銀行コード: {self.bank_code}'

    @property
    def branch_name(self):
        """支店名を取得"""
        if not self.bank_code or not self.branch_code:
            return ''
        try:
            from apps.master.models import Bank, BankBranch
            bank = Bank.objects.get(bank_code=self.bank_code, is_active=True)
            branch = BankBranch.objects.get(bank=bank, branch_code=self.branch_code, is_active=True)
            return branch.name
        except (Bank.DoesNotExist, BankBranch.DoesNotExist):
            return f'支店コード: {self.branch_code}'

    @property
    def full_bank_info(self):
        """完全な銀行情報"""
        parts = []
        if self.bank_name:
            parts.append(self.bank_name)
        if self.branch_name:
            parts.append(self.branch_name)
        if parts:
            return ' '.join(parts)
        return '銀行情報なし'
