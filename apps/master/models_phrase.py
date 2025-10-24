from django.db import models
from ..common.models import MyModel


class PhraseTemplate(MyModel):
    """
    汎用文言テンプレートを管理するモデル。
    各種非加入理由などの定型文を管理する。
    """
    
    CATEGORY_CHOICES = [
        ('health_insurance_non_enrollment', '健保非加入理由'),
        ('pension_insurance_non_enrollment', '厚年非加入理由'),
        ('employment_insurance_non_enrollment', '雇保非加入理由'),
    ]
    
    category = models.CharField(
        '分類',
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text='文言の分類を選択してください'
    )
    content = models.TextField(
        '内容',
        help_text='文言の内容を入力してください'
    )
    is_active = models.BooleanField(
        '状態',
        default=True,
        help_text='有効な文言かどうかを設定してください'
    )
    display_order = models.PositiveIntegerField(
        '表示順',
        default=0,
        help_text='表示順序を設定してください（小さい数字が先に表示されます）'
    )

    class Meta:
        db_table = 'apps_master_phrase_template'
        verbose_name = '汎用文言テンプレート'
        verbose_name_plural = '汎用文言テンプレート'
        ordering = ['category', 'display_order', 'id']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.content[:50]}{'...' if len(self.content) > 50 else ''}"

    @classmethod
    def get_active_by_category(cls, category):
        """指定された分類の有効な文言を表示順で取得"""
        return cls.objects.filter(
            category=category,
            is_active=True
        ).order_by('display_order', 'id')