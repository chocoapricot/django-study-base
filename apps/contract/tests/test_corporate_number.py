from django.test import TestCase
from apps.company.models import Company
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import ContractPattern, Dropdowns
from apps.contract.forms import ClientContractForm, StaffContractForm
import datetime


class ContractCorporateNumberTest(TestCase):
    def setUp(self):
        """テストデータの準備"""
        self.company = Company.objects.create(
            name="テスト株式会社",
            corporate_number="1112223334445"
        )
        self.client = Client.objects.create(
            name="テストクライアント",
            corporate_number="5000000000001",
            basic_contract_date=datetime.date(2024, 1, 1)
        )
        self.staff = Staff.objects.create(
            name_last="山田",
            name_first="太郎",
            hire_date=datetime.date(2024, 1, 1)
        )
        self.bill_unit = Dropdowns.objects.create(category='bill_unit', value='10', name='月額', active=True)
        self.pay_unit = Dropdowns.objects.create(category='pay_unit', value='10', name='月給', active=True)
        self.staff_pattern = ContractPattern.objects.create(name='Staff Test Pattern', domain='1', is_active=True)
        
        # 就業時間パターン
        from apps.master.models import WorkTimePattern, OvertimePattern
        self.worktime_pattern = WorkTimePattern.objects.create(name='標準勤務', is_active=True)
        
        # 時間外算出パターン
        self.overtime_pattern = OvertimePattern.objects.create(
            name='標準時間外算出',
            calculation_type='premium',
            is_active=True
        )

    def test_client_contract_sets_corporate_number(self):
        """ClientContract作成時に法人番号が自動設定されることを確認"""
        contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10', contract_type_code='10')
        form_data = {
            'client': self.client.pk,
            'contract_name': 'テスト契約',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'contract_pattern': contract_pattern.pk,
            'client_contract_type_code': '10',
            'bill_unit': self.bill_unit.value,
            'worktime_pattern': self.worktime_pattern.pk,
        }
        form = ClientContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        contract = form.save()
        self.assertEqual(contract.corporate_number, self.company.corporate_number)

    def test_staff_contract_sets_corporate_number(self):
        """StaffContract作成時に法人番号が自動設定されることを確認"""
        form_data = {
            'staff': self.staff.pk,
            'contract_name': 'テスト雇用契約',
            'start_date': '2025-04-01',
            'end_date': '2025-12-31',
            'pay_unit': self.pay_unit.value,
            'contract_pattern': self.staff_pattern.pk,
            'worktime_pattern': self.worktime_pattern.pk,
            'overtime_pattern': self.overtime_pattern.pk,
        }
        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        contract = form.save()
        self.assertEqual(contract.corporate_number, self.company.corporate_number)
