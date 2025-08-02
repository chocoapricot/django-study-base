from django import forms
from django.db import models
from django.conf import settings

from apps.common.models import MyModel

# Create your models here.
class Dropdowns(MyModel):
#class Dropdowns(models.Model):

    category = models.CharField('カテゴリ',max_length=50, default='')  # カテゴリーを文字列として管理
    name = models.CharField('表示名',max_length=100)  # 表示名
    value = models.CharField('設定値',max_length=100)  # 実際の設定値
    disp_seq = models.PositiveIntegerField('表示順',default=0)  # 表示順
    active = models.BooleanField('有効',default=True)  # 表示非表示

    class Meta:
        ordering = ['category','disp_seq']  # 表示順に並べる
        db_table = 'apps_system_dropdowns'  # 既存のテーブル名を指定
        verbose_name = 'プルダウン'
        verbose_name_plural = 'プルダウン'

    def __str__(self):
        return self.name


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