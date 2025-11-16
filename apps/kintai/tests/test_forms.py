from django.test import TestCase
from datetime import date, time
from apps.kintai.forms import StaffTimesheetForm, StaffTimecardForm
from apps.kintai.models import StaffTimesheet
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern
from apps.common.constants import Constants


class StaffTimesheetFormTest(TestCase):
    """月次勤怠フォームのテスト"""

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

    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'staff_contract': self.staff_contract.pk,
            'target_month': '2024-11',
            'memo': 'テストメモ'
        }
        form = StaffTimesheetForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_month_format(self):
        """無効な年月フォーマットのテスト"""
        form_data = {
            'staff_contract': self.staff_contract.pk,
            'target_month': '2024-13',  # 無効なフォーマット
        }
        form = StaffTimesheetForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('target_month', form.errors)

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = StaffTimesheetForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('staff_contract', form.errors)
        self.assertIn('target_month', form.errors)


class StaffTimecardFormTest(TestCase):
    """日次勤怠フォームのテスト"""

    def test_valid_form_work_day(self):
        """有効な出勤日フォームデータのテスト"""
        form_data = {
            'work_date': '2024-11-01',
            'work_type': '10',  # 出勤
            'start_time': '09:00',
            'end_time': '18:00',
            'break_minutes': 60,
            'paid_leave_days': 0,
        }
        form = StaffTimecardForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_form_paid_leave(self):
        """有効な有給休暇フォームデータのテスト"""
        form_data = {
            'work_date': '2024-11-01',
            'work_type': '40',  # 有給休暇
            'break_minutes': 0,
            'paid_leave_days': 1.0,
        }
        form = StaffTimecardForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = StaffTimecardForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('work_date', form.errors)
        self.assertIn('work_type', form.errors)
