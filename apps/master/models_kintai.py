from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import MyModel
from apps.common.constants import (
    Constants,
    get_time_rounding_unit_choices,
    get_time_rounding_method_choices,
    get_break_input_choices
)


class TimePunch(MyModel):
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
        default=Constants.TIME_ROUNDING_UNIT.ONE_MINUTE,
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
        default=Constants.TIME_ROUNDING_UNIT.ONE_MINUTE,
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
        default=Constants.TIME_ROUNDING_UNIT.ONE_MINUTE,
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
        default=Constants.TIME_ROUNDING_UNIT.ONE_MINUTE,
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
        
        # 開始・終了時刻の設定を比較
        if (self.start_time_unit == self.end_time_unit and 
            self.start_time_method == self.end_time_method):
            # 同じ設定の場合はまとめて表示
            summary.append(f"開始終了: {self.start_time_unit}分{self.get_start_time_method_display()}")
        else:
            # 異なる設定の場合は個別に表示
            summary.append(f"開始: {self.start_time_unit}分{self.get_start_time_method_display()}")
            summary.append(f"終了: {self.end_time_unit}分{self.get_end_time_method_display()}")
        
        if self.break_input:
            # 休憩開始・終了時刻の設定を比較
            if (self.break_start_unit == self.break_end_unit and 
                self.break_start_method == self.break_end_method):
                # 同じ設定の場合はまとめて表示
                summary.append(f"休憩: {self.break_start_unit}分{self.get_break_start_method_display()}")
            else:
                # 異なる設定の場合は個別に表示
                summary.append(f"休憩開始: {self.break_start_unit}分{self.get_break_start_method_display()}")
                summary.append(f"休憩終了: {self.break_end_unit}分{self.get_break_end_method_display()}")
        else:
            summary.append("休憩: 入力なし")
        
        return " / ".join(summary)


class OvertimePattern(MyModel):
    """
    時間外算出パターンマスタ
    """
    name = models.CharField('名称', max_length=100)
    calculate_midnight_premium = models.BooleanField('深夜割増を計算する', default=False)
    memo = models.TextField('メモ', blank=True, null=True)

    # 計算方式選択
    CALCULATION_TYPE_CHOICES = [
        ('premium', '割増'),
        ('monthly_range', '月単位時間範囲'),
        ('variable', '1ヶ月単位変形労働'),
        ('flextime', '1ヶ月単位フレックス'),
    ]
    calculation_type = models.CharField('計算方式', max_length=20, choices=CALCULATION_TYPE_CHOICES, default='premium')

    # 割増方式の設定
    daily_overtime_enabled = models.BooleanField('日単位時間外計算', default=False)
    daily_overtime_hours = models.IntegerField('日単位時間外時間', default=8, blank=True, null=True)
    daily_overtime_minutes = models.IntegerField('日単位時間外分', default=0, blank=True, null=True)

    weekly_overtime_enabled = models.BooleanField('週単位時間外計算', default=False)
    weekly_overtime_hours = models.IntegerField('週単位時間外時間', default=40, blank=True, null=True)
    weekly_overtime_minutes = models.IntegerField('週単位時間外分', default=0, blank=True, null=True)

    monthly_overtime_enabled = models.BooleanField('月単位時間外割増', default=False)
    monthly_overtime_hours = models.IntegerField('月単位時間外割増時間', default=60, blank=True, null=True)

    monthly_estimated_enabled = models.BooleanField('月単位見込み残業', default=False)
    monthly_estimated_hours = models.IntegerField('月単位見込み残業時間', default=20, blank=True, null=True)

    # 月単位時間範囲方式の設定
    monthly_range_min = models.IntegerField('月単位時間範囲最小', default=140, blank=True, null=True)
    monthly_range_max = models.IntegerField('月単位時間範囲最大', default=160, blank=True, null=True)

    # 1ヶ月単位変形労働の設定（28日～31日の基準時間）
    # 注: 日単位・週単位時間外計算は上記の共通フィールド（daily_overtime_*, weekly_overtime_*）を使用
    days_28_hours = models.IntegerField('28日時間', default=160)
    days_28_minutes = models.IntegerField('28日分', default=0)
    days_29_hours = models.IntegerField('29日時間', default=165)
    days_29_minutes = models.IntegerField('29日分', default=42)
    days_30_hours = models.IntegerField('30日時間', default=171)
    days_30_minutes = models.IntegerField('30日分', default=25)
    days_31_hours = models.IntegerField('31日時間', default=177)
    days_31_minutes = models.IntegerField('31日分', default=8)

    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_overtime_pattern'
        verbose_name = '時間外算出パターン'
        verbose_name_plural = '時間外算出パターン'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name
