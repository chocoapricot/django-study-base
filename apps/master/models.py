import os
from uuid import uuid4
from django.db import models
from apps.common.models import MyModel
from apps.system.settings.models import Dropdowns


def information_file_path(instance, filename):
    """
    お知らせ添付ファイルのアップロードパスを生成する。
    media/information_files/<information_id>/<uuid>_<filename>
    """
    filename = os.path.basename(filename)
    return os.path.join(
        'information_files',
        str(instance.information.id),
        f"{uuid4().hex}_{filename}"
    )


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

    @classmethod
    def get_active_list(cls):
        """有効な支払条件一覧を取得"""
        return cls.objects.filter(is_active=True).order_by('display_order', 'name')


class MinimumPay(MyModel):
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
        from apps.system.settings.models import Dropdowns
        d = Dropdowns.objects.filter(category='pref', value=self.pref).first()
        if d:
            return f"{d.value}:{d.name}"
        return self.pref


class BillBank(MyModel):
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
    
class ContractPattern(MyModel):
    """
    契約書パターンマスタ
    """
    name = models.CharField('名称', max_length=100)
    domain = models.CharField(
        '対象',
        max_length=2,
        choices=[('1', 'スタッフ'), ('10', 'クライアント')],
        default='1',
    )
    contract_type_code = models.CharField('契約種別', max_length=2, blank=True, null=True)
    memo = models.TextField('メモ', blank=True, null=True)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_contract_pattern'
        verbose_name = '契約書パターン'
        verbose_name_plural = '契約書パターン'
        ordering = ['domain', 'display_order']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


class ContractTerms(MyModel):
    """
    契約文言マスタ
    """
    contract_pattern = models.ForeignKey(
        ContractPattern,
        on_delete=models.CASCADE,
        verbose_name='契約書パターン',
        related_name='terms'
    )
    contract_clause = models.TextField('契約条項')
    contract_terms = models.TextField('契約文言')
    POSITION_CHOICES = [
        (1, '前文'),
        (2, '本文'),
        (3, '末文'),
    ]
    display_position = models.IntegerField(
        '表示場所',
        choices=POSITION_CHOICES,
        default=2,
    )
    memo = models.CharField('メモ', max_length=255, blank=True, null=True)
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_contract_terms'
        verbose_name = '契約文言'
        verbose_name_plural = '契約文言'
        ordering = ['display_position', 'display_order']
        indexes = [
            models.Index(fields=['display_position']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"{self.contract_pattern.name} - {self.id}"


class MailTemplate(MyModel):
    """
    メールテンプレートを管理するマスターデータモデル。
    """
    name = models.CharField('日本語名', max_length=255, editable=False, default='')
    template_key = models.CharField(
        'テンプレートキー',
        max_length=255,
        unique=True,
        help_text='プログラム側で識別するためのキー（例: "connect_request_new_user"）',
        editable=False
    )
    subject = models.CharField('件名', max_length=255)
    body = models.TextField('本文')
    remarks = models.TextField('備考', blank=True, null=True, help_text='このテンプレートの説明や変数のリストなど')

    class Meta:
        db_table = 'apps_master_mail_template'
        verbose_name = 'メールテンプレート'
        verbose_name_plural = 'メールテンプレート'
        ordering = ['template_key']

    def __str__(self):
        return self.name


class StaffAgreement(MyModel):
    """
    スタッフ同意文言マスター
    """
    name = models.CharField('名称', max_length=100)
    agreement_text = models.TextField('文言')
    corporation_number = models.CharField('法人番号', max_length=13, blank=True, null=True)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_staff_agreement'
        verbose_name = 'スタッフ同意文言'
        verbose_name_plural = 'スタッフ同意文言'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                original = StaffAgreement.objects.get(pk=self.pk)
                if (self.name == original.name and
                    self.agreement_text == original.agreement_text and
                    self.display_order == original.display_order and
                    self.is_active == original.is_active):
                    return  # No changes, so don't save
            except StaffAgreement.DoesNotExist:
                pass  # Object is new, proceed to save
        super().save(*args, **kwargs)


class JobCategory(MyModel):
    """
    職種マスタ
    """
    name = models.CharField('名称', max_length=100)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)
    is_manufacturing_dispatch = models.BooleanField('製造派遣該当', default=False, help_text='この職種が製造業務への労働者派遣に該当する場合にチェックします。')
    jobs_kourou = models.ForeignKey(
        'settings.Dropdowns',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='職業分類(厚労省)',
        related_name='job_category_kourou',
        limit_choices_to={'category': 'jobs_kourou', 'active': True}
    )
    jobs_soumu = models.ForeignKey(
        'settings.Dropdowns',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='職業分類(総務省)',
        related_name='job_category_soumu',
        limit_choices_to={'category': 'jobs_soumu', 'active': True}
    )

    class Meta:
        db_table = 'apps_master_job_category'
        verbose_name = '職種マスタ'
        verbose_name_plural = '職種マスタ'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


class BusinessContent(MyModel):
    """
    業務内容マスタ
    """
    content = models.TextField('内容')
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_business_content'
        verbose_name = '業務内容'
        verbose_name_plural = '業務内容'
        ordering = ['display_order']

    def __str__(self):
        return self.content


class HakenResponsibilityDegree(MyModel):
    """
    派遣責任程度マスタ
    """
    content = models.CharField('内容', max_length=255)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_haken_responsibility_degree'
        verbose_name = '派遣責任程度'
        verbose_name_plural = '派遣責任程度'
        ordering = ['display_order']

    def __str__(self):
        return self.content


class Information(MyModel):
    """
    お知らせ情報を管理するマスターデータモデル。
    """

    target = models.CharField(
        '対象',
        max_length=10,
        default='1',
    )
    subject = models.CharField('件名', max_length=200)
    content = models.TextField('内容')
    start_date = models.DateField('開始日', null=True, blank=True)
    end_date = models.DateField('終了日', null=True, blank=True)
    corporation_number = models.CharField('法人番号', max_length=13, blank=True, null=True)

    class Meta:
        db_table = 'apps_master_information'
        verbose_name = 'お知らせ'
        verbose_name_plural = 'お知らせ'
        ordering = ['-start_date']

    def __str__(self):
        return self.subject


class InformationFile(MyModel):
    """
    お知らせの添付ファイルを管理するモデル。
    """
    information = models.ForeignKey(
        Information,
        on_delete=models.CASCADE,
        verbose_name='お知らせ',
        related_name='files'
    )
    file = models.FileField('ファイル', upload_to=information_file_path)
    filename = models.CharField('ファイル名', max_length=255, blank=True)

    class Meta:
        db_table = 'apps_master_information_file'
        verbose_name = 'お知らせ添付ファイル'
        verbose_name_plural = 'お知らせ添付ファイル'
        ordering = ['-created_at']

    def __str__(self):
        return self.filename or str(self.file)

    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # ファイルも削除
        self.file.delete(save=False)
        super().delete(*args, **kwargs)


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


class DefaultValue(MyModel):
    """
    システムの各項目における初期値を管理するマスターデータ。
    """
    FORMAT_CHOICES = [
        ('text', 'テキスト'),
        ('textarea', 'テキストエリア'),
    ]

    key = models.CharField('キー', max_length=255, primary_key=True)
    target_item = models.CharField('対象項目', max_length=255)
    format = models.CharField('形式', max_length=10, choices=FORMAT_CHOICES, default='text')
    value = models.TextField('値', blank=True)
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_default_value'
        verbose_name = '初期値マスタ'
        verbose_name_plural = '初期値マスタ'
        ordering = ['display_order', 'target_item']

    def __str__(self):
        return self.target_item
