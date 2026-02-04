from django.db import models
from apps.common.models import MyTenantModel
from apps.system.settings.models import Dropdowns


class BillPayment(MyTenantModel):
    """
    支払条件（締め日・支払日など）を管理するマスターデータモデル。
    """

    name = models.CharField('支払条件名', max_length=100)
    closing_day = models.IntegerField('締め日', help_text='月末締めの場合は31を入力')
    invoice_months_after = models.IntegerField('請求書提出月数', default=0, help_text='締め日から何か月後')
    invoice_day = models.IntegerField('請求書必着日', help_text='請求書が必着する日')
    payment_months_after = models.IntegerField('支払い月数', default=1, help_text='締め日から何か月後')
    payment_day = models.IntegerField('支払い日', help_text='支払いが行われる日')
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_bill_payment'
        verbose_name = '支払条件'
        verbose_name_plural = '支払条件'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name

    @property
    def closing_day_display(self):
        """締め日の表示用文字列"""
        if self.closing_day == 31:
            return "月末"
        else:
            return f"{self.closing_day}日"

    @property
    def invoice_schedule_display(self):
        """請求書スケジュールの表示用文字列"""
        if self.invoice_months_after == 0:
            return f"当月{self.invoice_day}日まで"
        else:
            return f"{self.invoice_months_after}か月後{self.invoice_day}日まで"

    @property
    def payment_schedule_display(self):
        """支払いスケジュールの表示用文字列"""
        if self.payment_months_after == 0:
            return f"当月{self.payment_day}日"
        else:
            return f"{self.payment_months_after}か月後{self.payment_day}日"

    @property
    def full_schedule_display(self):
        """完全なスケジュール表示"""
        return f"{self.closing_day_display}締め → {self.invoice_schedule_display}請求書必着 → {self.payment_schedule_display}支払い"

    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError

        # 締め日のバリデーション
        if not (1 <= self.closing_day <= 31):
            raise ValidationError('締め日は1-31の範囲で入力してください。')

        # 請求書必着日のバリデーション
        if not (1 <= self.invoice_day <= 31):
            raise ValidationError('請求書必着日は1-31の範囲で入力してください。')

        # 支払い日のバリデーション
        if not (1 <= self.payment_day <= 31):
            raise ValidationError('支払い日は1-31の範囲で入力してください。')

        # 月数のバリデーション
        if self.invoice_months_after < 0:
            raise ValidationError('請求書提出月数は0以上で入力してください。')

        if self.payment_months_after < 0:
            raise ValidationError('支払い月数は0以上で入力してください。')

    @property
    def usage_count(self):
        """この支払条件の利用件数（クライアント + クライアント契約）"""
        # クライアントでの利用件数
        from apps.client.models import Client
        client_count = Client.objects.filter(payment_site=self).count()

        # クライアント契約での利用件数
        from apps.contract.models import ClientContract
        contract_count = ClientContract.objects.filter(payment_site=self).count()

        return client_count + contract_count

    @classmethod
    def get_active_list(cls):
        """有効な支払条件一覧を取得"""
        return cls.objects.filter(is_active=True).order_by('display_order', 'name')


class MinimumPay(MyTenantModel):
    """
    最低賃金マスタ
    """
    pref = models.CharField('都道府県', max_length=10)
    start_date = models.DateField('開始日')
    hourly_wage = models.IntegerField('最低時給')
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_minimum_pay'
        verbose_name = '最低賃金'
        verbose_name_plural = '最低賃金'
        ordering = ['display_order', 'pref', '-start_date']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
            models.Index(fields=['pref']),
            models.Index(fields=['start_date']),
        ]

    def __str__(self):
        return f"{self.pref_name} - {self.start_date.strftime('%Y/%m/%d')} - ¥{self.hourly_wage:,}"

    @property
    def pref_name(self):
        """都道府県名"""
        d = Dropdowns.objects.filter(category='pref', value=self.pref).first()
        if d:
            return f"{d.value}:{d.name}"
        return self.pref


