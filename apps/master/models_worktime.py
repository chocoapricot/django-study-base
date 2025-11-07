from django.db import models
from apps.common.models import MyModel


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
    time_name = models.CharField('時間名称', max_length=100, blank=True, null=True, help_text='例：日勤、準夜勤、夜勤')
    start_time = models.TimeField('開始時刻')
    end_time = models.TimeField('終了時刻')
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
        name_part = f"【{self.time_name}】" if self.time_name else ""
        return f"{name_part} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"


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
    time_name = models.CharField('時間名称', max_length=100, blank=True, null=True, help_text='例：休憩１、休憩２')
    start_time = models.TimeField('開始時刻')
    end_time = models.TimeField('終了時刻')
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
        name_part = f"【{self.time_name}】" if self.time_name else ""
        return f"休憩{name_part} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
