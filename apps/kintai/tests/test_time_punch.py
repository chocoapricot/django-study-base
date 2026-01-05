from django.test import TestCase
from datetime import datetime, date
from apps.kintai.models import StaffTimerecord, StaffTimerecordBreak
from apps.kintai.utils import round_time, apply_time_punch, apply_break_time_punch
from apps.master.models_kintai import TimePunch
from apps.master.models_contract import ContractPattern
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.common.constants import Constants


class TimePunchUtilsTest(TestCase):
    """勤怠打刻ユーティリティ関数のテスト"""
    
    def test_round_time_10min_ceil(self):
        """10分単位切り上げのテスト"""
        # 例: 開始時刻で10分単位、切り上げ
        test_cases = [
            (datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:00 -> 9:00
            (datetime(2024, 1, 1, 9, 1, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:01 -> 9:10
            (datetime(2024, 1, 1, 9, 4, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:04 -> 9:10
            (datetime(2024, 1, 1, 9, 5, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:05 -> 9:10
            (datetime(2024, 1, 1, 9, 9, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:09 -> 9:10
            (datetime(2024, 1, 1, 9, 10, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:10 -> 9:10
        ]
        
        for input_time, expected_time in test_cases:
            with self.subTest(input_time=input_time):
                result = round_time(input_time, 10, Constants.TIME_ROUNDING_METHOD.CEIL)
                self.assertEqual(result, expected_time)
    
    def test_round_time_10min_floor(self):
        """10分単位切り捨てのテスト"""
        # 例: 開始時刻で10分単位、切り捨て
        test_cases = [
            (datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:00 -> 9:00
            (datetime(2024, 1, 1, 9, 1, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:01 -> 9:00
            (datetime(2024, 1, 1, 9, 4, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:04 -> 9:00
            (datetime(2024, 1, 1, 9, 5, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:05 -> 9:00
            (datetime(2024, 1, 1, 9, 9, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:09 -> 9:00
            (datetime(2024, 1, 1, 9, 10, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:10 -> 9:10
        ]
        
        for input_time, expected_time in test_cases:
            with self.subTest(input_time=input_time):
                result = round_time(input_time, 10, Constants.TIME_ROUNDING_METHOD.FLOOR)
                self.assertEqual(result, expected_time)
    
    def test_round_time_10min_round(self):
        """10分単位四捨五入のテスト"""
        # 例: 開始時刻で10分単位、四捨五入
        test_cases = [
            (datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:00 -> 9:00
            (datetime(2024, 1, 1, 9, 1, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:01 -> 9:00
            (datetime(2024, 1, 1, 9, 4, 0), datetime(2024, 1, 1, 9, 0, 0)),  # 9:04 -> 9:00
            (datetime(2024, 1, 1, 9, 5, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:05 -> 9:10
            (datetime(2024, 1, 1, 9, 9, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:09 -> 9:10
            (datetime(2024, 1, 1, 9, 10, 0), datetime(2024, 1, 1, 9, 10, 0)), # 9:10 -> 9:10
        ]
        
        for input_time, expected_time in test_cases:
            with self.subTest(input_time=input_time):
                result = round_time(input_time, 10, Constants.TIME_ROUNDING_METHOD.ROUND)
                self.assertEqual(result, expected_time)
    
    def test_round_time_with_seconds(self):
        """秒を含む時刻の丸めテスト"""
        test_cases = [
            # 9:04:30 -> 9:05（5分単位四捨五入）
            (datetime(2024, 1, 1, 9, 4, 30), datetime(2024, 1, 1, 9, 5, 0)),
            # 9:02:29 -> 9:00（5分単位四捨五入）
            (datetime(2024, 1, 1, 9, 2, 29), datetime(2024, 1, 1, 9, 0, 0)),
            # 9:02:30 -> 9:05（5分単位四捨五入）
            (datetime(2024, 1, 1, 9, 2, 30), datetime(2024, 1, 1, 9, 5, 0)),
        ]
        
        for input_time, expected_time in test_cases:
            with self.subTest(input_time=input_time):
                result = round_time(input_time, 5, Constants.TIME_ROUNDING_METHOD.ROUND)
                self.assertEqual(result, expected_time)
    
    def test_round_time_hour_overflow(self):
        """時間をまたぐ丸めのテスト"""
        test_cases = [
            # 9:59 -> 10:00（10分単位四捨五入）
            (datetime(2024, 1, 1, 9, 59, 0), datetime(2024, 1, 1, 10, 0, 0)),
            # 9:55 -> 10:00（10分単位切り上げ）
            (datetime(2024, 1, 1, 9, 55, 0), datetime(2024, 1, 1, 10, 0, 0)),
        ]
        
        for input_time, expected_time in test_cases:
            with self.subTest(input_time=input_time):
                result = round_time(input_time, 10, Constants.TIME_ROUNDING_METHOD.ROUND)
                self.assertEqual(result, expected_time)

    def test_round_time_1min_truncate(self):
        """1分単位の丸めが秒の切り捨てとして機能することを確認するテスト"""
        input_time = datetime(2024, 1, 1, 9, 0, 30)
        expected_time = datetime(2024, 1, 1, 9, 0, 0)

        methods = [
            Constants.TIME_ROUNDING_METHOD.CEIL,
            Constants.TIME_ROUNDING_METHOD.FLOOR,
            Constants.TIME_ROUNDING_METHOD.ROUND,
        ]

        for method in methods:
            with self.subTest(method=method):
                result = round_time(input_time, 1, method)
                self.assertEqual(result, expected_time)


class StaffTimerecordRoundingTest(TestCase):
    """StaffTimerecordモデルの時刻丸め機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # スタッフを作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ'
        )
        
        # 契約パターンを作成
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain=Constants.DOMAIN.STAFF
        )
        
        # 時間丸め設定を作成（10分単位、開始時刻切り上げ、終了時刻切り捨て）
        self.time_punch = TimePunch.objects.create(
            name='テスト用丸め設定',
            start_time_unit=10,
            start_time_method=Constants.TIME_ROUNDING_METHOD.CEIL,
            end_time_unit=10,
            end_time_method=Constants.TIME_ROUNDING_METHOD.FLOOR,
            break_input=True,
            break_start_unit=5,
            break_start_method=Constants.TIME_ROUNDING_METHOD.ROUND,
            break_end_unit=5,
            break_end_method=Constants.TIME_ROUNDING_METHOD.ROUND
        )
        
        # スタッフ契約を作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 1, 1),
            time_punch=self.time_punch
        )
    
    def test_timerecord_rounding_with_config(self):
        """時間丸め設定ありの勤怠打刻テスト"""
        # 勤怠打刻を作成
        timerecord = StaffTimerecord.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            work_date=date(2024, 1, 1),
            start_time=datetime(2024, 1, 1, 9, 3, 0),  # 9:03
            end_time=datetime(2024, 1, 1, 18, 7, 0)    # 18:07
        )
        
        # 丸め結果を確認
        # 開始時刻: 9:03 -> 9:10（10分単位切り上げ）
        # 終了時刻: 18:07 -> 18:00（10分単位切り捨て）
        self.assertEqual(timerecord.rounded_start_time, datetime(2024, 1, 1, 9, 10, 0))
        self.assertEqual(timerecord.rounded_end_time, datetime(2024, 1, 1, 18, 0, 0))
    
    def test_timerecord_rounding_without_config(self):
        """時間丸め設定なしの勤怠打刻テスト"""
        # 時間丸め設定なしのスタッフ契約を作成
        staff_contract_no_rounding = StaffContract.objects.create(
            staff=self.staff,
            contract_name='丸め設定なし契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 1, 1),
            time_punch=None
        )
        
        # 勤怠打刻を作成
        timerecord = StaffTimerecord.objects.create(
            staff_contract=staff_contract_no_rounding,
            staff=self.staff,
            work_date=date(2024, 1, 1),
            start_time=datetime(2024, 1, 1, 9, 3, 30),  # 9:03:30
            end_time=datetime(2024, 1, 1, 18, 7, 59)    # 18:07:59
        )
        
        # 丸め設定がない場合は秒が切り捨てられる
        self.assertEqual(timerecord.rounded_start_time, datetime(2024, 1, 1, 9, 3, 0))
        self.assertEqual(timerecord.rounded_end_time, datetime(2024, 1, 1, 18, 7, 0))
    
    def test_break_rounding_with_config(self):
        """休憩時間の丸めテスト"""
        # 勤怠打刻を作成
        timerecord = StaffTimerecord.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            work_date=date(2024, 1, 1),
            start_time=datetime(2024, 1, 1, 9, 0, 0),
            end_time=datetime(2024, 1, 1, 18, 0, 0)
        )
        
        # 休憩時間を作成
        break_record = StaffTimerecordBreak.objects.create(
            timerecord=timerecord,
            break_start=datetime(2024, 1, 1, 12, 2, 30),  # 12:02:30
            break_end=datetime(2024, 1, 1, 13, 8, 59)     # 13:08:59
        )
        
        # 休憩時間の丸め結果を確認
        # 休憩開始: 12:02:30 -> 12:02:00 -> 12:00:00 (5分単位四捨五入)
        # 休憩終了: 13:08:59 -> 13:08:00 -> 13:10:00 (5分単位四捨五入)
        self.assertEqual(break_record.rounded_break_start, datetime(2024, 1, 1, 12, 0, 0))
        self.assertEqual(break_record.rounded_break_end, datetime(2024, 1, 1, 13, 10, 0))
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 開始時刻のみの場合
        timerecord = StaffTimerecord.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            work_date=date(2024, 1, 1),
            start_time=datetime(2024, 1, 1, 9, 3, 0),
            end_time=None
        )
        
        self.assertEqual(timerecord.rounded_start_time, datetime(2024, 1, 1, 9, 10, 0))
        self.assertIsNone(timerecord.rounded_end_time)
        
        # 終了時刻のみの場合
        timerecord2 = StaffTimerecord.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            work_date=date(2024, 1, 2),
            start_time=None,
            end_time=datetime(2024, 1, 2, 18, 7, 0)
        )
        
        self.assertIsNone(timerecord2.rounded_start_time)
        self.assertEqual(timerecord2.rounded_end_time, datetime(2024, 1, 2, 18, 0, 0))
