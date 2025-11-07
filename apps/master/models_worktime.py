from django.db import models
from apps.common.models import MyModel
from .models_phrase import PhraseTemplate


class WorkTimePattern(MyModel):
    """
    就業時間パターンマスタ
    """
    name = models.CharField('名称', max_length=100)
    memo = models.TextField('メモ', blank=True, null=True)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_worktime_pattern'
        verbose_name = '就業時間パターン'
        verbose_name_plural = '就業時間パターン'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


class WorkTimePatternWork(MyModel):
    """
    就業時間パターン勤務時間
    """
    worktime_pattern = models.ForeignKey(
        WorkTimePattern,
        on_delete=models.CASCADE,
        verbose_name='就業時間パターン',
        related_name='work_times'
    )
    time_name = models.ForeignKey(
        PhraseTemplate,
        on_delete=models.PROTECT,
        verbose_name='時間名称',
        related_name='worktime_pattern_works',
        limit_choices_to={'title__key': 'WORKTIME_NAME', 'is_active': True}
    )
    start_time = models.TimeField('開始時刻')
    start_time_next_day = models.BooleanField('開始時刻翌日', default=False, help_text='開始時刻が翌日の場合にチェック')
    end_time = models.TimeField('終了時刻')
    end_time_next_day = models.BooleanField('終了時刻翌日', default=False, help_text='終了時刻が翌日の場合にチェック')
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_worktime_pattern_work'
        verbose_name = '就業時間パターン勤務時間'
        verbose_name_plural = '就業時間パターン勤務時間'
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        name_part = f"【{self.time_name.content}】" if self.time_name else ""
        return f"{name_part} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
    
    def get_time_display(self):
        """時刻表示（翌日フラグ考慮）"""
        start = self.start_time.strftime('%H:%M')
        end = self.end_time.strftime('%H:%M')
        return f"{start}-{end}"
    
    def get_full_display(self):
        """完全な表示（名称 + 時刻）"""
        name = self.time_name.content if self.time_name else "未設定"
        return f"{name} {self.get_time_display()}"


class WorkTimePatternBreak(MyModel):
    """
    就業時間パターン休憩時間
    """
    work_time = models.ForeignKey(
        WorkTimePatternWork,
        on_delete=models.CASCADE,
        verbose_name='勤務時間',
        related_name='break_times'
    )
    start_time = models.TimeField('開始時刻')
    start_time_next_day = models.BooleanField('開始時刻翌日', default=False, help_text='開始時刻が翌日の場合にチェック')
    end_time = models.TimeField('終了時刻')
    end_time_next_day = models.BooleanField('終了時刻翌日', default=False, help_text='終了時刻が翌日の場合にチェック')
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_worktime_pattern_break'
        verbose_name = '就業時間パターン休憩時間'
        verbose_name_plural = '就業時間パターン休憩時間'
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"休憩 {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
