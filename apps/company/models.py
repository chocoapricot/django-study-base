from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.common.models import MyModel
from apps.common.constants import Constants, get_dispatch_treatment_method_choices

class CompanyDepartment(MyModel):
    """
    自社の部署情報を管理するモデル。
    部署コードと有効期間に基づいた重複チェック機能を持つ。
    """
    name = models.CharField('部署名', max_length=100)
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True, db_index=True)
    department_code = models.CharField('部署コード', max_length=20)
    accounting_code = models.CharField('会計コード', max_length=20, blank=True, null=True)
    display_order = models.PositiveIntegerField('表示順', default=0)
    postal_code = models.CharField('郵便番号', max_length=7, blank=True, null=True)
    address = models.TextField('住所', blank=True, null=True)
    phone_number = models.CharField('電話番号', max_length=20, blank=True, null=True)
    # 有効期限フィールドを追加
    valid_from = models.DateField('有効期限開始日', blank=True, null=True, help_text='未入力の場合は無期限')
    valid_to = models.DateField('有効期限終了日', blank=True, null=True, help_text='未入力の場合は無期限')
    
    class Meta:
        db_table = 'apps_company_department'
        verbose_name = '部署'
        verbose_name_plural = '部署'
        ordering = ['display_order', 'name']
        # 部署コードと有効期間の組み合わせでユニーク制約を削除（期間重複チェックはcleanメソッドで実装）

    def clean(self):
        """期間重複チェックと日付の妥当性チェック"""
        super().clean()
        
        # 開始日と終了日の妥当性チェック
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError('有効期限開始日は終了日より前の日付を入力してください。')
        
        # 同じ部署コードでの期間重複チェック
        self._check_period_overlap()
    
    def _check_period_overlap(self):
        """同じ部署コードでの期間重複をチェック"""
        if not self.department_code:
            return
        
        # 自分以外の同じ部署コードのレコードを取得
        queryset = CompanyDepartment.objects.filter(department_code=self.department_code)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        
        for existing in queryset:
            if self._periods_overlap(existing):
                raise ValidationError(
                    f'部署コード「{self.department_code}」の有効期間が既存のレコード（{existing.name}）と重複しています。'
                )
    
    def _periods_overlap(self, other):
        """2つの期間が重複するかチェック"""
        # 自分の期間
        my_start = self.valid_from
        my_end = self.valid_to
        
        # 相手の期間
        other_start = other.valid_from
        other_end = other.valid_to
        
        # 無期限（None）の場合の処理
        # 開始日がNoneの場合は過去無限大として扱う
        # 終了日がNoneの場合は未来無限大として扱う
        
        # 自分の実効的な開始日と終了日
        effective_my_start = my_start if my_start else timezone.datetime.min.date()
        effective_my_end = my_end if my_end else timezone.datetime.max.date()
        
        # 相手の実効的な開始日と終了日
        effective_other_start = other_start if other_start else timezone.datetime.min.date()
        effective_other_end = other_end if other_end else timezone.datetime.max.date()
        
        # 期間重複の判定
        # 重複しない条件: 自分の終了日 < 相手の開始日 OR 相手の終了日 < 自分の開始日
        # 重複する条件: 上記の否定
        return not (effective_my_end < effective_other_start or effective_other_end < effective_my_start)
    
    def is_valid_on_date(self, date=None):
        """指定日時点で有効かどうかを判定"""
        if date is None:
            date = timezone.now().date()
        
        # 開始日チェック
        if self.valid_from and date < self.valid_from:
            return False
        
        # 終了日チェック
        if self.valid_to and date > self.valid_to:
            return False
        
        return True
    
    @classmethod
    def get_valid_departments(cls, date=None):
        """指定日時点で有効な部署一覧を取得"""
        if date is None:
            date = timezone.now().date()
        
        queryset = cls.objects.all()
        
        # 開始日条件（開始日がNullまたは指定日以前）
        queryset = queryset.filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=date)
        )
        
        # 終了日条件（終了日がNullまたは指定日以降）
        queryset = queryset.filter(
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=date)
        )
        
        return queryset

    def __str__(self):
        period_str = ""
        if self.valid_from or self.valid_to:
            start = self.valid_from.strftime('%Y/%m/%d') if self.valid_from else '無期限'
            end = self.valid_to.strftime('%Y/%m/%d') if self.valid_to else '無期限'
            period_str = f" ({start}～{end})"
        return f"{self.name}{period_str}"


