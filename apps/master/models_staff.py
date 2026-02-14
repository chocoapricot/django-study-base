from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import MyTenantModel
from apps.common.constants import (
    Constants,
    get_pay_unit_choices,
    get_qualification_level_choices,
    get_skill_level_choices
)


class Qualification(MyTenantModel):
    """
    資格情報を管理するマスターデータモデル。
    カテゴリと資格の2階層構造を持つ。
    """

    name = models.CharField('名称', max_length=100)
    level = models.IntegerField(
        '階層レベル',
        choices=get_qualification_level_choices(),
        default=Constants.MASTER_LEVEL.ITEM
    )
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
        return self.level == Constants.MASTER_LEVEL.CATEGORY

    @property
    def level_display_name(self):
        """階層レベルの表示名"""
        return dict(get_qualification_level_choices()).get(self.level, self.level)

    @property
    def full_name(self):
        """フルパス名称"""
        if self.level == Constants.MASTER_LEVEL.CATEGORY:
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
        if self.level == Constants.MASTER_LEVEL.CATEGORY and self.parent:
            raise ValidationError('カテゴリは親を持つことができません。')

        # レベル2（資格）は親が必要（レベル1のみ）
        if self.level == Constants.MASTER_LEVEL.ITEM:
            if not self.parent:
                raise ValidationError('資格は親カテゴリが必要です。')
            if self.parent.level != Constants.MASTER_LEVEL.CATEGORY:
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


class Skill(MyTenantModel):
    """
    技能（スキル）情報を管理するマスターデータモデル。
    カテゴリと技能の2階層構造を持つ。
    """

    name = models.CharField('名称', max_length=100)
    level = models.IntegerField(
        '階層レベル',
        choices=get_skill_level_choices(),
        default=Constants.MASTER_LEVEL.ITEM
    )
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
        return self.level == Constants.MASTER_LEVEL.CATEGORY

    @property
    def level_display_name(self):
        """階層レベルの表示名"""
        return dict(get_skill_level_choices()).get(self.level, self.level)

    @property
    def full_name(self):
        """フルパス名称"""
        if self.level == Constants.MASTER_LEVEL.CATEGORY:
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
        if self.level == Constants.MASTER_LEVEL.CATEGORY and self.parent:
            raise ValidationError('カテゴリは親を持つことができません。')

        # レベル2（技能）は親が必要（レベル1のみ）
        if self.level == Constants.MASTER_LEVEL.ITEM:
            if not self.parent:
                raise ValidationError('技能は親カテゴリが必要です。')
            if self.parent.level != Constants.MASTER_LEVEL.CATEGORY:
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


class StaffAgreement(MyTenantModel):
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


class StaffTag(MyTenantModel):
    """
    スタッフタグマスタ
    """
    name = models.CharField('名称', max_length=100)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_staff_tag'
        verbose_name = 'スタッフタグ'
        verbose_name_plural = 'スタッフタグ'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


class StaffRegistStatus(MyTenantModel):
    """
    スタッフ登録状況マスタ
    """
    name = models.CharField('名称', max_length=100)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_staff_regist_status'
        verbose_name = 'スタッフ登録状況'
        verbose_name_plural = 'スタッフ登録状況'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name

class Grade(MyTenantModel):
    """
    スタッフ等級マスタ
    """
    code = models.CharField('コード', max_length=20)
    name = models.CharField('名称', max_length=100)
    salary_type = models.CharField('給与種別', max_length=10, choices=get_pay_unit_choices())
    amount = models.IntegerField('金額')
    start_date = models.DateField('有効期間開始日', blank=True, null=True)
    end_date = models.DateField('有効期間終了日', blank=True, null=True)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_grade'
        verbose_name = 'スタッフ等級'
        verbose_name_plural = 'スタッフ等級'
        ordering = ['display_order', 'code']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


class StaffContactType(MyTenantModel):
    """
    スタッフ連絡種別マスタ
    """
    name = models.CharField('名称', max_length=100)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    def clean(self):
        super().clean()
        original = None
        if self.pk:
            try:
                original = StaffContactType.objects.get(pk=self.pk)
            except StaffContactType.DoesNotExist:
                pass

        if original:
            if original.display_order == 50 and self.display_order != 50:
                raise ValidationError('表示順が50のデータは変更できません。')
            if original.display_order != 50 and self.display_order == 50:
                raise ValidationError('表示順を50に設定することはできません。')
        # We allow creation (no original) with display_order=50 at the model level
        # to support initial data loading from fixtures. The restriction for users
        # adding order 50 is enforced at the Form level.

    def delete(self, *args, **kwargs):
        if self.display_order == 50:
            raise ValidationError('表示順が50のデータは削除できません。')
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.clean()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'apps_master_staff_contact_type'
        verbose_name = 'スタッフ連絡種別'
        verbose_name_plural = 'スタッフ連絡種別'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name
