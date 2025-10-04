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

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
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

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
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

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
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

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
    def test_haken_contract_includes_office_and_unit(self, mock_generate_pdf):
        """
        Test that haken office and unit are included in the PDF content for a dispatch contract.
        """
        from apps.contract.models import ClientContractHaken
        from apps.client.models import ClientDepartment

        # Create ClientDepartment instances for office and unit
        office_department = ClientDepartment.objects.create(
            client=self.client,
            name='本社事業所'
        )
        unit_department = ClientDepartment.objects.create(
            client=self.client,
            name='開発第一部'
        )

        # Create a dispatch contract
        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Haken Contract with Office/Unit',
            contract_pattern=self.haken_pattern,
            start_date=datetime.date.today(),
            payment_site=self.payment_site,
        )

        # Link the haken info with office and unit
        ClientContractHaken.objects.create(
            client_contract=haken_contract,
            haken_office=office_department,
            haken_unit=unit_department
        )

        # Generate the PDF content
        generate_contract_pdf_content(haken_contract)

        # Check the mock call
        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        items = args[3]

        # Verify office item
        office_item = next((item for item in items if item['title'] == '派遣先事業所の名称及び所在地'), None)
        self.assertIsNotNone(office_item)
        # Since address details are missing, the text should just be the client and office name.
        self.assertEqual(office_item['text'], 'Test Client　本社事業所')

        # Verify unit item
        unit_item = next((item for item in items if item['title'] == '組織単位'), None)
        self.assertIsNotNone(unit_item)
        # Since manager title is missing, the text should just be the unit name.
        self.assertEqual(unit_item['text'], '開発第一部')

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
    def test_haken_contract_formats_office_and_unit_correctly(self, mock_generate_pdf):
        """
        Test that haken office and unit are formatted correctly in the PDF content.
        """
        from apps.contract.models import ClientContractHaken
        from apps.client.models import ClientDepartment

        # Create ClientDepartment instance for office with full details
        office_department = ClientDepartment.objects.create(
            client=self.client,
            name='本社事業所',
            postal_code='1000001',
            address='東京都千代田区千代田1-1',
            phone_number='03-1234-5678'
        )
        # Create ClientDepartment instance for unit with manager title
        unit_department = ClientDepartment.objects.create(
            client=self.client,
            name='開発第一部',
            haken_unit_manager_title='部長'
        )

        # Create a dispatch contract
        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Haken Contract with Formatted Office/Unit',
            contract_pattern=self.haken_pattern,
            start_date=datetime.date.today(),
            payment_site=self.payment_site,
        )

        # Link the haken info with office and unit
        ClientContractHaken.objects.create(
            client_contract=haken_contract,
            haken_office=office_department,
            haken_unit=unit_department
        )

        # Generate the PDF content
        generate_contract_pdf_content(haken_contract)

        # Check the mock call
        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        items = args[3]

        # Verify formatted office item
        office_item = next((item for item in items if item['title'] == '派遣先事業所の名称及び所在地'), None)
        self.assertIsNotNone(office_item)
        expected_office_text = (
            "Test Client　本社事業所\n"
            "〒1000001 東京都千代田区千代田1-1 電話番号：03-1234-5678"
        )
        self.assertEqual(office_item['text'], expected_office_text)

        # Verify formatted unit item
        unit_item = next((item for item in items if item['title'] == '組織単位'), None)
        self.assertIsNotNone(unit_item)
        self.assertEqual(unit_item['text'], '開発第一部　（部長）')
