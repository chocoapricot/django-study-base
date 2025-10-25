import unittest
from django.test import TestCase
from unittest.mock import patch
from apps.contract.utils import generate_haken_notification_pdf
from apps.contract.models import ClientContract, ClientContractHaken, StaffContract
from apps.master.models import ContractPattern, BillPayment, EmploymentType
from apps.client.models import Client
from apps.company.models import Company
from apps.staff.models import Staff
from apps.accounts.models import MyUser
from datetime import datetime, date


class DispatchTreatmentMethodTest(TestCase):
    """派遣待遇決定方式のテスト"""

    def setUp(self):
        """テスト用データのセットアップ"""
        self.user = MyUser.objects.create_user('testuser', 'test@example.com', 'password')
        self.client = Client.objects.create(name='Test Client')
        self.payment_site = BillPayment.objects.create(
            name='月末締め翌月末払い',
            closing_day=31,
            invoice_months_after=1,
            invoice_day=10,
            payment_months_after=1,
            payment_day=31,
        )
        self.haken_pattern = ContractPattern.objects.create(
            name='派遣契約',
            domain='10',
            contract_type_code='20'
        )
        self.staff_pattern = ContractPattern.objects.create(
            name='スタッフ契約',
            domain='20',
            contract_type_code='1'
        )
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
    def test_haken_notification_agreement_method(self, mock_generate_pdf):
        """労使協定方式の場合のテスト"""
        # 労使協定方式の会社を作成
        company = Company.objects.create(
            name='Test Company',
            dispatch_treatment_method='agreement'
        )

        # スタッフを作成
        staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date=date(1990, 1, 1)
        )

        # 派遣契約を作成
        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Dispatch Contract',
            contract_pattern=self.haken_pattern,
            start_date=date.today(),
            payment_site=self.payment_site,
        )

        # 派遣情報を作成
        ClientContractHaken.objects.create(client_contract=haken_contract)

        # スタッフ契約を作成
        staff_contract = StaffContract.objects.create(
            staff=staff,
            employment_type=self.employment_type,
            contract_pattern=self.staff_pattern,
            start_date=date.today(),
            contract_name='Test Staff Contract'
        )

        # スタッフ契約をクライアント契約に関連付け
        haken_contract.staff_contracts.add(staff_contract)

        # 派遣通知書PDFを生成
        generate_haken_notification_pdf(haken_contract, self.user, datetime.now())

        # モックの呼び出しを確認
        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        items = args[3]

        # 派遣労働者の項目を検索
        worker_item = next((item for item in items if item['title'] == '派遣労働者1'), None)
        self.assertIsNotNone(worker_item)
        
        # 協定対象の項目を確認
        agreement_item = next((sub_item for sub_item in worker_item['rowspan_items'] if sub_item['title'] == '協定対象'), None)
        self.assertIsNotNone(agreement_item)
        self.assertIn('■　協定対象　（労使協定方式）', agreement_item['text'])
        self.assertIn('□　協定対象でない　（均等・均衡方式）', agreement_item['text'])

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
    def test_haken_notification_equal_balance_method(self, mock_generate_pdf):
        """派遣先均等・均衡方式の場合のテスト"""
        # 派遣先均等・均衡方式の会社を作成
        company = Company.objects.create(
            name='Test Company',
            dispatch_treatment_method='equal_balance'
        )

        # スタッフを作成
        staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date=date(1990, 1, 1)
        )

        # 派遣契約を作成
        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Dispatch Contract',
            contract_pattern=self.haken_pattern,
            start_date=date.today(),
            payment_site=self.payment_site,
        )

        # 派遣情報を作成
        ClientContractHaken.objects.create(client_contract=haken_contract)

        # スタッフ契約を作成
        staff_contract = StaffContract.objects.create(
            staff=staff,
            employment_type=self.employment_type,
            contract_pattern=self.staff_pattern,
            start_date=date.today(),
            contract_name='Test Staff Contract'
        )

        # スタッフ契約をクライアント契約に関連付け
        haken_contract.staff_contracts.add(staff_contract)

        # 派遣通知書PDFを生成
        generate_haken_notification_pdf(haken_contract, self.user, datetime.now())

        # モックの呼び出しを確認
        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        items = args[3]

        # 派遣労働者の項目を検索
        worker_item = next((item for item in items if item['title'] == '派遣労働者1'), None)
        self.assertIsNotNone(worker_item)
        
        # 協定対象の項目を確認
        agreement_item = next((sub_item for sub_item in worker_item['rowspan_items'] if sub_item['title'] == '協定対象'), None)
        self.assertIsNotNone(agreement_item)
        self.assertIn('□　協定対象　（労使協定方式）', agreement_item['text'])
        self.assertIn('■　協定対象でない　（均等・均衡方式）', agreement_item['text'])