from django.test import TestCase
from apps.kintai.models import StaffTimecard, StaffTimesheet
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models_contract import OvertimePattern, ContractPattern, EmploymentType
from datetime import date, time, timedelta

class StaffTimesheetFlexibleOvertimeTest(TestCase):
    """1ヶ月単位変形労働制の計算ロジックテスト"""

    @classmethod
    def setUpTestData(cls):
        # --- Master Data ---
        cls.emp_type = EmploymentType.objects.create(name="正社員")
        cls.contract_pattern = ContractPattern.objects.create(name="test", domain='1')

        # --- Overtime Pattern (変形労働) ---
        cls.pattern_flexible = OvertimePattern.objects.create(
            name='変形労働',
            calculate_midnight_premium=False,
            calculation_type='flexible',
            # 日単位設定: 8時間30分
            flexible_daily_overtime_enabled=True,
            flexible_daily_overtime_hours=8,
            flexible_daily_overtime_minutes=30,
            # 月次基準時間設定
            days_28_hours=160, days_28_minutes=0,
            days_29_hours=165, days_29_minutes=0,
            days_30_hours=171, days_30_minutes=0,
            days_31_hours=177, days_31_minutes=0,
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
            overtime_pattern=cls.pattern_flexible,
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

    def test_daily_overtime_calculation(self):
        """日単位の残業計算テスト（8時間30分超過分が残業）"""
        # 2023年2月（28日）のタイムシート
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2023, 2, 1),
        )

        # ケース1: 9時間勤務（休憩なし） -> 30分残業
        # 8:30 + 0:30 = 9:00
        tc1 = self._create_timecard(
            timesheet, date(2023, 2, 1),
            time(9, 0), time(18, 0), 0
        )
        self.assertEqual(tc1.work_minutes, 540)  # 9時間
        self.assertEqual(tc1.overtime_minutes, 30)

        # ケース2: 8時間30分勤務 -> 残業0
        tc2 = self._create_timecard(
            timesheet, date(2023, 2, 2),
            time(9, 0), time(17, 30), 0
        )
        self.assertEqual(tc2.work_minutes, 510)  # 8.5時間
        self.assertEqual(tc2.overtime_minutes, 0)

    def test_monthly_premium_calculation_28_days(self):
        """28日の月での割増計算テスト（基準160時間）"""
        # 2023年2月（28日）
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2023, 2, 1),
        )

        # 基準時間: 160時間 = 9600分

        # 1. 残業が発生する勤務: 10日間
        # 1日9時間30分勤務（内、残業1時間）
        # 総労働: 9.5h * 10 = 95h
        # 残業: 1h * 10 = 10h
        # 実労働貢献: 8.5h * 10 = 85h
        for day in range(1, 11):
            self._create_timecard(
                timesheet, date(2023, 2, day),
                time(9, 0), time(18, 30), 0
            )

        # 2. 残業が発生しない勤務: 10日間
        # 1日8時間勤務
        # 総労働: 8h * 10 = 80h
        # 残業: 0h
        # 実労働貢献: 8h * 10 = 80h
        for day in range(11, 21):
            self._create_timecard(
                timesheet, date(2023, 2, day),
                time(9, 0), time(17, 0), 0
            )

        # 集計
        # 総労働時間 = 95h + 80h = 175h = 10500分
        # 総残業時間 = 10h = 600分
        # 実労働時間（割増判定用） = 175h - 10h = 165h = 9900分
        
        # 基準時間(160h)との差分
        # 165h - 160h = 5h = 300分 -> これが割増時間になるはず

        timesheet.refresh_from_db()
        
        self.assertEqual(timesheet.total_work_minutes, 10500)
        self.assertEqual(timesheet.total_overtime_minutes, 600)
        
        # 割増時間の検証
        expected_premium = (165 - 160) * 60
        self.assertEqual(timesheet.total_premium_minutes, expected_premium)

    def test_monthly_premium_calculation_31_days(self):
        """31日の月での割増計算テスト（基準177時間）"""
        # 2023年1月（31日）
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2023, 1, 1),
        )

        # 基準時間: 177時間 = 10620分

        # 1日9時間勤務（休憩なし）を20日間
        # 日単位残業設定は8.5hなので、毎日0.5hの残業が発生
        # 総労働: 9h * 20 = 180h
        # 残業: 0.5h * 20 = 10h
        # 実労働貢献: 8.5h * 20 = 170h
        for day in range(1, 21):
            self._create_timecard(
                timesheet, date(2023, 1, day),
                time(9, 0), time(18, 0), 0
            )
        
        # 追加で1日8時間勤務を1日
        # 総労働: 8h
        # 残業: 0h
        # 実労働貢献: 8h
        self._create_timecard(
            timesheet, date(2023, 1, 21),
            time(9, 0), time(17, 0), 0
        )

        # 集計
        # 総労働時間 = 180h + 8h = 188h = 11280分
        # 総残業時間 = 10h = 600分
        # 実労働時間（割増判定用） = 188h - 10h = 178h = 10680分
        
        # 基準時間(177h)との差分
        # 178h - 177h = 1h = 60分 -> これが割増時間になるはず

        timesheet.refresh_from_db()
        
        self.assertEqual(timesheet.total_work_minutes, 11280)
        self.assertEqual(timesheet.total_overtime_minutes, 600)
        
        # 割増時間の検証
        expected_premium = (178 - 177) * 60
        self.assertEqual(timesheet.total_premium_minutes, expected_premium)
