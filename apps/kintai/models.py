from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import MyModel, MyTenantModel, TenantManager
from apps.contract.models import StaffContract, ClientContract
from apps.client.models import Client
from apps.staff.models import Staff
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, time, datetime, timedelta
from calendar import monthrange
from decimal import Decimal

User = get_user_model()


class StaffTimesheet(MyTenantModel):
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
    total_variable_minutes = models.PositiveIntegerField('変形時間（分）', default=0, help_text='1ヶ月単位変形労働での月次法定超過時間')
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
        self.total_variable_minutes = 0
        
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
            
            elif overtime_pattern.calculation_type == 'premium':
                # 割増方式で月単位時間外割増が有効な場合
                if overtime_pattern.monthly_overtime_enabled and overtime_pattern.monthly_overtime_hours:
                    # 月単位時間外割増時間を超えた残業時間を割増時間として計算
                    monthly_overtime_threshold = overtime_pattern.monthly_overtime_hours * 60
                    if self.total_overtime_minutes > monthly_overtime_threshold:
                        self.total_premium_minutes = self.total_overtime_minutes - monthly_overtime_threshold

            elif overtime_pattern.calculation_type == 'variable':
                # 1ヶ月単位変形労働方式の場合
                # 対象月の日数を取得
                year = self.target_month.year
                month = self.target_month.month
                _, days_in_month = monthrange(year, month)
                
                # 日数に応じた基準時間を取得
                standard_hours = 0
                standard_minutes = 0
                
                if days_in_month == 28:
                    standard_hours = overtime_pattern.days_28_hours
                    standard_minutes = overtime_pattern.days_28_minutes
                elif days_in_month == 29:
                    standard_hours = overtime_pattern.days_29_hours
                    standard_minutes = overtime_pattern.days_29_minutes
                elif days_in_month == 30:
                    standard_hours = overtime_pattern.days_30_hours
                    standard_minutes = overtime_pattern.days_30_minutes
                elif days_in_month == 31:
                    standard_hours = overtime_pattern.days_31_hours
                    standard_minutes = overtime_pattern.days_31_minutes
                
                # 基準時間を分単位に変換
                standard_total_minutes = (standard_hours * 60) + standard_minutes
                
                # 実労働時間（総労働時間 - 日次・週次残業時間）を計算
                actual_work_minutes = self.total_work_minutes - self.total_overtime_minutes
                
                # 基準時間を超えている場合は変形時間として計算
                if actual_work_minutes > standard_total_minutes:
                    self.total_variable_minutes = actual_work_minutes - standard_total_minutes
                
                # 月単位時間外割増が有効な場合、残業時間+変形時間が閾値を超えた分を割増時間として計算
                if overtime_pattern.monthly_overtime_enabled and overtime_pattern.monthly_overtime_hours:
                    monthly_overtime_threshold = overtime_pattern.monthly_overtime_hours * 60
                    total_overtime_and_variable = self.total_overtime_minutes + self.total_variable_minutes
                    if total_overtime_and_variable > monthly_overtime_threshold:
                        self.total_premium_minutes = total_overtime_and_variable - monthly_overtime_threshold

            elif overtime_pattern.calculation_type == 'flextime':
                # 1ヶ月単位フレックス方式の場合
                # 対象月の日数を取得
                year = self.target_month.year
                month = self.target_month.month
                _, days_in_month = monthrange(year, month)
                
                # 日数に応じた法定労働時間を取得
                standard_hours = 0
                standard_minutes = 0
                
                if days_in_month == 28:
                    standard_hours = overtime_pattern.days_28_hours
                    standard_minutes = overtime_pattern.days_28_minutes
                elif days_in_month == 29:
                    standard_hours = overtime_pattern.days_29_hours
                    standard_minutes = overtime_pattern.days_29_minutes
                elif days_in_month == 30:
                    standard_hours = overtime_pattern.days_30_hours
                    standard_minutes = overtime_pattern.days_30_minutes
                elif days_in_month == 31:
                    standard_hours = overtime_pattern.days_31_hours
                    standard_minutes = overtime_pattern.days_31_minutes
                
                # 法定労働時間を分単位に変換
                standard_total_minutes = (standard_hours * 60) + standard_minutes
                
                # 総労働時間と法定労働時間を比較
                if self.total_work_minutes > standard_total_minutes:
                    # 総労働時間が法定労働時間を超えた分を残業時間として計算
                    self.total_overtime_minutes = self.total_work_minutes - standard_total_minutes
                    
                    # 月単位時間外割増が有効な場合、残業時間が閾値を超えた分を割増時間として計算
                    if overtime_pattern.monthly_overtime_enabled and overtime_pattern.monthly_overtime_hours:
                        monthly_overtime_threshold = overtime_pattern.monthly_overtime_hours * 60
                        if self.total_overtime_minutes > monthly_overtime_threshold:
                            self.total_premium_minutes = self.total_overtime_minutes - monthly_overtime_threshold
                elif self.total_work_minutes < standard_total_minutes:
                    # 総労働時間が法定労働時間未満の場合、不足分を控除時間として計算
                    self.total_deduction_minutes = standard_total_minutes - self.total_work_minutes


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
    def monthly_standard_hours(self):
        """その月の基準時間（法定労働時間）を取得"""
        if not self.staff_contract or not self.staff_contract.overtime_pattern:
            return 0
            
        overtime_pattern = self.staff_contract.overtime_pattern
        year = self.target_month.year
        month = self.target_month.month
        _, days_in_month = monthrange(year, month)
        
        if days_in_month == 28:
            return overtime_pattern.days_28_hours
        elif days_in_month == 29:
            return overtime_pattern.days_29_hours
        elif days_in_month == 30:
            return overtime_pattern.days_30_hours
        elif days_in_month == 31:
            return overtime_pattern.days_31_hours
        return 0

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

    @property
    def total_variable_hours_display(self):
        """変形時間の表示用文字列"""
        if self.total_variable_minutes and self.total_variable_minutes > 0:
            hours, minutes = divmod(self.total_variable_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"


class ClientTimesheet(MyTenantModel):
    """
    クライアント向け月次勤怠情報を管理するモデル。
    クライアント契約に対してスタッフごとに毎月作成される。
    """
    client_contract = models.ForeignKey(
        ClientContract,
        on_delete=models.CASCADE,
        related_name='client_timesheets',
        verbose_name='クライアント契約'
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='client_timesheets',
        verbose_name='クライアント'
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='client_timesheets',
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
    total_variable_minutes = models.PositiveIntegerField('変形時間（分）', default=0, help_text='1ヶ月単位変形労働での月次法定超過時間')
    total_absence_days = models.PositiveIntegerField('欠勤日数', default=0)

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
        related_name='submitted_client_timesheets',
        verbose_name='提出者'
    )
    approved_at = models.DateTimeField('承認日時', blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_client_timesheets',
        verbose_name='承認者'
    )
    rejected_at = models.DateTimeField('差戻し日時', blank=True, null=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_client_timesheets',
        verbose_name='差戻し者'
    )
    rejection_reason = models.TextField('差戻し理由', blank=True, null=True)

    class Meta:
        db_table = 'apps_kintai_client_timesheet'
        verbose_name = 'クライアント月次勤怠'
        verbose_name_plural = 'クライアント月次勤怠'
        unique_together = ['client_contract', 'staff', 'target_month']
        ordering = ['-target_month', 'client__name', 'staff__name_last', 'staff__name_first']
        indexes = [
            models.Index(fields=['client_contract']),
            models.Index(fields=['client']),
            models.Index(fields=['staff']),
            models.Index(fields=['target_month']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        if self.target_month:
            return f"{self.client} - {self.staff} - {self.target_month.year}年{self.target_month.month}月"
        return f"{self.client} - {self.staff} - (年月未設定)"

    def clean(self):
        """バリデーション"""
        if self.target_month and self.target_month.day != 1:
            raise ValidationError({'target_month': '対象年月は月の1日を設定してください。'})

        # クライアント契約の契約期間内かチェック
        if getattr(self, 'client_contract_id', None) and self.target_month:
            try:
                _, last_day_num = monthrange(self.target_month.year, self.target_month.month)
                last_day = date(self.target_month.year, self.target_month.month, last_day_num)
            except (ValueError, TypeError):
                last_day = None

            if self.target_month and last_day:
                cc = self.client_contract
                cc_start = cc.start_date
                cc_end = cc.end_date

                if cc_start and last_day < cc_start:
                    raise ValidationError('指定した年月はクライアント契約の契約期間外です。')

                if cc_end and self.target_month > cc_end:
                    raise ValidationError('指定した年月はクライアント契約の契約期間外です。')

    def save(self, *args, **kwargs):
        # target_month を常にその月の1日に設定
        if self.target_month:
            self.target_month = self.target_month.replace(day=1)

        # クライアント契約からクライアントを自動設定
        if self.client_contract and not self.client_id:
            self.client = self.client_contract.client
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """日次勤怠データから集計値を計算する"""
        timecards = self.timecards.all()

        self.total_work_days = timecards.filter(work_type='10').count()
        self.total_work_minutes = sum(tc.work_minutes or 0 for tc in timecards)
        self.total_overtime_minutes = sum(tc.overtime_minutes or 0 for tc in timecards)
        self.total_late_night_overtime_minutes = sum(tc.late_night_overtime_minutes or 0 for tc in timecards)
        self.total_holiday_work_minutes = sum(tc.holiday_work_minutes or 0 for tc in timecards)
        self.total_absence_days = timecards.filter(work_type='30').count()

        # --- 月単位時間範囲方式の割増・控除時間計算 ---
        self.total_premium_minutes = 0
        self.total_deduction_minutes = 0
        self.total_variable_minutes = 0

        if self.client_contract and self.client_contract.overtime_pattern:
            overtime_pattern = self.client_contract.overtime_pattern

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

            elif overtime_pattern.calculation_type == 'premium':
                # 割増方式で月単位時間外割増が有効な場合
                if overtime_pattern.monthly_overtime_enabled and overtime_pattern.monthly_overtime_hours:
                    # 月単位時間外割増時間を超えた残業時間を割増時間として計算
                    monthly_overtime_threshold = overtime_pattern.monthly_overtime_hours * 60
                    if self.total_overtime_minutes > monthly_overtime_threshold:
                        self.total_premium_minutes = self.total_overtime_minutes - monthly_overtime_threshold

            elif overtime_pattern.calculation_type == 'variable':
                # 1ヶ月単位変形労働方式の場合
                year = self.target_month.year
                month = self.target_month.month
                _, days_in_month = monthrange(year, month)

                standard_hours = 0
                standard_minutes = 0

                if days_in_month == 28:
                    standard_hours = overtime_pattern.days_28_hours
                    standard_minutes = overtime_pattern.days_28_minutes
                elif days_in_month == 29:
                    standard_hours = overtime_pattern.days_29_hours
                    standard_minutes = overtime_pattern.days_29_minutes
                elif days_in_month == 30:
                    standard_hours = overtime_pattern.days_30_hours
                    standard_minutes = overtime_pattern.days_30_minutes
                elif days_in_month == 31:
                    standard_hours = overtime_pattern.days_31_hours
                    standard_minutes = overtime_pattern.days_31_minutes

                standard_total_minutes = (standard_hours * 60) + standard_minutes
                actual_work_minutes = self.total_work_minutes - self.total_overtime_minutes

                if actual_work_minutes > standard_total_minutes:
                    self.total_variable_minutes = actual_work_minutes - standard_total_minutes

                if overtime_pattern.monthly_overtime_enabled and overtime_pattern.monthly_overtime_hours:
                    monthly_overtime_threshold = overtime_pattern.monthly_overtime_hours * 60
                    total_overtime_and_variable = self.total_overtime_minutes + self.total_variable_minutes
                    if total_overtime_and_variable > monthly_overtime_threshold:
                        self.total_premium_minutes = total_overtime_and_variable - monthly_overtime_threshold

            elif overtime_pattern.calculation_type == 'flextime':
                # 1ヶ月単位フレックス方式の場合
                year = self.target_month.year
                month = self.target_month.month
                _, days_in_month = monthrange(year, month)

                standard_hours = 0
                standard_minutes = 0

                if days_in_month == 28:
                    standard_hours = overtime_pattern.days_28_hours
                    standard_minutes = overtime_pattern.days_28_minutes
                elif days_in_month == 29:
                    standard_hours = overtime_pattern.days_29_hours
                    standard_minutes = overtime_pattern.days_29_minutes
                elif days_in_month == 30:
                    standard_hours = overtime_pattern.days_30_hours
                    standard_minutes = overtime_pattern.days_30_minutes
                elif days_in_month == 31:
                    standard_hours = overtime_pattern.days_31_hours
                    standard_minutes = overtime_pattern.days_31_minutes

                standard_total_minutes = (standard_hours * 60) + standard_minutes

                if self.total_work_minutes > standard_total_minutes:
                    self.total_overtime_minutes = self.total_work_minutes - standard_total_minutes

                    if overtime_pattern.monthly_overtime_enabled and overtime_pattern.monthly_overtime_hours:
                        monthly_overtime_threshold = overtime_pattern.monthly_overtime_hours * 60
                        if self.total_overtime_minutes > monthly_overtime_threshold:
                            self.total_premium_minutes = self.total_overtime_minutes - monthly_overtime_threshold
                elif self.total_work_minutes < standard_total_minutes:
                    self.total_deduction_minutes = standard_total_minutes - self.total_work_minutes

        self.save()

    @property
    def is_editable(self):
        """編集可能かどうか"""
        return self.status in ['10', '40']

    @property
    def is_submitted(self):
        """提出済みかどうか"""
        return self.status in ['20', '30']

    @property
    def is_approved(self):
        """承認済みかどうか"""
        return self.status == '30'

    @property
    def monthly_standard_hours(self):
        """その月の基準時間（法定労働時間）を取得"""
        if not self.client_contract or not self.client_contract.overtime_pattern:
            return 0

        overtime_pattern = self.client_contract.overtime_pattern
        year = self.target_month.year
        month = self.target_month.month
        _, days_in_month = monthrange(year, month)

        if days_in_month == 28:
            return overtime_pattern.days_28_hours
        elif days_in_month == 29:
            return overtime_pattern.days_29_hours
        elif days_in_month == 30:
            return overtime_pattern.days_30_hours
        elif days_in_month == 31:
            return overtime_pattern.days_31_hours
        return 0

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

    @property
    def total_variable_hours_display(self):
        """変形時間の表示用文字列"""
        if self.total_variable_minutes and self.total_variable_minutes > 0:
            hours, minutes = divmod(self.total_variable_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"


class ClientTimecard(MyTenantModel):
    """
    クライアント向け日次勤怠情報を管理するモデル。
    クライアント月次勤怠（ClientTimesheet）に紐づく。
    """
    timesheet = models.ForeignKey(
        ClientTimesheet,
        on_delete=models.CASCADE,
        related_name='timecards',
        verbose_name='クライアント月次勤怠',
        null=True,
        blank=True
    )
    client_contract = models.ForeignKey(
        ClientContract,
        on_delete=models.CASCADE,
        related_name='client_timecards_direct',
        verbose_name='クライアント契約'
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='client_timecards',
        verbose_name='スタッフ'
    )
    work_date = models.DateField('勤務日')
    work_time_pattern_work = models.ForeignKey(
        'master.WorkTimePatternWork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='就業時間パターン',
        related_name='client_timecards'
    )

    # 勤務区分
    work_type = models.CharField(
        '勤務区分',
        max_length=2,
        choices=[
            ('10', '出勤'),
            ('20', '休日'),
            ('30', '欠勤'),
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

    # 備考
    memo = models.TextField('メモ', blank=True, null=True)

    class Meta:
        db_table = 'apps_kintai_client_timecard'
        verbose_name = 'クライアント日次勤怠'
        verbose_name_plural = 'クライアント日次勤怠'
        unique_together = [['client_contract', 'staff', 'work_date']]
        ordering = ['work_date']
        indexes = [
            models.Index(fields=['timesheet']),
            models.Index(fields=['client_contract']),
            models.Index(fields=['staff']),
            models.Index(fields=['work_date']),
            models.Index(fields=['work_type']),
        ]

    def __str__(self):
        try:
            if self.timesheet and self.timesheet.staff:
                return f"{self.timesheet.staff} - {self.work_date}"
        except:
            pass
        if self.staff:
            return f"{self.staff} - {self.work_date}"
        return f"クライアント日次勤怠 - {self.work_date}"

    def clean(self):
        """バリデーション"""
        # 出勤の場合は出勤・退勤時刻が必須
        if self.work_type == '10':  # 出勤
            if not self.start_time or not self.end_time:
                raise ValidationError('出勤の場合は出勤時刻と退勤時刻を入力してください。')

            # 退勤時刻が出勤時刻より前の場合はエラー（翌日フラグを考慮）
            if not self.start_time_next_day and not self.end_time_next_day:
                if self.start_time >= self.end_time:
                    raise ValidationError('退勤時刻は出勤時刻より後の時刻を入力してください。')

        # client_contract が指定されている場合、勤務日が契約期間内かチェック
        if self.client_contract_id and self.work_date:
            try:
                cc = self.client_contract
                cc_start = cc.start_date
                cc_end = cc.end_date
                if cc_start and self.work_date < cc_start:
                    raise ValidationError('勤務日はクライアント契約の契約期間外です。')
                if cc_end and self.work_date > cc_end:
                    raise ValidationError('勤務日はクライアント契約の契約期間外です。')
            except ValidationError:
                raise
            except Exception:
                pass

    def save(self, skip_timesheet_update=False, *args, **kwargs):
        # client_contract と staff が指定されている場合、対応するクライアント月次勤怠を自動作成または取得
        if self.client_contract_id and self.staff_id and self.work_date:
            target_month = self.work_date.replace(day=1)

            timesheet, created = ClientTimesheet.objects.get_or_create(
                client_contract=self.client_contract,
                staff=self.staff,
                target_month=target_month,
                defaults={
                    'client': self.client_contract.client,
                }
            )
            self.timesheet = timesheet

        # 労働時間を自動計算
        self.calculate_work_hours()
        super().save(*args, **kwargs)

        # 月次勤怠の集計を更新
        if not skip_timesheet_update and self.timesheet:
            self.timesheet.calculate_totals()

    def calculate_work_hours(self):
        """労働時間を計算する"""
        if self.work_type != '10' or not self.start_time or not self.end_time:
            self.work_minutes = 0
            self.overtime_minutes = 0
            self.late_night_overtime_minutes = 0
            self.holiday_work_minutes = 0
            return

        # 勤務時間を計算（分単位）
        today = timezone.localdate()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)

        if self.start_time_next_day:
            start_dt += timedelta(days=1)
        if self.end_time_next_day:
            end_dt += timedelta(days=1)

        if not self.start_time_next_day and not self.end_time_next_day and end_dt <= start_dt:
            end_dt += timedelta(days=1)

        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        total_break_minutes = (self.break_minutes or 0) + (self.late_night_break_minutes or 0)
        work_minutes = total_minutes - total_break_minutes
        self.work_minutes = work_minutes if work_minutes > 0 else 0

        # --- 契約に紐づく時間外算出パターンを取得 ---
        overtime_pattern = None
        if self.timesheet and self.timesheet.client_contract:
            overtime_pattern = self.timesheet.client_contract.overtime_pattern

        # --- 残業時間の計算 ---
        self.overtime_minutes = 0
        if overtime_pattern:
            if overtime_pattern.calculation_type == 'premium':
                if (overtime_pattern.daily_overtime_enabled and
                        overtime_pattern.daily_overtime_hours is not None):
                    standard_hours = overtime_pattern.daily_overtime_hours or 0
                    standard_mins = overtime_pattern.daily_overtime_minutes or 0
                    standard_minutes = standard_hours * 60 + standard_mins
                    if self.work_minutes > standard_minutes:
                        self.overtime_minutes = self.work_minutes - standard_minutes

            elif overtime_pattern.calculation_type == 'variable':
                if (overtime_pattern.daily_overtime_enabled and
                        overtime_pattern.daily_overtime_hours is not None):
                    standard_hours = overtime_pattern.daily_overtime_hours or 0
                    standard_mins = overtime_pattern.daily_overtime_minutes or 0
                    standard_minutes = standard_hours * 60 + standard_mins
                    if self.work_minutes > standard_minutes:
                        self.overtime_minutes = self.work_minutes - standard_minutes

        # --- 深夜時間の計算 ---
        self.late_night_overtime_minutes = 0
        if overtime_pattern and overtime_pattern.calculate_midnight_premium:
            late_night_start = time(22, 0)
            late_night_end = time(5, 0)

            late_night_minutes = 0
            current_time = start_dt
            while current_time < end_dt:
                t = current_time.time()
                if t >= late_night_start or t < late_night_end:
                    late_night_minutes += 1
                current_time += timedelta(minutes=1)

            late_night_work_minutes = late_night_minutes - (self.late_night_break_minutes or 0)
            self.late_night_overtime_minutes = late_night_work_minutes if late_night_work_minutes > 0 else 0

        # --- 休日労働時間の計算 ---
        if self.work_date.weekday() >= 5:  # 土日
            self.holiday_work_minutes = self.work_minutes
        else:
            self.holiday_work_minutes = 0

    @property
    def is_holiday(self):
        return self.work_type in ['20', '70']

    @property
    def is_absence(self):
        return self.work_type == '30'

    @property
    def work_hours_display(self):
        if self.work_minutes:
            hours, minutes = divmod(self.work_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def overtime_hours_display(self):
        if self.overtime_minutes and self.overtime_minutes > 0:
            hours, minutes = divmod(self.overtime_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def late_night_overtime_hours_display(self):
        if self.late_night_overtime_minutes and self.late_night_overtime_minutes > 0:
            hours, minutes = divmod(self.late_night_overtime_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"

    @property
    def holiday_work_hours_display(self):
        if self.holiday_work_minutes and self.holiday_work_minutes > 0:
            hours, minutes = divmod(self.holiday_work_minutes, 60)
            return f"{hours}時間{minutes:02d}分"
        return "-"


class StaffTimecard(MyTenantModel):
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
    work_time_pattern_work = models.ForeignKey(
        'master.WorkTimePatternWork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='就業時間パターン',
        related_name='timecards'
    )

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
        today = timezone.localdate()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)

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
                    # 時間と分を合計して総分数を計算
                    standard_hours = overtime_pattern.daily_overtime_hours or 0
                    standard_mins = overtime_pattern.daily_overtime_minutes or 0
                    standard_minutes = standard_hours * 60 + standard_mins
                    if self.work_minutes > standard_minutes:
                        self.overtime_minutes = self.work_minutes - standard_minutes
            
            elif overtime_pattern.calculation_type == 'monthly_range':
                # 月単位時間範囲方式: 日次では残業計算を行わない（月次集計時に計算）
                # ここでは残業時間は0のまま
                pass
            
            elif overtime_pattern.calculation_type == 'variable':
                # 1ヶ月単位変形労働方式
                if (overtime_pattern.daily_overtime_enabled and
                        overtime_pattern.daily_overtime_hours is not None):
                    # 日単位時間外計算が有効な場合、基準時間を超えた分を残業とする
                    standard_hours = overtime_pattern.daily_overtime_hours or 0
                    standard_mins = overtime_pattern.daily_overtime_minutes or 0
                    standard_minutes = standard_hours * 60 + standard_mins
                    if self.work_minutes > standard_minutes:
                        self.overtime_minutes = self.work_minutes - standard_minutes

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


class StaffTimerecord(MyModel):
    """
    勤怠打刻情報を管理するモデル。
    スタッフが実際に打刻した時刻を記録する。
    StaffTimecard、StaffTimesheetとは独立したモデル。
    """
    staff_contract = models.ForeignKey(
        StaffContract,
        on_delete=models.CASCADE,
        related_name='timerecords',
        verbose_name='スタッフ契約',
        null=True,
        blank=True
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='timerecords',
        verbose_name='スタッフ'
    )
    work_date = models.DateField('勤務日')
    
    # 打刻時刻
    start_time = models.DateTimeField('開始時刻', blank=True, null=True)
    end_time = models.DateTimeField('終了時刻', blank=True, null=True)
    
    # 丸め時刻
    rounded_start_time = models.DateTimeField('丸め開始時刻', blank=True, null=True)
    rounded_end_time = models.DateTimeField('丸め終了時刻', blank=True, null=True)
    
    # 位置情報（緯度・経度）
    start_latitude = models.DecimalField('開始位置（緯度）', max_digits=8, decimal_places=5, blank=True, null=True)
    start_longitude = models.DecimalField('開始位置（経度）', max_digits=8, decimal_places=5, blank=True, null=True)
    end_latitude = models.DecimalField('終了位置（緯度）', max_digits=8, decimal_places=5, blank=True, null=True)
    end_longitude = models.DecimalField('終了位置（経度）', max_digits=8, decimal_places=5, blank=True, null=True)

    # 住所情報
    start_address = models.TextField('開始位置（住所）', blank=True, null=True)
    end_address = models.TextField('終了位置（住所）', blank=True, null=True)
    
    # 備考
    memo = models.TextField('メモ', blank=True, null=True)
    
    class Meta:
        db_table = 'apps_kintai_staff_timerecord'
        verbose_name = '勤怠打刻'
        verbose_name_plural = '勤怠打刻'
        unique_together = [['staff_contract', 'work_date']]
        ordering = ['-work_date', 'staff__name_last', 'staff__name_first']
        indexes = [
            models.Index(fields=['staff_contract']),
            models.Index(fields=['staff']),
            models.Index(fields=['work_date']),
            models.Index(fields=['start_time']),
            models.Index(fields=['end_time']),
        ]
    
    def __str__(self):
        return f"{self.staff} - {self.work_date}"
    
    def clean(self):
        """バリデーション"""
        # 終了時刻が開始時刻より前の場合はエラー
        # 打刻時刻または丸め時刻を使用してチェック
        start = self.start_time if self.start_time else self.rounded_start_time
        end = self.end_time if self.end_time else self.rounded_end_time
        if start and end:
            if end <= start:
                raise ValidationError('終了時刻は開始時刻より後の時刻を入力してください。')
        
        # スタッフ契約からスタッフを自動設定（saveメソッドが呼ばれる前にも検証が必要なため）
        if self.staff_contract and not self.staff_id:
            self.staff = self.staff_contract.staff

        # スタッフ契約とスタッフの整合性チェック
        if self.staff_contract and self.staff_id:
            if self.staff_contract.staff_id != self.staff_id:
                raise ValidationError('スタッフ契約とスタッフが一致しません。')

    def save(self, *args, **kwargs):
        # スタッフ契約からスタッフを自動設定
        if self.staff_contract and not self.staff_id:
            self.staff = self.staff_contract.staff

        # 常に秒を切り捨てて保存
        # 丸め後の時刻がすでに設定されている場合（手動更新の場合）は、それを尊重する
        if self.start_time and not self.rounded_start_time:
            self.rounded_start_time = self.start_time.replace(second=0, microsecond=0)
            # 時間丸め設定があれば適用
            if self.staff_contract and self.staff_contract.time_punch:
                from .utils import apply_time_rounding
                self.rounded_start_time, _ = apply_time_rounding(
                    self.rounded_start_time, None, self.staff_contract.time_punch
                )

        if self.end_time and not self.rounded_end_time:
            self.rounded_end_time = self.end_time.replace(second=0, microsecond=0)
            # 時間丸め設定があれば適用
            if self.staff_contract and self.staff_contract.time_punch:
                from .utils import apply_time_rounding
                _, self.rounded_end_time = apply_time_rounding(
                    None, self.rounded_end_time, self.staff_contract.time_punch
                )

        super().save(*args, **kwargs)
    
    @property
    def total_work_minutes(self):
        """総労働時間（分）を計算（丸め時刻を使用）"""
        # 丸め時刻がある場合はそれを使用、ない場合は元の時刻を使用
        start_time = self.rounded_start_time if self.rounded_start_time else self.start_time
        end_time = self.rounded_end_time if self.rounded_end_time else self.end_time
        
        if not start_time or not end_time:
            return 0
        
        # 休憩時間の合計を計算（丸め時刻を使用）
        total_break_minutes = self.total_break_minutes
        
        # 労働時間を計算
        work_duration = end_time - start_time
        work_minutes = int(work_duration.total_seconds() / 60)
        
        # 休憩時間を引く
        net_work_minutes = work_minutes - total_break_minutes
        return net_work_minutes if net_work_minutes > 0 else 0
    
    @property
    def total_break_minutes(self):
        """休憩時間の合計（分）を計算（丸め時刻を使用）"""
        return sum(
            break_record.break_minutes for break_record in self.breaks.all()
        )

    @property
    def break_hours_display(self):
        """休憩時間の表示用文字列"""
        minutes = self.total_break_minutes
        if minutes:
            hours, mins = divmod(minutes, 60)
            return f"{hours}時間{mins:02d}分"
        return "-"

    @property
    def work_hours_display(self):
        """労働時間の表示用文字列（丸め時刻を使用）"""
        minutes = self.total_work_minutes
        if minutes:
            hours, mins = divmod(minutes, 60)
            return f"{hours}時間{mins:02d}分"
        return "-"
    
    @property
    def work_hours_int(self):
        """労働時間の時間部分（整数）"""
        if self.total_work_minutes:
            hours, _ = divmod(self.total_work_minutes, 60)
            return hours
        return 0

    @property
    def work_minutes_int(self):
        """労働時間の分部分（整数）"""
        if self.total_work_minutes:
            _, minutes = divmod(self.total_work_minutes, 60)
            return minutes
        return 0
    
    @property
    def break_hours_int(self):
        """休憩時間の時間部分（整数）"""
        if self.total_break_minutes:
            hours, _ = divmod(self.total_break_minutes, 60)
            return hours
        return 0

    @property
    def break_minutes_int(self):
        """休憩時間の分部分（整数）"""
        if self.total_break_minutes:
            _, minutes = divmod(self.total_break_minutes, 60)
            return minutes
        return 0
    
    @property
    def rounded_start_time_display(self):
        """丸め開始時刻の表示用文字列"""
        if self.rounded_start_time:
            return self.rounded_start_time.strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    
    @property
    def rounded_end_time_display(self):
        """丸め終了時刻の表示用文字列"""
        if self.rounded_end_time:
            return self.rounded_end_time.strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    
    @property
    def has_rounding_difference(self):
        """丸め処理により時刻が変更されているかどうか"""
        start_diff = (self.rounded_start_time != self.start_time) if (self.rounded_start_time and self.start_time) else False
        end_diff = (self.rounded_end_time != self.end_time) if (self.rounded_end_time and self.end_time) else False
        return start_diff or end_diff


class StaffTimerecordBreak(MyModel):
    """
    勤怠打刻の休憩時間を管理するモデル。
    1つの勤怠打刻に対して複数の休憩時間を登録できる。
    """
    timerecord = models.ForeignKey(
        StaffTimerecord,
        on_delete=models.CASCADE,
        related_name='breaks',
        verbose_name='勤怠打刻'
    )
    break_start = models.DateTimeField('休憩開始時刻', blank=True, null=True)
    break_end = models.DateTimeField('休憩終了時刻', blank=True, null=True)
    
    # 丸め時刻
    rounded_break_start = models.DateTimeField('丸め休憩開始時刻', blank=True, null=True)
    rounded_break_end = models.DateTimeField('丸め休憩終了時刻', blank=True, null=True)
    
    # 位置情報（緯度・経度）
    start_latitude = models.DecimalField('開始位置（緯度）', max_digits=8, decimal_places=5, blank=True, null=True)
    start_longitude = models.DecimalField('開始位置（経度）', max_digits=8, decimal_places=5, blank=True, null=True)
    end_latitude = models.DecimalField('終了位置（緯度）', max_digits=8, decimal_places=5, blank=True, null=True)
    end_longitude = models.DecimalField('終了位置（経度）', max_digits=8, decimal_places=5, blank=True, null=True)

    # 住所情報
    start_address = models.TextField('開始位置（住所）', blank=True, null=True)
    end_address = models.TextField('終了位置（住所）', blank=True, null=True)
    
    class Meta:
        db_table = 'apps_kintai_staff_timerecord_break'
        verbose_name = '休憩時間'
        verbose_name_plural = '休憩時間'
        ordering = ['break_start']
        indexes = [
            models.Index(fields=['timerecord']),
            models.Index(fields=['break_start']),
            models.Index(fields=['break_end']),
        ]
    
    def __str__(self):
        end_str = self.break_end.strftime('%H:%M') if self.break_end else '休憩中'
        return f"{self.timerecord} - 休憩 {self.break_start.strftime('%H:%M')}～{end_str}"
    
    def clean(self):
        """バリデーション"""
        # 休憩終了時刻が休憩開始時刻より前の場合はエラー
        # 打刻時刻または丸め時刻を使用してチェック
        start = self.break_start if self.break_start else self.rounded_break_start
        end = self.break_end if self.break_end else self.rounded_break_end
        if start and end:
            if end <= start:
                raise ValidationError('休憩終了時刻は休憩開始時刻より後の時刻を入力してください。')
        
        # 休憩時間が勤怠打刻の時間範囲内かチェック
        if self.timerecord_id:
            try:
                tr = self.timerecord
                tr_start = tr.start_time if tr.start_time else tr.rounded_start_time
                tr_end = tr.end_time if tr.end_time else tr.rounded_end_time

                if tr_start and start and start < tr_start:
                    raise ValidationError('休憩開始時刻は勤務開始時刻より後の時刻を入力してください。')
                if tr_end and end and end > tr_end:
                    raise ValidationError('休憩終了時刻は勤務終了時刻より前の時刻を入力してください。')
            except ValidationError:
                raise
            except Exception:
                pass
    
    def save(self, *args, **kwargs):
        # 常に秒を切り捨てて保存
        # 丸め後の時刻がすでに設定されている場合（手動更新の場合）は、それを尊重する
        if self.break_start and not self.rounded_break_start:
            self.rounded_break_start = self.break_start.replace(second=0, microsecond=0)
            # 時間丸め設定があれば適用
            if (self.timerecord and
                    self.timerecord.staff_contract and
                    self.timerecord.staff_contract.time_punch):
                from .utils import apply_break_time_rounding
                self.rounded_break_start, _ = apply_break_time_rounding(
                    self.rounded_break_start, None, self.timerecord.staff_contract.time_punch
                )

        if self.break_end and not self.rounded_break_end:
            self.rounded_break_end = self.break_end.replace(second=0, microsecond=0)
            # 時間丸め設定があれば適用
            if (self.timerecord and
                    self.timerecord.staff_contract and
                    self.timerecord.staff_contract.time_punch):
                from .utils import apply_break_time_rounding
                _, self.rounded_break_end = apply_break_time_rounding(
                    None, self.rounded_break_end, self.timerecord.staff_contract.time_punch
                )

        super().save(*args, **kwargs)
    
    @property
    def break_minutes(self):
        """休憩時間（分）を計算（丸め時刻を使用）"""
        # 丸め時刻がある場合はそれを使用、ない場合は元の時刻を使用
        start_time = self.rounded_break_start if self.rounded_break_start else self.break_start
        end_time = self.rounded_break_end if self.rounded_break_end else self.break_end
        
        if not end_time:
            return 0
        duration = end_time - start_time
        return int(duration.total_seconds() / 60)
    
    @property
    def break_hours_display(self):
        """休憩時間の表示用文字列"""
        minutes = self.break_minutes
        hours, mins = divmod(minutes, 60)
        return f"{hours}時間{mins:02d}分"
    
    @property
    def rounded_break_start_display(self):
        """丸め休憩開始時刻の表示用文字列"""
        if self.rounded_break_start:
            return self.rounded_break_start.strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    
    @property
    def rounded_break_end_display(self):
        """丸め休憩終了時刻の表示用文字列"""
        if self.rounded_break_end:
            return self.rounded_break_end.strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    
    @property
    def has_rounding_difference(self):
        """丸め処理により時刻が変更されているかどうか"""
        start_diff = (self.rounded_break_start != self.break_start) if (self.rounded_break_start and self.break_start) else False
        end_diff = (self.rounded_break_end != self.break_end) if (self.rounded_break_end and self.break_end) else False
        return start_diff or end_diff

class StaffTimerecordApproval(MyTenantModel):
    """
    勤怠打刻の承認情報を管理するモデル。
    TimeRecordをまとめて申請承認管理するためのもの。
    """
    staff = models.ForeignKey(
        'staff.Staff',
        on_delete=models.CASCADE,
        related_name='timerecord_approvals',
        verbose_name='スタッフ'
    )
    staff_contract = models.ForeignKey(
        'contract.StaffContract',
        on_delete=models.CASCADE,
        related_name='timerecord_approvals',
        verbose_name='スタッフ契約'
    )
    closing_date = models.DateField('締め日')
    period_start = models.DateField('締期間開始')
    period_end = models.DateField('締期間終了')

    # 承認ステータス
    status = models.CharField(
        '承認ステータス',
        max_length=2,
        choices=[
            ('10', '作成中'),
            ('20', '提出済み'),
            ('30', '承認済み'),
            ('40', '差戻し'),
        ],
        default='10'
    )

    class Meta:
        db_table = 'apps_kintai_staff_timerecord_approval'
        verbose_name = '勤怠申請承認'
        verbose_name_plural = '勤怠申請承認'
        ordering = ['-closing_date', 'staff']
        indexes = [
            models.Index(fields=['staff']),
            models.Index(fields=['staff_contract']),
            models.Index(fields=['closing_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.staff} - {self.closing_date}締め"

    def clean(self):
        """バリデーション"""
        super().clean()
        # スタッフ契約とスタッフの整合性チェック
        if self.staff_contract_id and self.staff_id:
            if self.staff_contract.staff_id != self.staff_id:
                raise ValidationError('スタッフ契約とスタッフが一致しません。')

        # 期間の整合性チェック
        if self.period_start and self.period_end:
            if self.period_start > self.period_end:
                raise ValidationError('締期間終了は締期間開始より後の日付を入力してください。')

    def save(self, *args, **kwargs):
        # スタッフ契約からスタッフを自動設定
        if self.staff_contract and not self.staff_id:
            self.staff = self.staff_contract.staff
        super().save(*args, **kwargs)
