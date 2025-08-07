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


class Skill(MyModel):
    """技能マスター"""
    
    name = models.CharField('技能名', max_length=100)
    category = models.CharField('カテゴリ', max_length=50, blank=True, null=True)
    description = models.TextField('説明', blank=True, null=True)
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