def company_seal_upload_path(instance, filename):
    """会社印（丸印・角印）のアップロードパスを生成"""
    ext = filename.split('.')[-1]
    # round_seal または square_seal をファイル名に含める
    # instance._upload_type が設定されていることを期待
    upload_type = getattr(instance, '_upload_type', 'seal')
    return f'company_seals/{instance.pk}_{upload_type}.{ext}'

class Company(MyModel):
    """
    自社の会社情報を管理するモデル。
    このシステムは単一の会社で運用されることを想定しているため、
    通常、このテーブルには1つのレコードのみが存在する。
    """
    name = models.CharField('会社名', max_length=255, unique=True)
    # 会社情報として必要そうなフィールドを追加（例）
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True, unique=True)
    representative = models.CharField('代表者', max_length=100, blank=True, null=True)
    postal_code = models.CharField('郵便番号', max_length=7, blank=True, null=True)
    address = models.CharField('住所', max_length=500, blank=True, null=True)
    phone_number = models.CharField('電話番号', max_length=20, blank=True, null=True)
    haken_permit_number = models.CharField('許可番号(人材派遣)', max_length=100, blank=True, null=True)
    shokai_permit_number = models.CharField('許可番号(職業紹介)', max_length=100, blank=True, null=True)
    foreign_regist_number = models.CharField('登録番号(特定技能)', max_length=100, blank=True, null=True)
    
    # 派遣待遇決定方式の選択肢
    DISPATCH_TREATMENT_METHOD_CHOICES = get_dispatch_treatment_method_choices()
    dispatch_treatment_method = models.CharField(
        '派遣待遇決定方式',
        max_length=20,
        choices=DISPATCH_TREATMENT_METHOD_CHOICES,
        default=Constants.DISPATCH_TREATMENT_METHOD.AGREEMENT,
        help_text='派遣労働者の待遇決定方式を選択してください'
    )

    round_seal = models.ImageField(
        '丸印',
        upload_to=company_seal_upload_path,
        blank=True,
        null=True,
        help_text='契約書等に使用する丸印の画像 (600x600推奨)'
    )
    square_seal = models.ImageField(
        '角印',
        upload_to=company_seal_upload_path,
        blank=True,
        null=True,
        help_text='請求書等に使用する角印の画像 (600x600推奨)'
    )


    class Meta:
        db_table = 'apps_company'
        verbose_name = '会社'
        verbose_name_plural = '会社'

    def __str__(self):
        return self.name


class CompanyUser(MyModel):
    """自社の担当者情報を管理するモデル。"""
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True, db_index=True)
    department_code = models.CharField('部署コード', max_length=20, blank=True, null=True, db_index=True)
    name_last = models.CharField('姓', max_length=50)
    name_first = models.CharField('名', max_length=50)
    position = models.CharField('役職', max_length=50, blank=True, null=True)
    phone_number = models.CharField('電話番号', max_length=20, blank=True, null=True)
    email = models.EmailField('メールアドレス', blank=True, null=True)
    display_order = models.PositiveIntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_company_user'
        verbose_name = '自社担当者'
        verbose_name_plural = '自社担当者'
        ordering = ['display_order', 'name_last', 'name_first']

    @property
    def name(self):
        return f"{self.name_last} {self.name_first}"

    @property
    def department(self):
        if self.department_code:
            return CompanyDepartment.get_valid_departments().filter(department_code=self.department_code).first()
        return None

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        parts = []
        if self.department:
            parts.append(self.department.name)
        if self.position:
            parts.append(self.position)
        parts.append(self.name)
        return ' - '.join(parts)
