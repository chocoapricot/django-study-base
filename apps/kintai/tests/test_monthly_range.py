from django.test import TestCase
from apps.kintai.models import StaffTimecard, StaffTimesheet
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models_contract import OvertimePattern, ContractPattern, EmploymentType
from datetime import date, time


class StaffTimesheetMonthlyRangeTest(TestCase):
    """月単位時間範囲方式の割増・控除時間計算のテスト"""

    @classmethod
    def setUpTestData(cls):
        # --- Master Data ---
        cls.emp_type = EmploymentType.objects.create(name="正社員")
        cls.contract_pattern = ContractPattern.objects.create(name="test", domain='1')

        # --- Overtime Pattern (月単位時間範囲) ---
        cls.pattern_monthly_range = OvertimePattern.objects.create(
            name='月単位時間範囲',
            calculate_midnight_premium=False,
            calculation_type='monthly_range',
            monthly_range_min=140,  # 140時間
            monthly_range_max=160,  # 160時間
        )

        # --- Staff and Contract ---
        cls.staff = Staff.objects.create(
            name_last='テスト', name_first='太郎',
        )
        cls.staff_contract = StaffContract.objects.create(
            staff=cls.staff,
            contract_name='Test Contract',
            start_date=date(2023, 1, 1),
            contract_pattern=cls.contract_pattern,
            overtime_pattern=cls.pattern_monthly_range,
        )

        # --- Timesheet ---
        cls.timesheet = StaffTimesheet.objects.create(
            staff_contract=cls.staff_contract,
            staff=cls.staff,
            target_month=date(2023, 1, 1),
        )

    def _create_timecard(self, work_date, start_time, end_time, break_minutes):
        """タイムカードを作成するヘルパーメソッド"""
        timecard = StaffTimecard(
            staff_contract=self.staff_contract,
            timesheet=self.timesheet,
            work_date=work_date,
            work_type='10',
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
        )
        timecard.save()
        return timecard

    def test_monthly_range_within_range(self):
        """月の総労働時間が範囲内の場合、割増・控除ともに0"""
        # 150時間（範囲内: 140～160時間）
        # 25日間、1日6時間（休憩なし）勤務 = 150時間
        for day in range(1, 26):
            self._create_timecard(
                date(2023, 1, day),
                time(9, 0),
                time(15, 0),  # 6時間
                0
            )
        
        self.timesheet.refresh_from_db()
        self.assertEqual(self.timesheet.total_work_minutes, 150 * 60)  # 9000分
        self.assertEqual(self.timesheet.total_premium_minutes, 0)
        self.assertEqual(self.timesheet.total_deduction_minutes, 0)

    def test_monthly_range_below_minimum(self):
        """月の総労働時間が最小値未満の場合、控除時間が計算される"""
        # 120時間（最小値140時間未満）
        # 15日間、1日8時間（休憩60分）勤務 = 120時間
        for day in range(1, 16):
            self._create_timecard(
                date(2023, 1, day),
                time(9, 0),
                time(18, 0),  # 9時間 - 休憩60分 = 8時間
                60
            )
        
        self.timesheet.refresh_from_db()
        self.assertEqual(self.timesheet.total_work_minutes, 120 * 60)  # 7200分
        self.assertEqual(self.timesheet.total_premium_minutes, 0)
        # 控除時間 = 140 * 60 - 120 * 60 = 1200分（20時間）
        self.assertEqual(self.timesheet.total_deduction_minutes, 20 * 60)

    def test_monthly_range_above_maximum(self):
        """月の総労働時間が最大値超過の場合、割増時間が計算される"""
        # 180時間（最大値160時間超過）
        # 20日間、1日9時間（休憩60分）勤務 = 180時間
        for day in range(1, 21):
            self._create_timecard(
                date(2023, 1, day),
                time(9, 0),
                time(19, 0),  # 10時間 - 休憩60分 = 9時間
                60
            )
        
        self.timesheet.refresh_from_db()
        self.assertEqual(self.timesheet.total_work_minutes, 180 * 60)  # 10800分
        # 割増時間 = 180 * 60 - 160 * 60 = 1200分（20時間）
        self.assertEqual(self.timesheet.total_premium_minutes, 20 * 60)
        self.assertEqual(self.timesheet.total_deduction_minutes, 0)

    def test_monthly_range_exact_minimum(self):
        """月の総労働時間が最小値ちょうどの場合、控除時間は0"""
        # 140時間（最小値ちょうど）
        # 20日間、1日7時間（休憩60分）勤務 = 140時間
        for day in range(1, 21):
            self._create_timecard(
                date(2023, 1, day),
                time(9, 0),
                time(17, 0),  # 8時間 - 休憩60分 = 7時間
                60
            )
        
        self.timesheet.refresh_from_db()
        self.assertEqual(self.timesheet.total_work_minutes, 140 * 60)  # 8400分
        self.assertEqual(self.timesheet.total_premium_minutes, 0)
        self.assertEqual(self.timesheet.total_deduction_minutes, 0)

    def test_monthly_range_exact_maximum(self):
        """月の総労働時間が最大値ちょうどの場合、割増時間は0"""
        # 160時間（最大値ちょうど）
        # 20日間、1日8時間（休憩60分）勤務 = 160時間
        for day in range(1, 21):
            self._create_timecard(
                date(2023, 1, day),
                time(9, 0),
                time(18, 0),  # 9時間 - 休憩60分 = 8時間
                60
            )
        
        self.timesheet.refresh_from_db()
        self.assertEqual(self.timesheet.total_work_minutes, 160 * 60)  # 9600分
        self.assertEqual(self.timesheet.total_premium_minutes, 0)
        self.assertEqual(self.timesheet.total_deduction_minutes, 0)

    def test_non_monthly_range_pattern(self):
        """月単位時間範囲以外のパターンでは割増・控除時間は0"""
        # 割増方式のパターンに変更
        pattern_premium = OvertimePattern.objects.create(
            name='割増',
            calculate_midnight_premium=False,
            calculation_type='premium',
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
        )
        self.staff_contract.overtime_pattern = pattern_premium
        self.staff_contract.save()
        
        # 180時間勤務（月単位時間範囲なら割増になるが、割増方式なので0）
        for day in range(1, 21):
            self._create_timecard(
                date(2023, 1, day),
                time(9, 0),
                time(19, 0),
                60
            )
        
        self.timesheet.refresh_from_db()
        self.assertEqual(self.timesheet.total_work_minutes, 180 * 60)
        self.assertEqual(self.timesheet.total_premium_minutes, 0)
        self.assertEqual(self.timesheet.total_deduction_minutes, 0)
