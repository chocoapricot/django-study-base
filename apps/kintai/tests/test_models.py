from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, time
from decimal import Decimal
from apps.kintai.models import StaffTimesheet, StaffTimecard
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern, WorkTimePattern
from apps.common.constants import Constants


class StaffTimesheetModelTest(TestCase):
    """月次勤怠モデルのテスト"""

    def setUp(self):
        """テストデータの準備"""
        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            email='yamada@example.com',
            employee_no='EMP001',
            hire_date=date(2024, 4, 1)
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # 契約書パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            domain=Constants.DOMAIN.STAFF
        )

        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31)
        )

    def test_create_timesheet(self):
        """月次勤怠の作成テスト"""
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )
        self.assertEqual(timesheet.target_month, date(2024, 11, 1))
        self.assertEqual(timesheet.status, '10')  # 作成中
        self.assertEqual(timesheet.total_work_days, 0)

    def test_auto_set_staff(self):
        """スタッフ契約からスタッフを自動設定するテスト"""
        # 新しい契約を作成
        new_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約2',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31)
        )
        timesheet = StaffTimesheet.objects.create(
            staff_contract=new_contract,
            target_month=date(2024, 12, 1)
        )
        self.assertEqual(timesheet.staff, self.staff)

    def test_unique_constraint(self):
        """同一契約・年月の重複制約テスト"""
        StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )
        # 同じ契約・年月で作成しようとするとエラー
        with self.assertRaises(Exception):
            StaffTimesheet.objects.create(
                staff_contract=self.staff_contract,
                staff=self.staff,
                target_month=date(2024, 11, 1)
            )

    def test_is_editable(self):
        """編集可能判定のテスト"""
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1),
            status='10'  # 作成中
        )
        self.assertTrue(timesheet.is_editable)

        timesheet.status = '20'  # 提出済み
        timesheet.save()
        self.assertFalse(timesheet.is_editable)

    def test_str_method(self):
        """文字列表現のテスト"""
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )
        # スタッフの__str__は「姓 名」の形式（スペース入り）
        self.assertEqual(str(timesheet), '山田 太郎 - 2024年11月')


class StaffTimecardModelTest(TestCase):
    """日次勤怠モデルのテスト"""

    def setUp(self):
        """テストデータの準備"""
        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            email='yamada@example.com',
            employee_no='EMP001',
            hire_date=date(2024, 4, 1)
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # 契約書パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            domain=Constants.DOMAIN.STAFF
        )

        # 就業時間パターン作成
        self.worktime_pattern = WorkTimePattern.objects.create(
            name='標準勤務'
        )

        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            worktime_pattern=self.worktime_pattern
        )

        # 月次勤怠作成
        self.timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )

    def test_create_timecard(self):
        """日次勤怠の作成テスト"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 1),
            work_type='10',  # 出勤
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60
        )
        self.assertEqual(timecard.work_date, date(2024, 11, 1))
        self.assertEqual(timecard.work_type, '10')

    def test_calculate_work_hours(self):
        """労働時間計算のテスト"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 1),
            work_type='10',  # 出勤
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60
        )
        # 9:00-18:00で休憩60分 = 8時間 = 480分
        self.assertEqual(timecard.work_minutes, 480)
        self.assertEqual(timecard.overtime_minutes, 0)

    def test_calculate_overtime(self):
        """残業時間計算のテスト"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 1),
            work_type='10',  # 出勤
            start_time=time(9, 0),
            end_time=time(20, 0),  # 20時まで
            break_minutes=60
        )
        # 9:00-20:00で休憩60分 = 10時間 = 600分 (残業2時間 = 120分)
        self.assertEqual(timecard.work_minutes, 600)
        self.assertEqual(timecard.overtime_minutes, 120)

    def test_invalid_time_range(self):
        """無効な時刻範囲のバリデーションテスト"""
        timecard = StaffTimecard(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 1),
            work_type='10',  # 出勤
            start_time=time(18, 0),
            end_time=time(9, 0)  # 退勤が出勤より前
        )
        with self.assertRaises(ValidationError):
            timecard.full_clean()

    def test_str_method(self):
        """文字列表現のテスト"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 1),
            work_type='10',
            start_time=time(9, 0),
            end_time=time(18, 0)
        )
        self.assertEqual(str(timecard), '山田 太郎 - 2024-11-01')


