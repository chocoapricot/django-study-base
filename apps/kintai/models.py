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
    total_work_minutes = models.PositiveIntegerField('総労働時間（分）', default=0)
    total_overtime_minutes = models.PositiveIntegerField('残業時間（分）', default=0)
    total_late_night_overtime_minutes = models.PositiveIntegerField('深夜時間（分）', default=0)
    total_holiday_work_minutes = models.PositiveIntegerField('休日労働時間（分）', default=0)
    total_premium_minutes = models.PositiveIntegerField('割増時間（分）', default=0, help_text='月単位時間範囲での割増時間')
    total_deduction_minutes = models.PositiveIntegerField('控除時間（分）', default=0, help_text='月単位時間範囲での控除時間')
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
        self.total_work_minutes = sum(tc.work_minutes or 0 for tc in timecards)
        self.total_overtime_minutes = sum(tc.overtime_minutes or 0 for tc in timecards)
        self.total_late_night_overtime_minutes = sum(tc.late_night_overtime_minutes or 0 for tc in timecards)
        self.total_holiday_work_minutes = sum(tc.holiday_work_minutes or 0 for tc in timecards)
        # 遅刻・早退の集計は廃止（個別timecardの値は残るが月次の集計フィールドは削除）
        self.total_absence_days = timecards.filter(work_type='30').count()
        self.total_paid_leave_days = sum(tc.paid_leave_days or 0 for tc in timecards)

        # --- 月単位時間範囲方式の割増・控除時間計算 ---
        self.total_premium_minutes = 0
        self.total_deduction_minutes = 0
        
        if self.staff_contract and self.staff_contract.overtime_pattern:
            overtime_pattern = self.staff_contract.overtime_pattern
            
            if overtime_pattern.calculation_type == 'monthly_range':
                # 月単位時間範囲方式の場合
                monthly_range_min = overtime_pattern.monthly_range_min or 0
                monthly_range_max = overtime_pattern.monthly_range_max or 0
                
                if monthly_range_min > 0 and self.total_work_minutes < monthly_range_min * 60:
                    # 最小時間に満たない場合は控除時間を計算
                    self.total_deduction_minutes = (monthly_range_min * 60) - self.total_work_minutes
                
                if monthly_range_max > 0 and self.total_work_minutes > monthly_range_max * 60:
                    # 最大時間を超える場合は割増時間を計算
                    self.total_premium_minutes = self.total_work_minutes - (monthly_range_max * 60)

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

    # --- Display properties ---
    @property
    def total_work_hours_display(self):
        """総労働時間の表示用文字列"""
        if self.total_work_minutes:
            hours, minutes = divmod(self.total_work_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def total_overtime_hours_display(self):
        """残業時間の表示用文字列"""
        if self.total_overtime_minutes and self.total_overtime_minutes > 0:
            hours, minutes = divmod(self.total_overtime_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def total_late_night_overtime_hours_display(self):
        """深夜時間の表示用文字列"""
        if self.total_late_night_overtime_minutes and self.total_late_night_overtime_minutes > 0:
            hours, minutes = divmod(self.total_late_night_overtime_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def total_holiday_work_hours_display(self):
        """休日労働時間の表示用文字列"""
        if self.total_holiday_work_minutes and self.total_holiday_work_minutes > 0:
            hours, minutes = divmod(self.total_holiday_work_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def total_premium_hours_display(self):
        """割増時間の表示用文字列"""
        if self.total_premium_minutes and self.total_premium_minutes > 0:
            hours, minutes = divmod(self.total_premium_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def total_deduction_hours_display(self):
        """控除時間の表示用文字列"""
        if self.total_deduction_minutes and self.total_deduction_minutes > 0:
            hours, minutes = divmod(self.total_deduction_minutes, 60)
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
        verbose_name='月次勤怠',
        null=True,
        blank=True
    )
    staff_contract = models.ForeignKey(
        StaffContract,
        on_delete=models.CASCADE,
        related_name='timecards_direct',
        verbose_name='スタッフ契約'
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
    late_night_break_minutes = models.PositiveIntegerField('深夜休憩（分）', default=0)

    # 計算結果
    work_minutes = models.PositiveIntegerField('労働時間（分）', default=0, help_text='実労働時間（分）')
    overtime_minutes = models.PositiveIntegerField('残業時間（分）', default=0, help_text='残業時間（分）')
    late_night_overtime_minutes = models.PositiveIntegerField('深夜時間（分）', default=0, help_text='深夜残業時間（分）')
    holiday_work_minutes = models.PositiveIntegerField('休日労働時間（分）', default=0, help_text='休日労働時間（分）')
    # 遅刻・早退は個別フィールドとして保持しない（UI/集計上は不要のため削除）

    # 有給休暇
    paid_leave_days = models.DecimalField('有給休暇日数', max_digits=3, decimal_places=1, default=0, help_text='0.5（半休）または1.0（全休）')

    # 備考
    memo = models.TextField('メモ', blank=True, null=True)

    class Meta:
        db_table = 'apps_kintai_staff_timecard'
        verbose_name = '日次勤怠'
        verbose_name_plural = '日次勤怠'
        unique_together = [['staff_contract', 'work_date']]
        ordering = ['work_date']
        indexes = [
            models.Index(fields=['timesheet']),
            models.Index(fields=['staff_contract']),
            models.Index(fields=['work_date']),
            models.Index(fields=['work_type']),
        ]

    def __str__(self):
        try:
            if self.timesheet and self.timesheet.staff:
                return f"{self.timesheet.staff} - {self.work_date}"
        except:
            pass
        # timesheetが利用できない場合はstaff_contractから取得
        try:
            if self.staff_contract and self.staff_contract.staff:
                return f"{self.staff_contract.staff} - {self.work_date}"
        except:
            pass
        return f"日次勤怠 - {self.work_date}"

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

        # staff_contract が指定されている場合、勤務日が契約期間内かチェック
        if self.staff_contract_id and self.work_date:
            try:
                sc = self.staff_contract
                sc_start = sc.start_date
                sc_end = sc.end_date
                if sc_start and self.work_date < sc_start:
                    raise ValidationError('勤務日はスタッフ契約の契約期間外です。')
                if sc_end and self.work_date > sc_end:
                    raise ValidationError('勤務日はスタッフ契約の契約期間外です。')
            except ValidationError:
                raise
            except Exception:
                pass

        # timesheet と staff_contract の整合性チェック
        if self.timesheet_id and self.staff_contract_id:
            try:
                if self.timesheet.staff_contract_id != self.staff_contract_id:
                    raise ValidationError('月次勤怠のスタッフ契約と日次勤怠のスタッフ契約が一致しません。')
            except ValidationError:
                raise
            except Exception:
                pass

    def save(self, skip_timesheet_update=False, *args, **kwargs):
        # staff_contract が指定されている場合、対応する月次勤怠を自動作成または取得
        if self.staff_contract_id and self.work_date:
            # 対象年月を計算（work_dateの月の1日）
            target_month = self.work_date.replace(day=1)
            
            # 月次勤怠を取得または作成
            timesheet, created = StaffTimesheet.objects.get_or_create(
                staff_contract=self.staff_contract,
                target_month=target_month,
                defaults={
                    'staff': self.staff_contract.staff,
                }
            )
            self.timesheet = timesheet
        
        # 労働時間を自動計算
        self.calculate_work_hours()
        super().save(*args, **kwargs)
        
        # 月次勤怠の集計を更新（skip_timesheet_updateがTrueの場合はスキップ）
        if not skip_timesheet_update and self.timesheet:
            self.timesheet.calculate_totals()

    def calculate_work_hours(self):
        """労働時間を計算する"""
        if self.work_type != '10' or not self.start_time or not self.end_time:
            # 出勤以外または時刻未入力の場合は0
            self.work_minutes = 0
            self.overtime_minutes = 0
            self.late_night_overtime_minutes = 0
            self.holiday_work_minutes = 0
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
        total_break_minutes = (self.break_minutes or 0) + (self.late_night_break_minutes or 0)
        work_minutes = total_minutes - total_break_minutes
        work_minutes = work_minutes if work_minutes > 0 else 0

        # 労働時間（分単位）
        self.work_minutes = work_minutes

        # --- 契約に紐づく時間外算出パターンを取得 ---
        overtime_pattern = None
        if self.timesheet and self.timesheet.staff_contract:
            overtime_pattern = self.timesheet.staff_contract.overtime_pattern

        # --- 残業時間の計算 ---
        self.overtime_minutes = 0
        if overtime_pattern:
            # 計算方式に応じた残業時間の算出
            if overtime_pattern.calculation_type == 'premium':
                # 割増方式: 日単位の基準時間を超えた分を残業とする
                if (overtime_pattern.daily_overtime_enabled and
                        overtime_pattern.daily_overtime_hours is not None):
                    standard_minutes = overtime_pattern.daily_overtime_hours * 60
                    if self.work_minutes > standard_minutes:
                        self.overtime_minutes = self.work_minutes - standard_minutes
            
            elif overtime_pattern.calculation_type == 'monthly_range':
                # 月単位時間範囲方式: 日次では残業計算を行わない（月次集計時に計算）
                # ここでは残業時間は0のまま
                pass
            
            elif overtime_pattern.calculation_type == 'flexible':
                # 1ヶ月単位変形労働方式: 日次では残業計算を行わない（月次集計時に計算）
                # ここでは残業時間は0のまま
                pass

        # --- 深夜時間の計算 ---
        # 深夜時間は全ての計算方式で共通して計算される（22:00～5:00）
        self.late_night_overtime_minutes = 0
        if overtime_pattern and overtime_pattern.calculate_midnight_premium:
            late_night_start = time(22, 0)
            late_night_end = time(5, 0)

            # 1分ずつチェックする堅牢な方法
            late_night_minutes = 0
            current_time = start_dt
            while current_time < end_dt:
                t = current_time.time()
                is_late_night = False

                # 深夜時間帯の判定
                # 22:00以降、または翌日の00:00から05:00まで
                if t >= late_night_start or t < late_night_end:
                    is_late_night = True

                if is_late_night:
                    late_night_minutes += 1
                current_time += timedelta(minutes=1)

            # 深夜休憩時間を深夜時間から差し引く
            late_night_work_minutes = late_night_minutes - (self.late_night_break_minutes or 0)
            self.late_night_overtime_minutes = late_night_work_minutes if late_night_work_minutes > 0 else 0


        # --- 休日労働時間の計算 ---
        # TODO: 会社の休日カレンダーと連携する必要がある
        if self.work_date.weekday() >= 5:  # 土日
            self.holiday_work_minutes = self.work_minutes
        else:
            self.holiday_work_minutes = 0

    # --- Display properties ---
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
        if self.work_minutes:
            hours, minutes = divmod(self.work_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def overtime_hours_display(self):
        """残業時間の表示用文字列"""
        if self.overtime_minutes and self.overtime_minutes > 0:
            hours, minutes = divmod(self.overtime_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def late_night_overtime_hours_display(self):
        """深夜時間の表示用文字列"""
        if self.late_night_overtime_minutes and self.late_night_overtime_minutes > 0:
            hours, minutes = divmod(self.late_night_overtime_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def holiday_work_hours_display(self):
        """休日労働時間の表示用文字列"""
        if self.holiday_work_minutes and self.holiday_work_minutes > 0:
            hours, minutes = divmod(self.holiday_work_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"
