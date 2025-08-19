from django.db import models
from apps.common.models import MyModel


class Qualification(MyModel):
    """
    資格情報を管理するマスターデータモデル。
    カテゴリと資格の2階層構造を持つ。
    """
    
    LEVEL_CHOICES = [
        (1, 'カテゴリ'),
        (2, '資格'),
    ]
    
    name = models.CharField('名称', max_length=100)
    level = models.IntegerField('階層レベル', choices=LEVEL_CHOICES, default=2)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name='親カテゴリ',
        related_name='children'
    )
    description = models.TextField('説明', blank=True, null=True)
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)
    
    class Meta:
        db_table = 'apps_master_qualification'
        verbose_name = '資格'
        verbose_name_plural = '資格'
        ordering = ['level', 'display_order', 'name']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['parent']),
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        if self.level == 1:
            return f"[カテゴリ] {self.name}"
        else:
            parent_name = self.parent.name if self.parent else "未分類"
            return f"{parent_name} > {self.name}"
    
    @property
    def is_category(self):
        """カテゴリかどうか"""
        return self.level == 1
    
    @property
    def is_qualification(self):
        """資格かどうか"""
        return self.level == 2
    
    @property
    def level_display_name(self):
        """階層レベルの表示名"""
        return dict(self.LEVEL_CHOICES).get(self.level, self.level)
    
    @property
    def full_name(self):
        """フルパス名称"""
        if self.level == 1:
            return self.name
        else:
            parent_name = self.parent.name if self.parent else "未分類"
            return f"{parent_name} > {self.name}"
    
    def get_children(self):
        """子要素を取得"""
        return self.children.filter(is_active=True).order_by('display_order', 'name')
    
    @classmethod
    def get_categories(cls):
        """カテゴリ一覧を取得"""
        return cls.objects.filter(level=1, is_active=True).order_by('display_order', 'name')
    
    @classmethod
    def get_qualifications(cls, category=None):
        """資格一覧を取得"""
        qualifications = cls.objects.filter(level=2, is_active=True)
        if category:
            qualifications = qualifications.filter(parent=category)
        return qualifications.order_by('display_order', 'name')
    
    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        # レベル1（カテゴリ）は親を持てない
        if self.level == 1 and self.parent:
            raise ValidationError('カテゴリは親を持つことができません。')
        
        # レベル2（資格）は親が必要（レベル1のみ）
        if self.level == 2:
            if not self.parent:
                raise ValidationError('資格は親カテゴリが必要です。')
            if self.parent.level != 1:
                raise ValidationError('資格の親はカテゴリである必要があります。')
        
        # 自分自身を親にできない
        if self.parent == self:
            raise ValidationError('自分自身を親にすることはできません。')
    
    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.clean()
        super().save(*args, **kwargs)
    
    @property
    def usage_count(self):
        """この資格を持つスタッフの数"""
        if self.level == 1:  # カテゴリの場合は0
            return 0
        else:  # 資格の場合は直接カウント
            return self.staffqualification_set.count()
    
    def get_usage_details(self):
        """利用詳細を取得"""
        if self.level == 1:  # カテゴリの場合
            from apps.staff.models import StaffQualification
            child_qualifications = self.children.filter(is_active=True)
            return StaffQualification.objects.filter(qualification__in=child_qualifications).select_related('staff')
        else:  # 資格の場合
            return self.staffqualification_set.select_related('staff')


class Skill(MyModel):
    """
    技能（スキル）情報を管理するマスターデータモデル。
    カテゴリと技能の2階層構造を持つ。
    """
    
    LEVEL_CHOICES = [
        (1, 'カテゴリ'),
        (2, '技能'),
    ]
    
    name = models.CharField('名称', max_length=100)
    level = models.IntegerField('階層レベル', choices=LEVEL_CHOICES, default=2)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name='親カテゴリ',
        related_name='children'
    )
    description = models.TextField('説明', blank=True, null=True)
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)
    
    class Meta:
        db_table = 'apps_master_skill'
        verbose_name = '技能'
        verbose_name_plural = '技能'
        ordering = ['level', 'display_order', 'name']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['parent']),
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        if self.level == 1:
            return f"[カテゴリ] {self.name}"
        else:
            parent_name = self.parent.name if self.parent else "未分類"
            return f"{parent_name} > {self.name}"
    
    @property
    def is_category(self):
        """カテゴリかどうか"""
        return self.level == 1
    
    @property
    def is_skill(self):
        """技能かどうか"""
        return self.level == 2
    
    @property
    def level_display_name(self):
        """階層レベルの表示名"""
        return dict(self.LEVEL_CHOICES).get(self.level, self.level)
    
    @property
    def full_name(self):
        """フルパス名称"""
        if self.level == 1:
            return self.name
        else:
            parent_name = self.parent.name if self.parent else "未分類"
            return f"{parent_name} > {self.name}"
    
    def get_children(self):
        """子要素を取得"""
        return self.children.filter(is_active=True).order_by('display_order', 'name')
    
    @classmethod
    def get_categories(cls):
        """カテゴリ一覧を取得"""
        return cls.objects.filter(level=1, is_active=True).order_by('display_order', 'name')
    
    @classmethod
    def get_skills(cls, category=None):
        """技能一覧を取得"""
        skills = cls.objects.filter(level=2, is_active=True)
        if category:
            skills = skills.filter(parent=category)
        return skills.order_by('display_order', 'name')
    
    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        # レベル1（カテゴリ）は親を持てない
        if self.level == 1 and self.parent:
            raise ValidationError('カテゴリは親を持つことができません。')
        
        # レベル2（技能）は親が必要（レベル1のみ）
        if self.level == 2:
            if not self.parent:
                raise ValidationError('技能は親カテゴリが必要です。')
            if self.parent.level != 1:
                raise ValidationError('技能の親はカテゴリである必要があります。')
        
        # 自分自身を親にできない
        if self.parent == self:
            raise ValidationError('自分自身を親にすることはできません。')
    
    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.clean()
        super().save(*args, **kwargs)
    
    @property
    def usage_count(self):
        """この技能を持つスタッフの数"""
        if self.level == 1:  # カテゴリの場合は0
            return 0
        else:  # 技能の場合は直接カウント
            return self.staffskill_set.count()
    
    def get_usage_details(self):
        """利用詳細を取得"""
        if self.level == 1:  # カテゴリの場合
            from apps.staff.models import StaffSkill
            child_skills = self.children.filter(is_active=True)
            return StaffSkill.objects.filter(skill__in=child_skills).select_related('staff')
        else:  # 技能の場合
            return self.staffskill_set.select_related('staff')


