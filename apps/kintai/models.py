from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import MyModel
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from django.contrib.auth import get_user_model
from datetime import date, time, datetime, timedelta
from calendar import monthrange
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
    target_month = models.DateField('対象年月', help_text='対象年月の1日を設定してください。')
    
    # 勤怠集計情報
    total_work_days = models.PositiveIntegerField('出勤日数', default=0)
    total_work_hours = models.DecimalField('総労働時間', max_digits=6, decimal_places=2, default=0)
    total_overtime_hours = models.DecimalField('残業時間', max_digits=6, decimal_places=2, default=0)
    total_late_night_overtime_hours = models.DecimalField('深夜時間', max_digits=6, decimal_places=2, default=0)
    total_holiday_work_hours = models.DecimalField('休日労働時間', max_digits=6, decimal_places=2, default=0)
    # 遅刻・早退は個別の集計対象から除外
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

    class Meta:
        db_table = 'apps_kintai_staff_timesheet'
        verbose_name = '月次勤怠'
        verbose_name_plural = '月次勤怠'
        unique_together = ['staff_contract', 'target_month']
        ordering = ['-target_month', 'staff__name_last', 'staff__name_first']
        indexes = [
            models.Index(fields=['staff_contract']),
            models.Index(fields=['staff']),
            models.Index(fields=['target_month']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        if self.target_month:
            return f"{self.staff} - {self.target_month.year}年{self.target_month.month}月"
        return f"{self.staff} - (年月未設定)"

    def clean(self):
        """バリデーション"""
        # target_month が月の1日であるかチェック
        if self.target_month and self.target_month.day != 1:
            raise ValidationError({'target_month': '対象年月は月の1日を設定してください。'})
        
        # スタッフ契約とスタッフの整合性チェック
        if self.staff_contract_id and self.staff_id:
            if self.staff_contract.staff_id != self.staff_id:
                raise ValidationError('スタッフ契約とスタッフが一致しません。')

        # スタッフ契約の契約期間内かチェック
        if getattr(self, 'staff_contract_id', None) and self.target_month:
            try:
                _, last_day_num = monthrange(self.target_month.year, self.target_month.month)
                last_day = date(self.target_month.year, self.target_month.month, last_day_num)
            except (ValueError, TypeError):
                last_day = None

            if self.target_month and last_day:
                try:
                    sc = self.staff_contract
                except Exception:
                    sc = None

                if sc:
                    sc_start = sc.start_date
                    sc_end = sc.end_date

                    if sc_start and last_day < sc_start:
                        raise ValidationError('指定した年月はスタッフ契約の契約期間外です。')

                    if sc_end and self.target_month > sc_end:
                        raise ValidationError('指定した年月はスタッフ契約の契約期間外です。')

    def save(self, *args, **kwargs):
        # target_month を常にその月の1日に設定
        if self.target_month:
            self.target_month = self.target_month.replace(day=1)
            
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
        self.total_late_night_overtime_hours = sum(tc.late_night_overtime_hours or 0 for tc in timecards)
        self.total_holiday_work_hours = sum(tc.holiday_work_hours or 0 for tc in timecards)
    # 遅刻・早退の集計は廃止（個別timecardの値は残るが月次の集計フィールドは削除）
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
    def total_late_night_overtime_hours_display(self):
        """深夜時間の表示用文字列"""
        if self.total_late_night_overtime_hours and self.total_late_night_overtime_hours > 0:
            hours = int(self.total_late_night_overtime_hours)
            minutes = int((self.total_late_night_overtime_hours - hours) * 60)
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
    start_time_next_day = models.BooleanField('出勤時刻翌日', default=False)
    end_time = models.TimeField('退勤時刻', blank=True, null=True)
    end_time_next_day = models.BooleanField('退勤時刻翌日', default=False)
    break_minutes = models.PositiveIntegerField('休憩時間（分）', default=0)
    
    # 計算結果
    work_hours = models.DecimalField('労働時間', max_digits=5, decimal_places=2, default=0, help_text='実労働時間（時間）')
    overtime_hours = models.DecimalField('残業時間', max_digits=5, decimal_places=2, default=0, help_text='残業時間（時間）')
    late_night_overtime_hours = models.DecimalField('深夜時間', max_digits=5, decimal_places=2, default=0, help_text='深夜残業時間（時間）')
    holiday_work_hours = models.DecimalField('休日労働時間', max_digits=5, decimal_places=2, default=0, help_text='休日労働時間（時間）')
    # 遅刻・早退は個別フィールドとして保持しない（UI/集計上は不要のため削除）
    
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
            
            # 退勤時刻が出勤時刻より前の場合はエラー（翌日フラグを考慮）
            # 翌日フラグがない場合のみチェック
            if not self.start_time_next_day and not self.end_time_next_day:
                if self.start_time >= self.end_time:
                    raise ValidationError('退勤時刻は出勤時刻より後の時刻を入力してください。')
        
        # 有給休暇の場合は日数が必須
        if self.work_type == '40':  # 有給休暇
            if not self.paid_leave_days or self.paid_leave_days <= 0:
                raise ValidationError('有給休暇の場合は有給休暇日数を入力してください。')

        # timesheet と staff_contract が有る場合、勤務日が契約期間内かチェック
        try:
            if self.timesheet and self.work_date:
                sc = None
                try:
                    sc = self.timesheet.staff_contract
                except:
                    sc = None

                if sc:
                    sc_start = sc.start_date
                    sc_end = sc.end_date
                    if sc_start and self.work_date < sc_start:
                        raise ValidationError('勤務日はスタッフ契約の契約期間外です。')
                    if sc_end and self.work_date > sc_end:
                        raise ValidationError('勤務日はスタッフ契約の契約期間外です。')
        except ValidationError:
            raise
        except Exception:
            # 予期しない例外はバリデーションで無視しておく（他のチェックで捕捉される）
            pass

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
            self.late_night_overtime_hours = 0
            self.holiday_work_hours = 0
            return

        # 勤務時間を計算（分単位）
        from datetime import datetime, timedelta
        start_dt = datetime.combine(date.today(), self.start_time)
        end_dt = datetime.combine(date.today(), self.end_time)
        
        # 翌日フラグを考慮
        if self.start_time_next_day:
            start_dt += timedelta(days=1)
        if self.end_time_next_day:
            end_dt += timedelta(days=1)
        
        # 日をまたぐ場合の処理（翌日フラグがない場合）
        if not self.start_time_next_day and not self.end_time_next_day and end_dt <= start_dt:
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
        
        # 深夜残業時間（22:00-05:00）を計算
        late_night_start = time(22, 0)
        late_night_end = time(5, 0)

        # start_dt と end_dt が datetime オブジェクトであることを確認
        if isinstance(start_dt, datetime) and isinstance(end_dt, datetime):
            # 深夜時間帯の開始時刻と終了時刻を計算
            # パターン1: 勤務開始日の22:00
            ln_start1 = datetime.combine(start_dt.date(), late_night_start)
            # パターン2: 勤務終了日の5:00
            ln_end1 = datetime.combine(end_dt.date(), late_night_end)
            # パターン3: 勤務開始日の翌日5:00
            ln_end2 = datetime.combine(start_dt.date() + timedelta(days=1), late_night_end)
            # パターン4: 勤務終了日の22:00（これは深夜時間帯の開始なので計算には使わない）

            # 深夜時間の重複部分を計算
            late_night_minutes = 0

            # 勤務時間帯と深夜時間帯の重複を計算
            # 1. start_dt.date()の22:00から翌5:00まで
            overlap_start1 = max(start_dt, ln_start1)
            overlap_end1 = min(end_dt, ln_end2)
            if overlap_end1 > overlap_start1:
                late_night_minutes += (overlap_end1 - overlap_start1).total_seconds() / 60

            # 2. end_dt.date()がstart_dt.date()より後の場合、その日の0:00から5:00まで
            if end_dt.date() > start_dt.date():
                ln_start2 = datetime.combine(end_dt.date(), time(0, 0))
                overlap_start2 = max(start_dt, ln_start2)
                overlap_end2 = min(end_dt, ln_end1)
                if overlap_end2 > overlap_start2:
                    # こちらのロジックは複雑になるため、よりシンプルなアプローチを採用
                    # 1分ずつチェックする方法で堅牢性を担保
                    pass

        # 1分ずつチェックする堅牢な方法
        late_night_minutes = 0
        current_time = start_dt
        while current_time < end_dt:
            # 休憩時間は深夜労働に含めない
            # ただし、休憩時間がいつ取られたかの情報がないため、ここでは考慮しない
            # 最終的な労働時間から按分するなどの方法もあるが、一旦総労働時間で計算

            # 現在時刻が深夜時間帯かどうか
            t = current_time.time()
            if t >= late_night_start or t < late_night_end:
                late_night_minutes += 1

            current_time += timedelta(minutes=1)

        # 休憩時間を深夜時間から差し引く（労働時間に比例して按分）
        if total_minutes > 0:
            late_night_work_minutes = late_night_minutes - (self.break_minutes * (late_night_minutes / total_minutes))
        else:
            late_night_work_minutes = 0

        self.late_night_overtime_hours = Decimal(late_night_work_minutes) / Decimal(60)

        # 休日労働時間（休日出勤の場合）
        if self.work_date.weekday() >= 5:  # 土日
            self.holiday_work_hours = self.work_hours
        else:
            self.holiday_work_hours = 0
        
        # 遅刻・早退の計算（9:00-18:00を基準とする）
        standard_start = datetime.combine(date.today(), time(9, 0))
        standard_end = datetime.combine(date.today(), time(18, 0))
        
        # 遅刻・早退の計算は表示要件に応じてフロント側で扱うためモデル内計算は行わない

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
    def late_night_overtime_hours_display(self):
        """深夜時間の表示用文字列"""
        if self.late_night_overtime_hours and self.late_night_overtime_hours > 0:
            hours = int(self.late_night_overtime_hours)
            minutes = int((self.late_night_overtime_hours - hours) * 60)
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
