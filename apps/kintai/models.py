from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import MyModel
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from django.contrib.auth import get_user_model
from datetime import date, time, datetime, timedelta
from decimal import Decimal

User = get_user_model()


class StaffTimesheet(MyModel):
    """
    月次勤怠情報を管理するモデル。
    スタッフ契約に対して毎月作成される。
    """
    staff_contract = models.ForeignKey(
        StaffContract,
        on_delete=models.CASCADE,
        related_name='timesheets',
        verbose_name='スタッフ契約'
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='timesheets',
        verbose_name='スタッフ'
    )
    year = models.PositiveIntegerField('年', help_text='対象年（例：2025）')
    month = models.PositiveIntegerField('月', help_text='対象月（1-12）')
    
    # 勤怠集計情報
    total_work_days = models.PositiveIntegerField('出勤日数', default=0)
    total_work_hours = models.DecimalField('総労働時間', max_digits=6, decimal_places=2, default=0)
    total_overtime_hours = models.DecimalField('残業時間', max_digits=6, decimal_places=2, default=0)
    total_holiday_work_hours = models.DecimalField('休日労働時間', max_digits=6, decimal_places=2, default=0)
    total_late_minutes = models.PositiveIntegerField('遅刻時間（分）', default=0)
    total_early_leave_minutes = models.PositiveIntegerField('早退時間（分）', default=0)
    total_absence_days = models.PositiveIntegerField('欠勤日数', default=0)
    total_paid_leave_days = models.DecimalField('有給休暇日数', max_digits=4, decimal_places=1, default=0)
    
    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=2,
        choices=[
            ('10', '作成中'),
            ('20', '提出済み'),
            ('30', '承認済み'),
            ('40', '差戻し'),
        ],
        default='10'
    )
    
    # 提出・承認情報
    submitted_at = models.DateTimeField('提出日時', blank=True, null=True)
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_timesheets',
        verbose_name='提出者'
    )
    approved_at = models.DateTimeField('承認日時', blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_timesheets',
        verbose_name='承認者'
    )
    rejected_at = models.DateTimeField('差戻し日時', blank=True, null=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_timesheets',
        verbose_name='差戻し者'
    )
    rejection_reason = models.TextField('差戻し理由', blank=True, null=True)
    
    # 備考
    memo = models.TextField('メモ', blank=True, null=True)

    class Meta:
        db_table = 'apps_kintai_staff_timesheet'
        verbose_name = '月次勤怠'
        verbose_name_plural = '月次勤怠'
        unique_together = ['staff_contract', 'year', 'month']
        ordering = ['-year', '-month', 'staff__name_last', 'staff__name_first']
        indexes = [
            models.Index(fields=['staff_contract']),
            models.Index(fields=['staff']),
            models.Index(fields=['year', 'month']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.staff} - {self.year}年{self.month}月"

    def clean(self):
        """バリデーション"""
        # 月の範囲チェック
        if self.month is not None and (self.month < 1 or self.month > 12):
            raise ValidationError('月は1から12の範囲で入力してください。')
        
        # スタッフ契約とスタッフの整合性チェック
        if self.staff_contract_id and self.staff_id:
            if self.staff_contract.staff_id != self.staff_id:
                raise ValidationError('スタッフ契約とスタッフが一致しません。')

    def save(self, *args, **kwargs):
        # スタッフ契約からスタッフを自動設定
        if self.staff_contract:
            try:
                if not self.staff_id:
                    self.staff = self.staff_contract.staff
            except:
                self.staff = self.staff_contract.staff
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """日次勤怠データから集計値を計算する"""
        timecards = self.timecards.all()
        
        self.total_work_days = timecards.filter(work_type='10').count()
        self.total_work_hours = sum(tc.work_hours or 0 for tc in timecards)
        self.total_overtime_hours = sum(tc.overtime_hours or 0 for tc in timecards)
        self.total_holiday_work_hours = sum(tc.holiday_work_hours or 0 for tc in timecards)
        self.total_late_minutes = sum(tc.late_minutes or 0 for tc in timecards)
        self.total_early_leave_minutes = sum(tc.early_leave_minutes or 0 for tc in timecards)
        self.total_absence_days = timecards.filter(work_type='30').count()
        self.total_paid_leave_days = sum(tc.paid_leave_days or 0 for tc in timecards)
        
        self.save()

    @property
    def is_editable(self):
        """編集可能かどうか"""
        return self.status in ['10', '40']  # 作成中または差戻し

    @property
    def is_submitted(self):
        """提出済みかどうか"""
        return self.status in ['20', '30']  # 提出済みまたは承認済み

    @property
    def is_approved(self):
        """承認済みかどうか"""
        return self.status == '30'
    
    @property
    def total_work_hours_display(self):
        """総労働時間の表示用文字列"""
        if self.total_work_hours:
            hours = int(self.total_work_hours)
            minutes = int((self.total_work_hours - hours) * 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"
    
    @property
    def total_overtime_hours_display(self):
        """残業時間の表示用文字列"""
        if self.total_overtime_hours and self.total_overtime_hours > 0:
            hours = int(self.total_overtime_hours)
            minutes = int((self.total_overtime_hours - hours) * 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"
    
    @property
    def total_holiday_work_hours_display(self):
        """休日労働時間の表示用文字列"""
        if self.total_holiday_work_hours and self.total_holiday_work_hours > 0:
            hours = int(self.total_holiday_work_hours)
            minutes = int((self.total_holiday_work_hours - hours) * 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"


class StaffTimecard(MyModel):
    """
    日次勤怠情報を管理するモデル。
    月次勤怠（StaffTimesheet）に紐づく。
    """
    timesheet = models.ForeignKey(
        StaffTimesheet,
        on_delete=models.CASCADE,
        related_name='timecards',
        verbose_name='月次勤怠'
    )
    work_date = models.DateField('勤務日')
    
    # 勤務区分
    work_type = models.CharField(
        '勤務区分',
        max_length=2,
        choices=[
            ('10', '出勤'),
            ('20', '休日'),
            ('30', '欠勤'),
            ('40', '有給休暇'),
            ('50', '特別休暇'),
            ('60', '代休'),
            ('70', '稼働無し'),
        ],
        default='10'
    )
    
    # 勤務時間
    start_time = models.TimeField('出勤時刻', blank=True, null=True)
    end_time = models.TimeField('退勤時刻', blank=True, null=True)
    break_minutes = models.PositiveIntegerField('休憩時間（分）', default=0)
    
    # 計算結果
    work_hours = models.DecimalField('労働時間', max_digits=5, decimal_places=2, default=0, help_text='実労働時間（時間）')
    overtime_hours = models.DecimalField('残業時間', max_digits=5, decimal_places=2, default=0, help_text='残業時間（時間）')
    holiday_work_hours = models.DecimalField('休日労働時間', max_digits=5, decimal_places=2, default=0, help_text='休日労働時間（時間）')
    late_minutes = models.PositiveIntegerField('遅刻時間（分）', default=0)
    early_leave_minutes = models.PositiveIntegerField('早退時間（分）', default=0)
    
    # 有給休暇
    paid_leave_days = models.DecimalField('有給休暇日数', max_digits=3, decimal_places=1, default=0, help_text='0.5（半休）または1.0（全休）')
    
    # 備考
    memo = models.TextField('メモ', blank=True, null=True)

    class Meta:
        db_table = 'apps_kintai_staff_timecard'
        verbose_name = '日次勤怠'
        verbose_name_plural = '日次勤怠'
        unique_together = ['timesheet', 'work_date']
        ordering = ['work_date']
        indexes = [
            models.Index(fields=['timesheet']),
            models.Index(fields=['work_date']),
            models.Index(fields=['work_type']),
        ]

    def __str__(self):
        return f"{self.timesheet.staff} - {self.work_date}"

    def clean(self):
        """バリデーション"""
        # 出勤の場合は出勤・退勤時刻が必須
        if self.work_type == '10':  # 出勤
            if not self.start_time or not self.end_time:
                raise ValidationError('出勤の場合は出勤時刻と退勤時刻を入力してください。')
            
            # 退勤時刻が出勤時刻より前の場合はエラー
            if self.start_time >= self.end_time:
                raise ValidationError('退勤時刻は出勤時刻より後の時刻を入力してください。')
        
        # 有給休暇の場合は日数が必須
        if self.work_type == '40':  # 有給休暇
            if not self.paid_leave_days or self.paid_leave_days <= 0:
                raise ValidationError('有給休暇の場合は有給休暇日数を入力してください。')

    def save(self, *args, **kwargs):
        # 労働時間を自動計算
        self.calculate_work_hours()
        super().save(*args, **kwargs)

    def calculate_work_hours(self):
        """労働時間を計算する"""
        if self.work_type != '10' or not self.start_time or not self.end_time:
            # 出勤以外または時刻未入力の場合は0
            self.work_hours = 0
            self.overtime_hours = 0
            self.holiday_work_hours = 0
            self.late_minutes = 0
            self.early_leave_minutes = 0
            return

        # 勤務時間を計算（分単位）
        from datetime import datetime, timedelta
        start_dt = datetime.combine(date.today(), self.start_time)
        end_dt = datetime.combine(date.today(), self.end_time)
        
        # 日をまたぐ場合の処理
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        
        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        work_minutes = total_minutes - self.break_minutes
        
        # 労働時間（時間単位、小数点2桁）
        self.work_hours = Decimal(work_minutes) / Decimal(60)
        
        # 所定労働時間（デフォルト8時間）
        standard_hours = 8
        
        # 残業時間を計算
        if self.work_hours > standard_hours:
            self.overtime_hours = self.work_hours - Decimal(standard_hours)
        else:
            self.overtime_hours = 0
        
        # 休日労働時間（休日出勤の場合）
        if self.work_date.weekday() >= 5:  # 土日
            self.holiday_work_hours = self.work_hours
        else:
            self.holiday_work_hours = 0
        
        # 遅刻・早退の計算（9:00-18:00を基準とする）
        standard_start = datetime.combine(date.today(), time(9, 0))
        standard_end = datetime.combine(date.today(), time(18, 0))
        
        if self.start_time > time(9, 0):
            late_dt = datetime.combine(date.today(), self.start_time)
            self.late_minutes = int((late_dt - standard_start).total_seconds() / 60)
        
        if self.end_time < time(18, 0):
            early_dt = datetime.combine(date.today(), self.end_time)
            self.early_leave_minutes = int((standard_end - early_dt).total_seconds() / 60)

    @property
    def is_holiday(self):
        """休日かどうか"""
        return self.work_type in ['20', '40', '50', '60']

    @property
    def is_absence(self):
        """欠勤かどうか"""
        return self.work_type == '30'

    @property
    def work_hours_display(self):
        """労働時間の表示用文字列"""
        if self.work_hours:
            hours = int(self.work_hours)
            minutes = int((self.work_hours - hours) * 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"
    
    @property
    def overtime_hours_display(self):
        """残業時間の表示用文字列"""
        if self.overtime_hours and self.overtime_hours > 0:
            hours = int(self.overtime_hours)
            minutes = int((self.overtime_hours - hours) * 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"
    
    @property
    def holiday_work_hours_display(self):
        """休日労働時間の表示用文字列"""
        if self.holiday_work_hours and self.holiday_work_hours > 0:
            hours = int(self.holiday_work_hours)
            minutes = int((self.holiday_work_hours - hours) * 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"
