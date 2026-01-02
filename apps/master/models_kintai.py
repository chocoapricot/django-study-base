from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import MyModel
from apps.common.constants import (
    Constants,
    get_time_rounding_unit_choices,
    get_time_rounding_method_choices,
    get_break_input_choices
)


class TimeRounding(MyModel):
    """時間丸めマスタ"""
    
    name = models.CharField(
        max_length=100,
        verbose_name='名称',
        help_text='時間丸め設定の名称'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='説明',
        help_text='設定の詳細説明'
    )
    
    # 開始時刻丸め設定
    start_time_unit = models.IntegerField(
        choices=get_time_rounding_unit_choices(),
        default=Constants.TIME_ROUNDING_UNIT.FIFTEEN_MINUTES,
        verbose_name='開始時刻丸め単位',
        help_text='開始時刻の丸め単位（分）'
    )
    
    start_time_method = models.CharField(
        max_length=10,
        choices=get_time_rounding_method_choices(),
        default=Constants.TIME_ROUNDING_METHOD.ROUND,
        verbose_name='開始時刻端数処理',
        help_text='開始時刻の端数処理方法'
    )
    
    # 終了時刻丸め設定
    end_time_unit = models.IntegerField(
        choices=get_time_rounding_unit_choices(),
        default=Constants.TIME_ROUNDING_UNIT.FIFTEEN_MINUTES,
        verbose_name='終了時刻丸め単位',
        help_text='終了時刻の丸め単位（分）'
    )
    
    end_time_method = models.CharField(
        max_length=10,
        choices=get_time_rounding_method_choices(),
        default=Constants.TIME_ROUNDING_METHOD.ROUND,
        verbose_name='終了時刻端数処理',
        help_text='終了時刻の端数処理方法'
    )
    
    # 休憩設定
    break_input = models.BooleanField(
        default=True,
        verbose_name='休憩入力',
        help_text='休憩時間を入力するかどうか'
    )
    
    # 休憩開始時刻丸め設定
    break_start_unit = models.IntegerField(
        choices=get_time_rounding_unit_choices(),
        default=Constants.TIME_ROUNDING_UNIT.FIFTEEN_MINUTES,
        verbose_name='休憩開始時刻丸め単位',
        help_text='休憩開始時刻の丸め単位（分）'
    )
    
    break_start_method = models.CharField(
        max_length=10,
        choices=get_time_rounding_method_choices(),
        default=Constants.TIME_ROUNDING_METHOD.ROUND,
        verbose_name='休憩開始時刻端数処理',
        help_text='休憩開始時刻の端数処理方法'
    )
    
    # 休憩終了時刻丸め設定
    break_end_unit = models.IntegerField(
        choices=get_time_rounding_unit_choices(),
        default=Constants.TIME_ROUNDING_UNIT.FIFTEEN_MINUTES,
        verbose_name='休憩終了時刻丸め単位',
        help_text='休憩終了時刻の丸め単位（分）'
    )
    
    break_end_method = models.CharField(
        max_length=10,
        choices=get_time_rounding_method_choices(),
        default=Constants.TIME_ROUNDING_METHOD.ROUND,
        verbose_name='休憩終了時刻端数処理',
        help_text='休憩終了時刻の端数処理方法'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効',
        help_text='この設定を有効にするかどうか'
    )
    
    sort_order = models.IntegerField(
        default=0,
        verbose_name='表示順',
        help_text='一覧での表示順序'
    )
    
    class Meta:
        db_table = 'apps_master_time_rounding'
        verbose_name = '時間丸めマスタ'
        verbose_name_plural = '時間丸めマスタ'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_rounding_summary(self):
        """丸め設定の概要を返す"""
        summary = []
        summary.append(f"開始: {self.start_time_unit}分{self.get_start_time_method_display()}")
        summary.append(f"終了: {self.end_time_unit}分{self.get_end_time_method_display()}")
        
        if self.break_input:
            summary.append(f"休憩開始: {self.break_start_unit}分{self.get_break_start_method_display()}")
            summary.append(f"休憩終了: {self.break_end_unit}分{self.get_break_end_method_display()}")
        else:
            summary.append("休憩: 入力なし")
        
        return " / ".join(summary)