class StaffTimecardLateNightOvertimeTest(TestCase):
    """日次勤怠モデルの深夜残業時間テスト"""

    def setUp(self):
        """テストデータの準備"""
        # Staff, EmploymentType, ContractPattern, WorkTimePattern, StaffContract, StaffTimesheet
        self.staff = Staff.objects.create(name_last='テスト', name_first='ユーザー')
        self.employment_type = EmploymentType.objects.create(name='契約社員')
        self.contract_pattern = ContractPattern.objects.create(name='標準', domain=Constants.DOMAIN.STAFF)
        self.worktime_pattern = WorkTimePattern.objects.create(name='標準勤務')
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            worktime_pattern=self.worktime_pattern,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )

    def test_calculate_late_night_overtime_no_overtime(self):
        """深夜残業なし（通常勤務）"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60
        )
        self.assertEqual(timecard.late_night_overtime_minutes, 0)

    def test_calculate_late_night_overtime_within_one_day(self):
        """日をまたがない深夜残業"""
        # 22:00から24:00(翌0:00)までの2時間が深夜残業
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(14, 0),
            end_time=time(0, 0),
            end_time_next_day=True,
            break_minutes=60
        )
        # 14:00-24:00 (10時間) - 休憩1時間 = 9時間労働
        # 深夜時間は 22:00-24:00 の2時間 = 120分
        # 休憩は深夜時間外なので深夜労働時間には影響しない
        self.assertEqual(timecard.late_night_overtime_minutes, 120)

    def test_calculate_late_night_overtime_across_midnight(self):
        """日をまたぐ深夜残業"""
        # 22:00から翌朝6:00まで勤務
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(22, 0),
            end_time=time(6, 0),
            end_time_next_day=True,
            break_minutes=0
        )
        # 22:00-06:00 (8時間)
        # 深夜時間は 22:00-05:00 の7時間 = 420分
        self.assertEqual(timecard.late_night_overtime_minutes, 420)

    def test_calculate_late_night_overtime_with_break(self):
        """休憩ありの日をまたぐ深夜残業"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(20, 0),
            end_time=time(5, 0), # 翌朝5時
            end_time_next_day=True,
            break_minutes=60
        )
        # 20:00-05:00 (9時間=540分) - 休憩1時間 = 8時間労働
        # 深夜時間は 22:00-05:00 の7時間 = 420分
        # 休憩は深夜時間外なので深夜労働時間には影響しない
        self.assertEqual(timecard.late_night_overtime_minutes, 420)

    def test_calculate_late_night_overtime_full_night(self):
        """フル深夜勤務"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(22, 0),
            end_time=time(5, 0),
            end_time_next_day=True,
            break_minutes=0
        )
        # 22:00-05:00 (7時間) - 休憩0 = 7時間労働
        # 深夜時間は7時間すべて = 420分
        self.assertEqual(timecard.late_night_overtime_minutes, 420)

    def test_calculate_late_night_overtime_with_late_night_break(self):
        """深夜休憩ありの深夜残業"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(22, 0),
            end_time=time(5, 0),
            end_time_next_day=True,
            break_minutes=0,
            late_night_break_minutes=60
        )
        # 22:00-05:00 (7時間)
        # 深夜時間 420分 - 深夜休憩 60分 = 360分
        self.assertEqual(timecard.late_night_overtime_minutes, 360)

    def test_calculate_late_night_overtime_with_both_breaks(self):
        """通常休憩と深夜休憩ありの深夜残業"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(20, 0),
            end_time=time(5, 0),
            end_time_next_day=True,
            break_minutes=30,
            late_night_break_minutes=60
        )
        # 20:00-05:00 (9時間=540分)
        # 総労働時間: 540分 - (通常休憩30分 + 深夜休憩60分) = 450分
        self.assertEqual(timecard.work_minutes, 450)
        # 深夜時間(22:00-05:00): 7時間 = 420分
        # 深夜労働時間: 420分 - 深夜休憩60分 = 360分
        self.assertEqual(timecard.late_night_overtime_minutes, 360)

    def test_calculate_late_night_overtime_within_one_day_with_late_night_break(self):
        """日をまたがない深夜残業（深夜休憩あり）"""
        timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            work_date=date(2024, 11, 5),
            work_type='10',
            start_time=time(18, 0),
            end_time=time(0, 0),
            end_time_next_day=True,
            break_minutes=30,
            late_night_break_minutes=30
        )
        # 18:00-24:00 (6時間=360分)
        # 総労働時間: 360分 - (通常休憩30分 + 深夜休憩30分) = 300分
        self.assertEqual(timecard.work_minutes, 300)
        # 深夜時間(22:00-24:00): 2時間 = 120分
        # 深夜労働時間: 120分 - 深夜休憩30分 = 90分
        self.assertEqual(timecard.late_night_overtime_minutes, 90)
