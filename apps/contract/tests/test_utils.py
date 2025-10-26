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
        # スタッフ用の契約パターンを作成
        self.staff_pattern = ContractPattern.objects.create(
            name='雇用契約',
            domain='20',
            contract_type_code='10'
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

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
    def test_haken_notification_agreement_method(self, mock_generate_pdf):
        """
        Test that the dispatch notification PDF uses the company's dispatch treatment method (agreement).
        """
        from apps.contract.utils import generate_haken_notification_pdf
        from apps.contract.models import ClientContractHaken, StaffContract
        from apps.company.models import Company
        from apps.staff.models import Staff
        from apps.master.models import EmploymentType
        from datetime import datetime

        # Create company with agreement method
        company = Company.objects.create(
            name='Test Company',
            dispatch_treatment_method='agreement'
        )

        # Create employment type
        employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # Create staff
        staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date=datetime(1990, 1, 1).date()
        )

        # Create dispatch contract
        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Dispatch Contract',
            contract_pattern=self.haken_pattern,
            start_date=datetime.today().date(),
            payment_site=self.payment_site,
        )

        # Create haken info
        ClientContractHaken.objects.create(client_contract=haken_contract)

        # Create staff contract
        staff_contract = StaffContract.objects.create(
            staff=staff,
            employment_type=employment_type,
            contract_pattern=self.staff_pattern,
            start_date=datetime.today().date(),
            contract_name='Test Staff Contract'
        )

        # Link staff contract to client contract
        haken_contract.staff_contracts.add(staff_contract)

        # Generate notification PDF
        generate_haken_notification_pdf(haken_contract, self.user, datetime.now())

        # Check the mock call
        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        items = args[3]

        # Find the worker item and check agreement target
        worker_item = next((item for item in items if item['title'] == '派遣労働者1'), None)
        self.assertIsNotNone(worker_item)
        
        # Check the agreement target sub-item
        agreement_item = next((sub_item for sub_item in worker_item['rowspan_items'] if sub_item['title'] == '協定対象'), None)
        self.assertIsNotNone(agreement_item)
        self.assertIn('■　協定対象　（労使協定方式）', agreement_item['text'])
        self.assertIn('□　協定対象でない　（均等・均衡方式）', agreement_item['text'])

    @patch('apps.contract.utils.generate_table_based_contract_pdf')
    def test_haken_notification_equal_balance_method(self, mock_generate_pdf):
        """
        Test that the dispatch notification PDF uses the company's dispatch treatment method (equal_balance).
        """
        from apps.contract.utils import generate_haken_notification_pdf
        from apps.contract.models import ClientContractHaken, StaffContract
        from apps.company.models import Company
        from apps.staff.models import Staff
        from apps.master.models import EmploymentType
        from datetime import datetime

        # Create company with equal_balance method
        company = Company.objects.create(
            name='Test Company',
            dispatch_treatment_method='equal_balance'
        )

        # Create employment type
        employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # Create staff
        staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date=datetime(1990, 1, 1).date()
        )

        # Create dispatch contract
        haken_contract = ClientContract.objects.create(
            client=self.client,
            contract_name='Test Dispatch Contract',
            contract_pattern=self.haken_pattern,
            start_date=datetime.today().date(),
            payment_site=self.payment_site,
        )

        # Create haken info
        ClientContractHaken.objects.create(client_contract=haken_contract)

        # Create staff contract
        staff_contract = StaffContract.objects.create(
            staff=staff,
            employment_type=employment_type,
            contract_pattern=self.staff_pattern,
            start_date=datetime.today().date(),
            contract_name='Test Staff Contract'
        )

        # Link staff contract to client contract
        haken_contract.staff_contracts.add(staff_contract)

        # Generate notification PDF
        generate_haken_notification_pdf(haken_contract, self.user, datetime.now())

        # Check the mock call
        mock_generate_pdf.assert_called_once()
        args, kwargs = mock_generate_pdf.call_args
        items = args[3]

        # Find the worker item and check agreement target
        worker_item = next((item for item in items if item['title'] == '派遣労働者1'), None)
        self.assertIsNotNone(worker_item)
        
        # Check the agreement target sub-item
        agreement_item = next((sub_item for sub_item in worker_item['rowspan_items'] if sub_item['title'] == '協定対象'), None)
        self.assertIsNotNone(agreement_item)
        self.assertIn('□　協定対象　（労使協定方式）', agreement_item['text'])
        self.assertIn('■　協定対象でない　（均等・均衡方式）', agreement_item['text'])
