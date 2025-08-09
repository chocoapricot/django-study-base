from django.db import models
from apps.common.models import MyModel


class Qualification(MyModel):
    """資格マスター（階層構造対応）"""
    
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
        if self.level == 1:  # カテゴリの場合は子資格の合計
            from apps.staff.models import StaffQualification
            child_qualifications = self.children.filter(is_active=True)
            return StaffQualification.objects.filter(qualification__in=child_qualifications).count()
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
    """技能マスター（階層構造対応）"""
    
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
        if self.level == 1:  # カテゴリの場合は子技能の合計
            from apps.staff.models import StaffSkill
            child_skills = self.children.filter(is_active=True)
            return StaffSkill.objects.filter(skill__in=child_skills).count()
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