from django.db import models
from ...common.models import MyModel

# Create your models here.
class Menu(MyModel):

    name = models.CharField('表示名',max_length=100)  # 表示名
    url  = models.CharField('URL',max_length=100)  # 実際の設定値
    icon = models.CharField('アイコン',max_length=100)  # 実際の設定値
    icon_style = models.CharField('アイコンスタイル',max_length=100)  # 実際の設定値
    disp_seq = models.PositiveIntegerField('表示順',default=0)  # 表示順
    active = models.BooleanField('有効',default=True)  # 表示非表示

    class Meta:
        ordering = ['disp_seq']  # 表示順に並べる
        db_table = 'apps_system_menu'  # 既存のテーブル名を指定
        verbose_name = 'メニュー'
        verbose_name_plural = 'メニュー'

    def __str__(self):
        return self.name