from django.db import models
from ..common.models import MyModel


class PhraseTemplateTitle(MyModel):
    """
    汎用文言タイトルを管理するモデル。
    admin画面からのみ操作可能。
    """
    
    FORMAT_CHOICES = [
        ('text', 'テキスト'),
        ('textarea', 'テキストエリア'),
    ]
    
    key = models.CharField(
        '参照キー',
        max_length=50,
        unique=True,
        help_text='プログラムから参照するためのキーを入力してください（英数字とアンダースコアのみ）'
    )
    name = models.CharField(
        '名称',
        max_length=100,
        help_text='文言タイトルの名称を入力してください'
    )
    description = models.TextField(
        '補足',
        blank=True,
        null=True,
        help_text='文言タイトルの補足説明を入力してください（任意）'
    )
    format_type = models.CharField(
        '書式',
        max_length=10,
        choices=FORMAT_CHOICES,
        default='text',
        help_text='入力フィールドの書式を選択してください'
    )
    is_active = models.BooleanField(
        '状態',
        default=True,
        help_text='有効な文言タイトルかどうかを設定してください'
    )
    display_order = models.PositiveIntegerField(
        '表示順',
        default=0,
        help_text='表示順序を設定してください（小さい数字が先に表示されます）'
    )

    class Meta:
        db_table = 'apps_master_phrase_template_title'
        verbose_name = '汎用文言タイトル'
        verbose_name_plural = '汎用文言タイトル'
        ordering = ['display_order', 'id']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def get_active_list(cls):
        """有効な文言タイトルを表示順で取得"""
        return cls.objects.filter(is_active=True).order_by('display_order', 'id')
    
    @classmethod
    def get_by_key(cls, key):
        """参照キーで文言タイトルを取得"""
        try:
            return cls.objects.get(key=key, is_active=True)
        except cls.DoesNotExist:
            return None


class PhraseTemplate(MyModel):
    """
    汎用文言テンプレートを管理するモデル。
    各種非加入理由などの定型文を管理する。
    """
    
    title = models.ForeignKey(
        PhraseTemplateTitle,
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name='文言タイトル',
        help_text='文言のタイトルを選択してください'
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
        ordering = ['title__display_order', 'display_order', 'id']
        indexes = [
            models.Index(fields=['title', 'is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"{self.title.name} - {self.content[:50]}{'...' if len(self.content) > 50 else ''}"

    @classmethod
    def get_active_by_title(cls, title):
        """指定されたタイトルの有効な文言を表示順で取得"""
        return cls.objects.filter(
            title=title,
            is_active=True
        ).order_by('display_order', 'id')
    
    @classmethod
    def get_active_by_title_key(cls, title_key):
        """指定されたタイトルキーの有効な文言を表示順で取得"""
        return cls.objects.filter(
            title__key=title_key,
            title__is_active=True,
            is_active=True
        ).order_by('display_order', 'id')