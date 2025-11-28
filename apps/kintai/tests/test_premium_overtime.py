from django.test import TestCase
from apps.kintai.models import StaffTimecard, StaffTimesheet
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models_contract import OvertimePattern, ContractPattern, EmploymentType
from datetime import date, time

class StaffTimesheetPremiumOvertimeTest(TestCase):
    """割増方式の月単位時間外割増計算テスト"""

    @classmethod
    def setUpTestData(cls):
        # --- Master Data ---
        cls.emp_type = EmploymentType.objects.create(name="正社員")
        cls.contract_pattern = ContractPattern.objects.create(name="test", domain='1')

        # --- Overtime Pattern (割増方式) ---
        cls.pattern_premium = OvertimePattern.objects.create(
            name='割増',
            calculate_midnight_premium=False,
            calculation_type='premium',
            # 日単位設定: 8時間
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
            daily_overtime_minutes=0,
            # 月単位時間外割増設定: 45時間
            monthly_overtime_enabled=True,
            monthly_overtime_hours=45,
        )

        # --- Staff and Contract ---
        cls.staff = Staff.objects.create(
            name_last='テスト', name_first='次郎',
        )
        cls.staff_contract = StaffContract.objects.create(
            staff=cls.staff,
            contract_name='Premium Contract',
            start_date=date(2023, 4, 1),
            contract_pattern=cls.contract_pattern,
            overtime_pattern=cls.pattern_premium,
        )

    def _create_timecard(self, timesheet, work_date, start_time, end_time, break_minutes):
        """タイムカードを作成するヘルパーメソッド"""
        timecard = StaffTimecard(
            staff_contract=self.staff_contract,
            timesheet=timesheet,
            work_date=work_date,
            work_type='10',
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
        )
        timecard.save()
        return timecard

    def test_monthly_premium_calculation(self):
        """月単位時間外割増の計算テスト（45時間超過分が割増）"""
        # 2023年4月
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2023, 4, 1),
        )

        # 月の残業時間が45時間を超えるようにデータを作成
        # 1日10時間勤務（休憩0） -> 労働10h, 残業2h
        # 23日間勤務 -> 総残業 2h * 23 = 46h
        
        for day in range(1, 24):
            self._create_timecard(
                timesheet, date(2023, 4, day),
                time(9, 0), time(19, 0), 0
            )

        # 集計
        # 総労働時間 = 10h * 23 = 230h = 13800分
        # 総残業時間 = 2h * 23 = 46h = 2760分
        
        # 月単位割増基準: 45h = 2700分
        # 割増時間 = 46h - 45h = 1h = 60分

        timesheet.refresh_from_db()
        
        self.assertEqual(timesheet.total_work_minutes, 13800)
        self.assertEqual(timesheet.total_overtime_minutes, 2760)
        
        # 割増時間の検証
        expected_premium = (46 - 45) * 60
        self.assertEqual(timesheet.total_premium_minutes, expected_premium)

    def test_monthly_premium_calculation_not_exceeded(self):
        """月単位時間外割増を超えない場合のテスト"""
        # 2023年5月
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2023, 5, 1),
        )

        # 月の残業時間が45時間ちょうどのケース
        # 1日10時間勤務（休憩0） -> 残業2h
        # 22日間勤務 -> 総残業 2h * 22 = 44h
        # プラス 1日9時間勤務 -> 残業1h
        # 合計残業 45h
        
        for day in range(1, 23):
            self._create_timecard(
                timesheet, date(2023, 5, day),
                time(9, 0), time(19, 0), 0
            )
        
        self._create_timecard(
            timesheet, date(2023, 5, 23),
            time(9, 0), time(18, 0), 0
        )

        # 集計
        # 総残業時間 = 44h + 1h = 45h = 2700分
        
        # 月単位割増基準: 45h
        # 割増時間 = 0

        timesheet.refresh_from_db()
        
        self.assertEqual(timesheet.total_overtime_minutes, 2700)
        self.assertEqual(timesheet.total_premium_minutes, 0)
