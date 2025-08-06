from django.db import models
from apps.common.models import MyModel


class Qualification(MyModel):
    """資格マスター"""
    
    CATEGORY_CHOICES = [
        ('national', '国家資格'),
        ('public', '公的資格'),
        ('private', '民間資格'),
        ('internal', '社内資格'),
        ('other', 'その他'),
    ]
    
    name = models.CharField('資格名', max_length=100)
    category = models.CharField(
        'カテゴリ', 
        max_length=20, 
        choices=CATEGORY_CHOICES,
        default='private'
    )
    description = models.TextField('説明', blank=True, null=True)
    issuing_organization = models.CharField('発行機関', max_length=100, blank=True, null=True)
    validity_period = models.IntegerField('有効期間（年）', blank=True, null=True, help_text='無期限の場合は空欄')
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)
    
    class Meta:
        db_table = 'apps_master_qualification'
        verbose_name = '資格'
        verbose_name_plural = '資格'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def category_display_name(self):
        """カテゴリの表示名"""
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)
    
    @property
    def has_validity_period(self):
        """有効期間があるかどうか"""
        return self.validity_period is not None


class Skill(MyModel):
    """技能マスター"""
    
    LEVEL_CHOICES = [
        ('beginner', '初級'),
        ('intermediate', '中級'),
        ('advanced', '上級'),
        ('expert', 'エキスパート'),
    ]
    
    name = models.CharField('技能名', max_length=100)
    category = models.CharField('カテゴリ', max_length=50, blank=True, null=True)
    description = models.TextField('説明', blank=True, null=True)
    required_level = models.CharField(
        '必要レベル',
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner',
        help_text='この技能に求められる最低レベル'
    )
    is_active = models.BooleanField('有効', default=True)
    display_order = models.IntegerField('表示順', default=0)
    
    class Meta:
        db_table = 'apps_master_skill'
        verbose_name = '技能'
        verbose_name_plural = '技能'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def required_level_display_name(self):
        """必要レベルの表示名"""
        return dict(self.LEVEL_CHOICES).get(self.required_level, self.required_level)