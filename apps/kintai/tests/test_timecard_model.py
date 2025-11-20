from django.test import TestCase
from apps.kintai.models import StaffTimecard, StaffTimesheet
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models_contract import OvertimePattern, ContractPattern, EmploymentType
from datetime import date, time

class StaffTimecardModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # --- Master Data ---
        cls.emp_type = EmploymentType.objects.create(name="正社員")
        cls.contract_pattern = ContractPattern.objects.create(name="test", domain='1')

        # --- Overtime Patterns ---
        cls.pattern_all_disabled = OvertimePattern.objects.create(
            name='すべて無効',
            calculate_midnight_premium=False,
            calculation_type='premium',
            daily_overtime_enabled=False,
        )
        cls.pattern_late_night_only = OvertimePattern.objects.create(
            name='深夜のみ有効',
            calculate_midnight_premium=True,
            calculation_type='premium',
            daily_overtime_enabled=False,
        )
        cls.pattern_overtime_8h_only = OvertimePattern.objects.create(
            name='時間外(8h)のみ有効',
            calculate_midnight_premium=False,
            calculation_type='premium',
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
        )
        cls.pattern_overtime_7h_late_night = OvertimePattern.objects.create(
            name='時間外(7h)と深夜が有効',
            calculate_midnight_premium=True,
            calculation_type='premium',
            daily_overtime_enabled=True,
            daily_overtime_hours=7,
        )
        cls.pattern_calc_type_not_premium = OvertimePattern.objects.create(
            name='割増以外',
            calculate_midnight_premium=True,
            calculation_type='monthly_range', # not 'premium'
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
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
            overtime_pattern=cls.pattern_all_disabled, # Default pattern
        )

        # --- Timesheet ---
        cls.timesheet = StaffTimesheet.objects.create(
            staff_contract=cls.staff_contract,
            staff=cls.staff,
            target_month=date(2023, 1, 1),
        )

    def _create_and_test_timecard(self, overtime_pattern, start_time, end_time, break_minutes, expected_work_min, expected_overtime_min, expected_late_night_min):
        """Helper function to create a timecard, test it, and return it."""
        self.staff_contract.overtime_pattern = overtime_pattern
        self.staff_contract.save()

        timecard = StaffTimecard(
            timesheet=self.timesheet,
            work_date=date(2023, 1, 10),
            work_type='10',
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
        )
        timecard.save()

        self.assertEqual(timecard.work_minutes, expected_work_min)
        self.assertEqual(timecard.overtime_minutes, expected_overtime_min)
        self.assertEqual(timecard.late_night_overtime_minutes, expected_late_night_min)
        return timecard

    def test_no_overtime_pattern(self):
        """時間外算出パターンが未設定の場合、すべて0になることをテスト"""
        # start: 9:00, end: 23:00, break: 60min -> work: 13h = 780min
        self._create_and_test_timecard(None, time(9, 0), time(23, 0), 60, 780, 0, 0)

    def test_all_disabled(self):
        """すべての計算が無効なパターンをテスト"""
        # start: 9:00, end: 23:00, break: 60min -> work: 13h = 780min
        self._create_and_test_timecard(self.pattern_all_disabled, time(9, 0), time(23, 0), 60, 780, 0, 0)

    def test_late_night_overtime_enabled(self):
        """深夜割増が有効な場合をテスト"""
        # start: 18:00, end: 23:00, break: 0 -> work: 5h = 300min
        # Late night: 22:00-23:00 = 60min
        timecard = self._create_and_test_timecard(self.pattern_late_night_only, time(18, 0), time(23, 0), 0, 300, 0, 60)
        timecard.late_night_break_minutes = 15
        timecard.save()
        self.assertEqual(timecard.late_night_overtime_minutes, 45) # 60 - 15

    def test_late_night_overtime_disabled(self):
        """深夜割増が無効な場合をテスト"""
        # start: 18:00, end: 23:00, break: 0 -> work: 5h = 300min
        self._create_and_test_timecard(self.pattern_overtime_8h_only, time(18, 0), time(23, 0), 0, 300, 0, 0)

    def test_daily_overtime_8h_enabled(self):
        """日単位時間外(8h)が有効な場合をテスト"""
        # start: 9:00, end: 19:00, break: 60min -> work: 9h = 540min
        # Overtime (8h): 540 - 480 = 60min
        self._create_and_test_timecard(self.pattern_overtime_8h_only, time(9, 0), time(19, 0), 60, 540, 60, 0)

    def test_daily_overtime_7h_enabled(self):
        """日単位時間外(7h)が有効な場合をテスト"""
        # start: 9:00, end: 19:00, break: 60min -> work: 9h = 540min
        # Overtime (7h): 540 - 420 = 120min
        self._create_and_test_timecard(self.pattern_overtime_7h_late_night, time(9, 0), time(19, 0), 60, 540, 120, 0)

    def test_daily_overtime_disabled(self):
        """日単位時間外が無効な場合をテスト"""
        # start: 9:00, end: 19:00, break: 60min -> work: 9h = 540min
        self._create_and_test_timecard(self.pattern_late_night_only, time(9, 0), time(19, 0), 60, 540, 0, 0)

    def test_calculation_type_not_premium(self):
        """計算方式が「割増」でない場合、時間外が計算されないことをテスト"""
        # start: 9:00, end: 19:00, break: 60min -> work: 9h = 540min
        # Late night should be 0 as there are no late night hours
        self._create_and_test_timecard(self.pattern_calc_type_not_premium, time(9, 0), time(19, 0), 60, 540, 0, 0)

    def test_combined_overtime_and_late_night(self):
        """時間外と深夜の両方が有効な場合をテスト"""
        # start: 13:00, end: 23:00, break: 60min -> work: 9h = 540min
        # Overtime (7h): 540 - 420 = 120min
        # Late night: 22:00-23:00 = 60min
        self._create_and_test_timecard(self.pattern_overtime_7h_late_night, time(13, 0), time(23, 0), 60, 540, 120, 60)
