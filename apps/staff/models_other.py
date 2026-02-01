from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from ..common.models import MyTenantModel, TenantManager
from django_currentuser.db.models import CurrentUserField
from .models_staff import Staff

def validate_mynumber(value):
    """マイナンバーのバリデーション関数"""
    if not value:
        return

    try:
        from stdnum.jp import in_
        if not in_.is_valid(value):
            raise ValidationError('正しいマイナンバーを入力してください。')
    except ImportError:
        # python-stdnumがインストールされていない場合は基本的なチェックのみ
        import re
        if not re.match(r'^\d{12}$', value):
            raise ValidationError('マイナンバーは12桁の数字で入力してください。')
    except Exception:
        raise ValidationError('正しいマイナンバーを入力してください。')

class StaffMynumber(MyTenantModel):
    """
    スタッフのマイナンバー情報を管理するモデル。
    Staffモデルと1対1で連携し、暗号化して保存することを想定（要追加実装）。
    """
    objects = TenantManager()

    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ',
        related_name='mynumber'
    )
    mynumber = models.CharField(
        max_length=12,
        verbose_name='マイナンバー',
        validators=[
            validate_mynumber,
            RegexValidator(
                regex=r'^\d{12}$',
                message='マイナンバーは12桁の数字で入力してください'
            )
        ],
        help_text='マイナンバーを12桁の数字で入力してください'
    )

    class Meta:
        verbose_name = 'スタッフマイナンバー'
        verbose_name_plural = 'スタッフマイナンバー'
        db_table = 'apps_staff_mynumber'

    def __str__(self):
        return f"{self.staff} - マイナンバー"


class StaffContact(MyTenantModel):
    """
    スタッフの連絡先情報を管理するモデル。
    """
    objects = TenantManager()
    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ',
        related_name='contact'
    )
    emergency_contact = models.CharField('緊急連絡先', max_length=100, blank=True, null=True)
    relationship = models.CharField('続柄', max_length=100, blank=True, null=True)
    postal_code = models.CharField('郵便番号（住民票）', max_length=7, blank=True, null=True)
    address1 = models.TextField('住所１（住民票）', blank=True, null=True)
    address2 = models.TextField('住所２（住民票）', blank=True, null=True)
    address3 = models.TextField('住所３（住民票）', blank=True, null=True)

    created_by = CurrentUserField(verbose_name="作成者", related_name="created_staff_contact_set_staff_app")
    updated_by = CurrentUserField(verbose_name="更新者", related_name="updated_staff_contact_set_staff_app")

    class Meta:
        verbose_name = 'スタッフ連絡先情報'
        verbose_name_plural = 'スタッフ連絡先情報'
        db_table = 'apps_staff_contacts'

    def __str__(self):
        return f"{self.staff} - 連絡先情報"


class StaffBank(MyTenantModel):
    """
    スタッフの銀行情報を管理するモデル。
    Staffモデルと1対1で連携し、振込先銀行情報を保存する。
    """
    objects = TenantManager()

    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ',
        related_name='bank'
    )
    bank_code = models.CharField(
        max_length=4,
        verbose_name='銀行コード',
        help_text='4桁の数字で入力',
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
        help_text='3桁の数字で入力',
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
        verbose_name = 'スタッフ銀行情報'
        verbose_name_plural = 'スタッフ銀行情報'
        db_table = 'apps_staff_bank'

    def __str__(self):
        return f"{self.staff} - 銀行情報"

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

class StaffInternational(MyTenantModel):
    """
    スタッフの外国籍情報を管理するモデル。
    Staffモデルと1対1で連携し、在留カード情報を保存する。
    """
    objects = TenantManager()

    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ',
        related_name='international'
    )
    residence_card_number = models.CharField(
        max_length=20,
        verbose_name='在留カード番号',
        help_text='在留カード番号を入力してください'
    )
    residence_status = models.CharField(
        max_length=100,
        verbose_name='在留資格',
        help_text='在留資格を入力してください'
    )
    residence_period_from = models.DateField(
        verbose_name='在留許可開始日',
        help_text='在留許可の開始日を入力してください'
    )
    residence_period_to = models.DateField(
        verbose_name='在留期限',
        help_text='在留期間の終了日（在留期限）を入力してください'
    )

    class Meta:
        verbose_name = 'スタッフ外国籍情報'
        verbose_name_plural = 'スタッフ外国籍情報'
        db_table = 'apps_staff_international'

    def __str__(self):
        return f"{self.staff} - 外国籍情報"

    @property
    def is_expired(self):
        """在留期限が切れているかどうか"""
        from django.utils import timezone
        return self.residence_period_to < timezone.localdate()

    @property
    def is_expiring_soon(self):
        """在留期限が間もなく切れるかどうか（30日以内）"""
        return self.is_expiring_soon_within_days(30)

    def is_expiring_soon_within_days(self, days=30):
        """在留期限が指定日数以内に切れるかどうか"""
        from django.utils import timezone
        from datetime import timedelta
        return self.residence_period_to <= timezone.localdate() + timedelta(days=days)


class StaffDisability(MyTenantModel):
    """
    スタッフの障害者情報を管理するモデル。
    """
    objects = TenantManager()

    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ',
        related_name='disability'
    )
    disability_type = models.CharField(
        max_length=100,
        verbose_name='障害の種類',
        help_text='障害の種類を入力してください'
    )
    disability_grade = models.CharField(
        max_length=100,
        verbose_name='等級',
        help_text='障害の等級を入力してください',
        blank=True,
        null=True
    )
    disability_severity = models.CharField(
        max_length=100,
        verbose_name='重度',
        help_text='障害の重度を入力してください',
        blank=True,
        null=True
    )
    class Meta:
        verbose_name = 'スタッフ障害者情報'
        verbose_name_plural = 'スタッフ障害者情報'
        db_table = 'apps_staff_disability'

    def __str__(self):
        return f"{self.staff} - 障害者情報"

from apps.common.models import MyFlagModel


class StaffFlag(MyFlagModel):
    """
    スタッフのフラッグ情報を管理するモデル。
    """
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ',
        related_name='flags'
    )
    
    class Meta:
        verbose_name = 'スタッフフラッグ'
        verbose_name_plural = 'スタッフフラッグ'
        db_table = 'apps_staff_flag'
    
    def __str__(self):
        return f"{self.staff} - {self.flag_status}"
