import os
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.models import Permission
from bs4 import BeautifulSoup

from apps.client.models import Client
from apps.contract.models import ClientContract, ClientContractPrint
from apps.master.models import ContractPattern

User = get_user_model()

class ClientContractStatusUITest(TestCase):
    """クライアント契約のステータスとUIに関するテスト"""

    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(username='testuser', password='password', is_staff=True)
        permissions = Permission.objects.filter(
            codename__in=['change_clientcontract', 'view_clientcontract']
        )
        self.user.user_permissions.add(*permissions)
        self.client.force_login(self.user)

        self.client_obj = Client.objects.create(name='テストクライアント', created_by=self.user, updated_by=self.user)
        self.pattern = ContractPattern.objects.create(name='テストパターン', domain='10')
        self.base_data = {
            'client': self.client_obj,
            'contract_name': 'テスト契約',
            'contract_pattern': self.pattern,
            'start_date': timezone.now().date(),
            'created_by': self.user,
            'updated_by': self.user,
        }

    def _get_soup(self, contract):
        """契約詳細ページのレスポンスからBeautifulSoupオブジェクトを取得"""
        url = reverse('contract:client_contract_detail', kwargs={'pk': contract.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, 'html.parser')

    def test_ui_status_draft(self):
        """「作成中」ステータスのUIテスト"""
        contract = ClientContract.objects.create(**self.base_data, contract_status='1')
        soup = self._get_soup(contract)

        # 承認スイッチは無効
        approval_switch = soup.find('input', {'id': 'approvalSwitch'})
        self.assertIsNotNone(approval_switch.get('disabled'))

        # 見積書発行スイッチは無効
        quotation_switch = soup.find('input', {'id': 'issueQuotationSwitch'})
        self.assertIsNotNone(quotation_switch.get('disabled'))

        # 契約書発行スイッチは無効
        issue_switch = soup.find('input', {'id': 'issueSwitch'})
        self.assertIsNotNone(issue_switch.get('disabled'))

    def test_ui_status_pending(self):
        """「申請中」ステータスのUIテスト"""
        contract = ClientContract.objects.create(**self.base_data, contract_status='5')
        soup = self._get_soup(contract)

        # 承認スイッチは有効で、チェックなし
        approval_switch = soup.find('input', {'id': 'approvalSwitch'})
        self.assertIsNone(approval_switch.get('disabled'))
        self.assertIsNone(approval_switch.get('checked'))

        # 見積書発行スイッチは無効
        quotation_switch = soup.find('input', {'id': 'issueQuotationSwitch'})
        self.assertIsNotNone(quotation_switch.get('disabled'))

        # 契約書発行スイッチは無効
        issue_switch = soup.find('input', {'id': 'issueSwitch'})
        self.assertIsNotNone(issue_switch.get('disabled'))

    def test_ui_status_approved(self):
        """「承認済」ステータスのUIテスト"""
        contract = ClientContract.objects.create(**self.base_data, contract_status='10')
        soup = self._get_soup(contract)

        # 承認スイッチは有効で、チェックあり
        approval_switch = soup.find('input', {'id': 'approvalSwitch'})
        self.assertIsNone(approval_switch.get('disabled'))
        self.assertIsNotNone(approval_switch.get('checked'))

        # 見積書発行スイッチは有効
        quotation_switch = soup.find('input', {'id': 'issueQuotationSwitch'})
        self.assertIsNone(quotation_switch.get('disabled'))

        # 契約書発行スイッチは有効
        issue_switch = soup.find('input', {'id': 'issueSwitch'})
        self.assertIsNone(issue_switch.get('disabled'))

    def test_ui_status_issued(self):
        """「発行済」ステータスのUIテスト"""
        contract = ClientContract.objects.create(**self.base_data, contract_status='20')
        soup = self._get_soup(contract)

        # 承認スイッチは有効で、チェックあり（承認解除のため）
        approval_switch = soup.find('input', {'id': 'approvalSwitch'})
        self.assertIsNone(approval_switch.get('disabled'))
        self.assertIsNotNone(approval_switch.get('checked'))

        # 契約書発行スイッチはチェックありで無効
        issue_switch = soup.find('input', {'id': 'issueSwitch'})
        self.assertIsNotNone(issue_switch.get('disabled'))
        self.assertIsNotNone(issue_switch.get('checked'))

    def test_ui_quotation_issued(self):
        """見積書発行済の場合のUIテスト"""
        contract = ClientContract.objects.create(**self.base_data, contract_status='10')
        ClientContractPrint.objects.create(client_contract=contract, print_type='20')
        soup = self._get_soup(contract)

        # 見積書発行スイッチはチェックありで無効
        quotation_switch = soup.find('input', {'id': 'issueQuotationSwitch'})
        self.assertIsNotNone(quotation_switch.get('disabled'))
        self.assertIsNotNone(quotation_switch.get('checked'))