class BillPayment(MyModel):
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
    
    def get_usage_details(self):
        """利用詳細を取得"""
        from apps.client.models import Client
        from apps.contract.models import ClientContract
        
        # クライアントでの利用
        clients = Client.objects.filter(payment_site=self).select_related()
        
        # クライアント契約での利用
        contracts = ClientContract.objects.filter(payment_site=self).select_related('client')
        
        return {
            'clients': clients,
            'contracts': contracts,
            'client_count': clients.count(),
            'contract_count': contracts.count(),
            'total_count': clients.count() + contracts.count()
        }
    
    @classmethod
    def get_active_list(cls):
        """有効な支払条件一覧を取得"""
        return cls.objects.filter(is_active=True).order_by('display_order', 'name')


class BillBank(MyModel):
    """
    自社の振込先銀行口座情報を管理するマスターデータモデル。
    """
    
    name = models.CharField('銀行名', max_length=100)
    bank_code = models.CharField('銀行コード', max_length=4, help_text='4桁の数字で入力')
    branch_name = models.CharField('支店名', max_length=100)
    branch_code = models.CharField('支店コード', max_length=3, help_text='3桁の数字で入力')
    account_type = models.CharField(
        '口座種別', 
        max_length=10, 
        choices=[
            ('ordinary', '普通'),
            ('current', '当座'),
        ],
        default='ordinary'
    )
    account_number = models.CharField('口座番号', max_length=8)
    account_holder = models.CharField('口座名義', max_length=100)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100, blank=True, null=True)
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)
    
    class Meta:
        db_table = 'apps_master_bill_bank'
        verbose_name = '振込先銀行'
        verbose_name_plural = '振込先銀行'
        ordering = ['display_order', 'name', 'branch_name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
            models.Index(fields=['bank_code']),
            models.Index(fields=['branch_code']),
        ]
    
    def __str__(self):
        return f"{self.name} {self.branch_name} {self.account_type_display} {self.account_number}"
    
    @property
    def account_type_display(self):
        """口座種別の表示名"""
        return dict(self._meta.get_field('account_type').choices).get(self.account_type, self.account_type)
    
    @property
    def full_bank_info(self):
        """完全な銀行情報"""
        bank_info = f"{self.name}"
        if self.bank_code:
            bank_info += f"（{self.bank_code}）"
        
        branch_info = f" {self.branch_name}"
        if self.branch_code:
            branch_info += f"（{self.branch_code}）"
        
        return f"{bank_info}{branch_info} {self.account_type_display} {self.account_number}"
    
    @property
    def account_info(self):
        """口座情報"""
        return f"{self.account_type_display} {self.account_number} {self.account_holder}"
    
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
        """有効な振込先銀行一覧を取得"""
        return cls.objects.filter(is_active=True).order_by('display_order', 'name', 'branch_name')


class Bank(MyModel):
    """
    銀行情報を管理するマスターデータモデル。
    """
    
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
    
    def get_usage_details(self):
        """利用詳細を取得"""
        # 将来的に他のモデルで銀行が参照される場合のために準備
        return {
            'total_count': 0
        }


class BankBranch(MyModel):
    """
    銀行の支店情報を管理するマスターデータモデル。
    Bankモデルと連携する。
    """
    
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
    
    @property
    def bank_branch_info(self):
        """銀行支店情報"""
        bank_info = self.bank.full_name
        branch_info = self.name
        if self.branch_code:
            branch_info += f"（{self.branch_code}）"
        return f"{bank_info} {branch_info}"
    
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
    
    @classmethod
    def get_by_bank(cls, bank):
        """指定銀行の支店一覧を取得"""
        return cls.objects.filter(bank=bank, is_active=True).order_by('name')
    
    @property
    def usage_count(self):
        """この銀行支店の利用件数"""
        # 将来的に他のモデルで銀行支店が参照される場合のために準備
        return 0
    
    def get_usage_details(self):
        """利用詳細を取得"""
        # 将来的に他のモデルで銀行支店が参照される場合のために準備
        return {
            'total_count': 0
        }