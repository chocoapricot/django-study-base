from django.test import TestCase
from apps.company.models import Company
from apps.client.models import Client
from apps.staff.models import Staff
from apps.contract.forms import ClientContractForm, StaffContractForm


from apps.master.models import ContractPattern


class ContractCorporateNumberTest(TestCase):
    def setUp(self):
        """テストデータの準備"""
        self.company = Company.objects.create(
            name="テスト株式会社",
            corporate_number="1112223334445"
        )
        self.client = Client.objects.create(name="テストクライアント")
        self.staff = Staff.objects.create(name_last="山田", name_first="太郎")
        self.client_pattern = ContractPattern.objects.create(name="クライアント契約", domain="10")
        self.staff_pattern = ContractPattern.objects.create(name="スタッフ契約", domain="1")

    def test_client_contract_sets_corporate_number(self):
        """ClientContract作成時に法人番号が自動設定されることを確認"""
        form_data = {
            'client': self.client.pk,
            'contract_name': 'テスト契約',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'contract_pattern': self.client_pattern.pk,
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
            'contract_pattern': self.staff_pattern.pk,
        }
        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        contract = form.save()
        self.assertEqual(contract.corporate_number, self.company.corporate_number)
