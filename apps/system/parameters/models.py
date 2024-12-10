from django.db import models
from ...common.models import MyModel

class Parameter(MyModel):

    category = models.CharField('分類',max_length=50, default='')  # カテゴリー
    key = models.CharField('キー',max_length=100)  # 表示名
    value = models.CharField('設定値',max_length=100)  # 実際の設定値
    default_value = models.CharField('初期値',max_length=100)  # 実際の設定値
    note  = models.CharField('備考',max_length=100)  # 実際の設定値
    disp_seq = models.PositiveIntegerField('表示順',default=0)  # 表示順
    active = models.BooleanField('有効',default=True)  # 表示非表示

    class Meta:
        ordering = ['category','disp_seq']  # 表示順に並べる
        db_table = 'apps_system_parameter'  # 既存のテーブル名を指定
        verbose_name = 'パラメータ'
        verbose_name_plural = 'パラメータ'

    def __str__(self):
        return self.key