from django.test import TestCase

from apps.contract.utils import get_contract_pdf_title
from unittest.mock import patch
from apps.contract.utils import generate_and_save_contract_pdf
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

        generate_and_save_contract_pdf(haken_contract, self.user)

        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        self.assertEqual(args[1], "労働者派遣個別契約書")

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_generate_ukeoi_contract_pdf_title(self, mock_generate_pdf):
        """
        Test that the title for a 'ukeoi' (contracting) contract is '業務委託契約書'.
        """
        ukeoi_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Ukeoi Contract',
            contract_pattern=self.ukeoi_pattern,
            start_date=datetime.date.today(),
            payment_site=self.payment_site,
        )

        generate_and_save_contract_pdf(ukeoi_contract, self.user)

        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        self.assertEqual(args[1], "業務委託契約書")

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_contract_with_no_pattern_pdf_title(self, mock_generate_pdf):
        """
        Test that a contract with no pattern defaults to '業務委託契約書'.
        """
        no_pattern_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test No Pattern Contract',
            contract_pattern=None,
            start_date=datetime.date.today(),
            payment_site=self.payment_site,
        )

        generate_and_save_contract_pdf(no_pattern_contract, self.user)

        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        self.assertEqual(args[1], "業務委託契約書")
