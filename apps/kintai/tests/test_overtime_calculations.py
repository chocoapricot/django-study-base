from django.test import TestCase
from apps.kintai.models import StaffTimecard, StaffTimesheet
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import OvertimePattern, ContractPattern, EmploymentType
from datetime import date, time

class OvertimeCalculationTest(TestCase):
    """各計算方式における残業・割増・控除・深夜時間の計算テスト"""

    @classmethod
    def setUpTestData(cls):
        # --- Master Data ---
        cls.emp_type = EmploymentType.objects.create(name="正社員")
        cls.contract_pattern = ContractPattern.objects.create(name="test", domain='1')

        # --- Staff ---
        cls.staff = Staff.objects.create(
            name_last='テスト', name_first='太郎',
        )

    def _create_contract(self, overtime_pattern):
        """指定された時間外パターンで契約を作成"""
        return StaffContract.objects.create(
            staff=self.staff,
            contract_name=f'Contract {overtime_pattern.calculation_type}',
            start_date=date(2023, 1, 1),
            contract_pattern=self.contract_pattern,
            overtime_pattern=overtime_pattern,
        )

    def _create_timesheet(self, contract, target_month):
        """タイムシートを作成"""
        return StaffTimesheet.objects.create(
            staff_contract=contract,
            staff=self.staff,
            target_month=target_month,
        )

    def _create_timecard(self, contract, timesheet, work_date, start_time, end_time, break_minutes):
        """タイムカードを作成"""
        timecard = StaffTimecard(
            staff_contract=contract,
            timesheet=timesheet,
            work_date=work_date,
            work_type='10',
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
        )
        timecard.save()
        return timecard

    # -------------------------------------------------------------------------
    # 1. 割増方式 (Premium)
    # -------------------------------------------------------------------------
    def test_premium_midnight_overtime(self):
        """割増方式：深夜残業のテスト"""
        pattern = OvertimePattern.objects.create(
            name='割増・深夜あり',
            calculation_type='premium',
            calculate_midnight_premium=True,
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
        )
        contract = self._create_contract(pattern)
        timesheet = self._create_timesheet(contract, date(2023, 4, 1))

        # 13:00 - 23:00 (休憩60分) -> 労働9時間
        # 22:00 - 23:00 は深夜時間 (1時間)
        # 8時間を超える1時間が残業
        self._create_timecard(
            contract, timesheet, date(2023, 4, 1),
            time(13, 0), time(23, 0), 60
        )

        timesheet.refresh_from_db()
        self.assertEqual(timesheet.total_work_minutes, 9 * 60)
        self.assertEqual(timesheet.total_overtime_minutes, 1 * 60)
        self.assertEqual(timesheet.total_late_night_overtime_minutes, 1 * 60)

    # -------------------------------------------------------------------------
    # 2. 月単位時間範囲 (Monthly Range)
    # -------------------------------------------------------------------------
    def test_monthly_range_midnight_overtime(self):
        """月単位時間範囲：深夜残業のテスト"""
        pattern = OvertimePattern.objects.create(
            name='月単位時間範囲・深夜あり',
            calculation_type='monthly_range',
            monthly_range_min=140,
            monthly_range_max=160,
            calculate_midnight_premium=True,
        )
        contract = self._create_contract(pattern)
        timesheet = self._create_timesheet(contract, date(2023, 4, 1))

        # 13:00 - 23:00 (休憩60分) -> 労働9時間
        # 22:00 - 23:00 は深夜時間 (1時間)
        self._create_timecard(
            contract, timesheet, date(2023, 4, 1),
            time(13, 0), time(23, 0), 60
        )

        timesheet.refresh_from_db()
        self.assertEqual(timesheet.total_work_minutes, 9 * 60)
        self.assertEqual(timesheet.total_late_night_overtime_minutes, 1 * 60)

    # -------------------------------------------------------------------------
    # 3. 1ヶ月単位変形労働 (Variable)
    # -------------------------------------------------------------------------
    def test_variable_monthly_premium_and_midnight(self):
        """1ヶ月単位変形労働：月単位割増と深夜残業のテスト"""
        pattern = OvertimePattern.objects.create(
            name='変形労働・月割増・深夜あり',
            calculation_type='variable',
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
            days_30_hours=171, days_30_minutes=0, # 4月(30日)の基準時間
            monthly_overtime_enabled=True,
            monthly_overtime_hours=10, # 閾値を低く設定してテストしやすくする
            calculate_midnight_premium=True,
        )
        contract = self._create_contract(pattern)
        timesheet = self._create_timesheet(contract, date(2023, 4, 1)) # 30日

        # 1. 深夜残業を含む勤務
        # 13:00 - 23:00 (休憩60分) -> 労働9時間
        # 残業: 1時間 (8時間超過)
        # 深夜: 1時間 (22:00-23:00)
        self._create_timecard(
            contract, timesheet, date(2023, 4, 1),
            time(13, 0), time(23, 0), 60
        )

        # 2. 変形時間と月単位割増を発生させるための追加勤務
        # 基準時間171時間を超えるように勤務を追加
        # 既に9時間勤務。残り162時間 + α
        # 1日9時間(残業1h) * 19日 = 171時間 (残業19h)
        # 合計労働: 9 + 171 = 180時間
        # 合計残業: 1 + 19 = 20時間
        # 実労働(変形判定用): 180 - 20 = 160時間 < 171時間 なので変形時間は0
        
        # 変形時間を発生させるには、残業にならない労働時間を増やす必要がある
        # 1日8時間 * 21日 = 168時間
        # 合計労働: 9 + 168 = 177時間
        # 合計残業: 1時間
        # 実労働: 177 - 1 = 176時間 > 171時間 -> 変形時間 5時間
        
        for day in range(2, 23):
            self._create_timecard(
                contract, timesheet, date(2023, 4, day),
                time(9, 0), time(18, 0), 60 # 8時間
            )

        timesheet.refresh_from_db()
        
        # 総労働時間: 9 + 168 = 177時間 = 10620分
        self.assertEqual(timesheet.total_work_minutes, 10620)
        
        # 総残業時間: 1時間 = 60分
        self.assertEqual(timesheet.total_overtime_minutes, 60)
        
        # 変形時間: 176 - 171 = 5時間 = 300分
        self.assertEqual(timesheet.total_variable_minutes, 300)
        
        # 深夜時間: 1時間 = 60分
        self.assertEqual(timesheet.total_late_night_overtime_minutes, 60)
        
        # 月単位割増:
        # 残業(1h) + 変形(5h) = 6h
        # 閾値(10h)を超えていないので割増は0
        self.assertEqual(timesheet.total_premium_minutes, 0)
        
        # さらに勤務を追加して月単位割増を発生させる
        # 変形時間をさらに5時間増やす (1日8時間 * 1日追加 -> 実労働184時間 -> 変形13時間)
        # 合計: 残業1h + 変形13h = 14h > 10h -> 割増4時間
        self._create_timecard(
            contract, timesheet, date(2023, 4, 23),
            time(9, 0), time(18, 0), 60 # 8時間
        )
        
        timesheet.refresh_from_db()
        
        # 変形時間: (176+8) - 171 = 13時間 = 780分
        self.assertEqual(timesheet.total_variable_minutes, 780)
        
        # 月単位割増: (1 + 13) - 10 = 4時間 = 240分
        self.assertEqual(timesheet.total_premium_minutes, 240)


    # -------------------------------------------------------------------------
    # 4. 1ヶ月単位フレックス (Flextime)
    # -------------------------------------------------------------------------
    def test_flextime_overtime_and_premium(self):
        """1ヶ月単位フレックス：残業と月単位割増のテスト"""
        pattern = OvertimePattern.objects.create(
            name='フレックス・月割増あり',
            calculation_type='flextime',
            days_30_hours=160, days_30_minutes=0, # 4月(30日)の法定労働時間
            monthly_overtime_enabled=True,
            monthly_overtime_hours=20, # 20時間超過で割増
        )
        contract = self._create_contract(pattern)
        timesheet = self._create_timesheet(contract, date(2023, 4, 1))

        # 185時間勤務させる (法定160時間 + 25時間)
        # 1日9.25時間 * 20日 = 185時間
        # 9.25h = 9時間15分 = 555分
        for day in range(1, 21):
            self._create_timecard(
                contract, timesheet, date(2023, 4, day),
                time(9, 0), time(18, 15), 0
            )

        timesheet.refresh_from_db()

        # 総労働時間: 185時間 = 11100分
        self.assertEqual(timesheet.total_work_minutes, 11100)

        # 残業時間: 185 - 160 = 25時間 = 1500分
        self.assertEqual(timesheet.total_overtime_minutes, 1500)

        # 割増時間: 25 - 20 = 5時間 = 300分
        self.assertEqual(timesheet.total_premium_minutes, 300)

    def test_flextime_deduction(self):
        """1ヶ月単位フレックス：控除時間のテスト"""
        pattern = OvertimePattern.objects.create(
            name='フレックス・控除あり',
            calculation_type='flextime',
            days_30_hours=160, days_30_minutes=0,
        )
        contract = self._create_contract(pattern)
        timesheet = self._create_timesheet(contract, date(2023, 4, 1))

        # 150時間勤務させる (法定160時間 - 10時間)
        # 1日7.5時間 * 20日 = 150時間
        # 7.5h = 7時間30分 = 450分
        for day in range(1, 21):
            self._create_timecard(
                contract, timesheet, date(2023, 4, day),
                time(9, 0), time(16, 30), 0
            )

        timesheet.refresh_from_db()

        # 総労働時間: 150時間 = 9000分
        self.assertEqual(timesheet.total_work_minutes, 9000)

        # 残業時間: 0
        self.assertEqual(timesheet.total_overtime_minutes, 0)

        # 控除時間: 160 - 150 = 10時間 = 600分
        self.assertEqual(timesheet.total_deduction_minutes, 600)

    def test_flextime_midnight(self):
        """1ヶ月単位フレックス：深夜残業のテスト"""
        pattern = OvertimePattern.objects.create(
            name='フレックス・深夜あり',
            calculation_type='flextime',
            days_30_hours=160, days_30_minutes=0,
            calculate_midnight_premium=True,
        )
        contract = self._create_contract(pattern)
        timesheet = self._create_timesheet(contract, date(2023, 4, 1))

        # 深夜勤務を含む勤務
        # 14:00 - 23:00 (休憩60分) -> 労働8時間
        # 22:00 - 23:00 は深夜 (1時間)
        self._create_timecard(
            contract, timesheet, date(2023, 4, 1),
            time(14, 0), time(23, 0), 60
        )

        timesheet.refresh_from_db()

        self.assertEqual(timesheet.total_work_minutes, 480)
        self.assertEqual(timesheet.total_late_night_overtime_minutes, 60)
