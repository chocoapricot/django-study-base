from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from apps.kintai.models import StaffTimerecordApproval
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern
from apps.common.constants import Constants


class StaffTimerecordApprovalModelTest(TestCase):
    """勤怠申請承認モデルのテスト"""

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

    def test_create_approval(self):
        """勤怠申請承認の作成テスト"""
        approval = StaffTimerecordApproval.objects.create(
            staff=self.staff,
            staff_contract=self.staff_contract,
            closing_date=date(2026, 1, 31),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31)
        )
        self.assertEqual(approval.closing_date, date(2026, 1, 31))
        self.assertEqual(approval.status, '10')  # 作成中
        self.assertEqual(str(approval), '山田 太郎 - 2026-01-31締め')

    def test_auto_set_staff(self):
        """スタッフ契約からスタッフを自動設定するテスト"""
        approval = StaffTimerecordApproval.objects.create(
            staff_contract=self.staff_contract,
            closing_date=date(2026, 1, 31),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31)
        )
        self.assertEqual(approval.staff, self.staff)

    def test_clean_invalid_staff(self):
        """スタッフとスタッフ契約の不一致バリデーションテスト"""
        other_staff = Staff.objects.create(
            name_last='鈴木',
            name_first='一郎',
            email='suzuki@example.com'
        )
        approval = StaffTimerecordApproval(
            staff=other_staff,
            staff_contract=self.staff_contract,
            closing_date=date(2026, 1, 31),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31)
        )
        with self.assertRaises(ValidationError):
            approval.full_clean()

    def test_clean_invalid_period(self):
        """無効な期間のバリデーションテスト"""
        approval = StaffTimerecordApproval(
            staff=self.staff,
            staff_contract=self.staff_contract,
            closing_date=date(2026, 1, 31),
            period_start=date(2026, 1, 31),
            period_end=date(2026, 1, 1)  # 終了が開始より前
        )
        with self.assertRaises(ValidationError):
            approval.full_clean()