class BillBank(MyTenantModel):
    """
    自社の銀行口座情報を管理するマスターデータモデル。
    """

    bank_code = models.CharField('銀行コード', max_length=4, help_text='4桁の数字で入力')
    branch_code = models.CharField('支店コード', max_length=3, help_text='3桁の数字で入力')
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        help_text='普通、当座など'
    )
    account_number = models.CharField('口座番号', max_length=8)
    account_holder = models.CharField('口座名義', max_length=100)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100, blank=True, null=True)
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_bill_bank'
        verbose_name = '会社銀行'
        verbose_name_plural = '会社銀行'
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
            models.Index(fields=['bank_code']),
            models.Index(fields=['branch_code']),
        ]

    def __str__(self):
        try:
            return f"{self.bank_name} {self.branch_name} {self.account_type} {self.account_number}"
        except (Bank.DoesNotExist, BankBranch.DoesNotExist):
            return f"{self.bank_code} {self.branch_code} {self.account_type} {self.account_number}"

    @property
    def bank(self):
        return Bank.objects.get(bank_code=self.bank_code)

    @property
    def branch(self):
        return BankBranch.objects.get(bank__bank_code=self.bank_code, branch_code=self.branch_code)

    @property
    def bank_name(self):
        return self.bank.name

    @property
    def branch_name(self):
        return self.branch.name

    @property
    def full_bank_info(self):
        """完全な銀行情報"""
        try:
            bank_info = f"{self.bank_name}"
            if self.bank_code:
                bank_info += f"（{self.bank_code}）"

            branch_info = f" {self.branch_name}"
            if self.branch_code:
                branch_info += f"（{self.branch_code}）"

            return f"{bank_info}{branch_info} {self.account_type} {self.account_number}"
        except (Bank.DoesNotExist, BankBranch.DoesNotExist):
            return f"銀行情報不明（{self.bank_code}） 支店情報不明（{self.branch_code}） {self.account_type} {self.account_number}"

    @property
    def account_info(self):
        """口座情報"""
        return f"{self.account_type} {self.account_number} {self.account_holder}"

    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError

        # 銀行コードのバリデーション（必須）
        if not self.bank_code:
            raise ValidationError('銀行コードは必須です。')

        if not self.bank_code.isdigit():
            raise ValidationError('銀行コードは数字で入力してください。')

        if len(self.bank_code) != 4:
            raise ValidationError('銀行コードは4桁で入力してください。')

        # 支店コードのバリデーション（必須）
        if not self.branch_code:
            raise ValidationError('支店コードは必須です。')

        if not self.branch_code.isdigit():
            raise ValidationError('支店コードは数字で入力してください。')

        if len(self.branch_code) != 3:
            raise ValidationError('支店コードは3桁で入力してください。')

        # 口座番号のバリデーション
        if not self.account_number.isdigit():
            raise ValidationError('口座番号は数字で入力してください。')

        if not (1 <= len(self.account_number) <= 8):
            raise ValidationError('口座番号は1-8桁で入力してください。')

    @classmethod
    def get_active_list(cls):
        """有効な会社銀行一覧を取得"""
        return cls.objects.filter(is_active=True).order_by('display_order')


class Bank(MyTenantModel):
    """
    銀行情報を管理するマスターデータモデル。
    """
    objects = models.Manager()

    name = models.CharField('銀行名', max_length=100)
    bank_code = models.CharField('銀行コード', max_length=4, unique=True, help_text='4桁の数字で入力')
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_bank'
        verbose_name = '銀行'
        verbose_name_plural = '銀行'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['bank_code']),
        ]

    def __str__(self):
        if self.bank_code:
            return f"{self.name}（{self.bank_code}）"
        return self.name

    @property
    def full_name(self):
        """完全な銀行名"""
        if self.bank_code:
            return f"{self.name}（{self.bank_code}）"
        return self.name

    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError

        # 銀行コードのバリデーション（必須）
        if not self.bank_code:
            raise ValidationError('銀行コードは必須です。')

        if not self.bank_code.isdigit():
            raise ValidationError('銀行コードは数字で入力してください。')

        if len(self.bank_code) != 4:
            raise ValidationError('銀行コードは4桁で入力してください。')

    @classmethod
    def get_active_list(cls):
        """有効な銀行一覧を取得"""
        return cls.objects.filter(is_active=True).order_by('name')

    @property
    def usage_count(self):
        """この銀行の利用件数"""
        # 将来的に他のモデルで銀行が参照される場合のために準備
        return 0


class BankBranch(MyTenantModel):
    """
    銀行の支店情報を管理するマスターデータモデル。
    Bankモデルと連携する。
    """
    objects = models.Manager()

    bank = models.ForeignKey(
        Bank,
        on_delete=models.CASCADE,
        verbose_name='銀行',
        related_name='branches'
    )
    name = models.CharField('支店名', max_length=100)
    branch_code = models.CharField('支店コード', max_length=3, help_text='3桁の数字で入力')
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_bank_branch'
        verbose_name = '銀行支店'
        verbose_name_plural = '銀行支店'
        ordering = ['bank__name', 'name']
        indexes = [
            models.Index(fields=['bank']),
            models.Index(fields=['is_active']),
            models.Index(fields=['branch_code']),
        ]
        unique_together = [
            ['bank', 'branch_code'],  # 同一銀行内で支店コードは重複不可
        ]

    def __str__(self):
        if self.branch_code:
            return f"{self.bank.name} {self.name}（{self.branch_code}）"
        return f"{self.bank.name} {self.name}"

    @property
    def full_name(self):
        """完全な支店名"""
        if self.branch_code:
            return f"{self.bank.name} {self.name}（{self.branch_code}）"
        return f"{self.bank.name} {self.name}"

    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError

        # 支店コードのバリデーション（必須）
        if not self.branch_code:
            raise ValidationError('支店コードは必須です。')

        if not self.branch_code.isdigit():
            raise ValidationError('支店コードは数字で入力してください。')

        if len(self.branch_code) != 3:
            raise ValidationError('支店コードは3桁で入力してください。')

    @classmethod
    def get_active_list(cls, bank=None):
        """有効な銀行支店一覧を取得"""
        branches = cls.objects.filter(is_active=True).select_related('bank')
        if bank:
            branches = branches.filter(bank=bank)
        return branches.order_by('bank__name', 'name')

    @property
    def usage_count(self):
        """この銀行支店の利用件数"""
        # 将来的に他のモデルで銀行支店が参照される場合のために準備
        return 0
