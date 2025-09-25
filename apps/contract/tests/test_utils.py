import unittest
from django.test import TestCase

from unittest.mock import patch
from apps.contract.utils import generate_contract_pdf_content
from apps.contract.models import ClientContract
from apps.master.models import ContractPattern, BillPayment
from apps.client.models import Client
from apps.accounts.models import MyUser
import datetime

class ContractUtilsTest(TestCase):
    def setUp(self):
        """
        Set up the necessary objects for testing.
        This includes creating a user, a client, and contract patterns.
        """
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
        self.ukeoi_pattern = ContractPattern.objects.create(
            name='請負契約',
            domain='10',
            contract_type_code='1'
        )

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_generate_haken_contract_pdf_title(self, mock_generate_pdf):
        """
        Test that the title for a 'haken' (dispatch) contract is '労働者派遣個別契約書'.
        """
        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Haken Contract',
            contract_pattern=self.haken_pattern,
            start_date=datetime.date.today(),
            payment_site=self.payment_site,
        )

        generate_contract_pdf_content(haken_contract)

        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        self.assertEqual(args[1], "労働者派遣個別契約書")

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_generate_ukeoi_contract_pdf_title(self, mock_generate_pdf):
        """
        Test that the title for a 'ukeoi' (contracting) contract is '業務委託個別契約書'.
        """
        ukeoi_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Ukeoi Contract',
            contract_pattern=self.ukeoi_pattern,
            start_date=datetime.date.today(),
            payment_site=self.payment_site,
        )

        generate_contract_pdf_content(ukeoi_contract)

        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        self.assertEqual(args[1], "業務委託個別契約書")

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_haken_contract_includes_permit_number(self, mock_generate_pdf):
        """
        Test that the haken permit number is included in the PDF content for a dispatch contract.
        """
        from apps.company.models import Company
        from apps.contract.models import ClientContractHaken

        Company.objects.create(name='Test Company', haken_permit_number='派13-123456')

        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Haken Contract',
            contract_pattern=self.haken_pattern,
            start_date=datetime.date.today(),
            payment_site=self.payment_site,
        )

        ClientContractHaken.objects.create(client_contract=haken_contract)

        generate_contract_pdf_content(haken_contract)

        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        items = args[3]

        permit_number_item = next((item for item in items if item['title'] == '許可番号'), None)
        self.assertIsNotNone(permit_number_item)
        self.assertEqual(permit_number_item['text'], '派13-123456')
