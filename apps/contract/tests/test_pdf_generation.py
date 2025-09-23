from django.test import TestCase
from unittest.mock import patch

from apps.client.models import Client, ClientDepartment, ClientUser
from apps.company.models import Company, CompanyDepartment as CompanyDept, CompanyUser
from apps.contract.models import ClientContract, ClientContractHaken
from apps.master.models import ContractPattern, BillPayment
from apps.contract.utils import generate_contract_pdf_content
import datetime

class ContractPdfGenerationTest(TestCase):

    def setUp(self):
        """Set up test data for PDF generation tests."""
        # Company
        self.company = Company.objects.create(name="Test Company", corporate_number="1234567890123")
        self.company_dept = CompanyDept.objects.create(name="Test Div", department_code="D001", corporate_number=self.company.corporate_number)
        self.company_user = CompanyUser.objects.create(
            name_last="Hakenmoto", name_first="Tantou",
            position="Manager",
            phone_number="03-1111-2222",
            department_code="D001",
            corporate_number=self.company.corporate_number,
        )

        # Client
        self.client = Client.objects.create(name="Test Client", corporate_number="9876543210987")
        self.client_dept = ClientDepartment.objects.create(client=self.client, name="Client Div")
        self.client_user = ClientUser.objects.create(
            client=self.client,
            department=self.client_dept,
            name_last="Hakensaki", name_first="Tantou",
            position="Leader",
            phone_number="03-3333-4444"
        )

        # Master data
        self.payment_site = BillPayment.objects.create(
            name="月末締め翌月末払い",
            closing_day=31,
            invoice_months_after=0,
            invoice_day=10,
            payment_months_after=1,
            payment_day=31,
        )
        self.dispatch_pattern = ContractPattern.objects.create(
            name="Dispatch Contract Pattern",
            domain='10', # Client contract
            contract_type_code='20' # Dispatch
        )
        self.normal_pattern = ContractPattern.objects.create(
            name="Normal Contract Pattern",
            domain='10', # Client contract
            contract_type_code='10' # Normal
        )

        # Contracts
        self.dispatch_contract = ClientContract.objects.create(
            client=self.client,
            contract_name="Test Dispatch Contract",
            contract_pattern=self.dispatch_pattern,
            start_date=datetime.date(2023, 4, 1),
            end_date=datetime.date(2024, 3, 31),
            payment_site=self.payment_site,
            contract_number="C-DIS-001"
        )
        self.haken_info = ClientContractHaken.objects.create(
            client_contract=self.dispatch_contract,
            commander=self.client_user,
            complaint_officer_client=self.client_user,
            responsible_person_client=self.client_user,
            complaint_officer_company=self.company_user,
            responsible_person_company=self.company_user,
            limit_by_agreement='1', # 限定する
            limit_indefinite_or_senior='0' # 限定しない
        )

        self.normal_contract = ClientContract.objects.create(
            client=self.client,
            contract_name="Test Normal Contract",
            contract_pattern=self.normal_pattern,
            start_date=datetime.date(2023, 5, 1),
            end_date=datetime.date(2024, 4, 30),
            payment_site=self.payment_site,
            contract_number="C-NOR-001"
        )


    @patch('apps.contract.utils.generate_contract_pdf')
    def test_dispatch_contract_pdf_includes_haken_info(self, mock_generate_pdf):
        """Test that PDF for dispatch contract includes haken specific information."""
        generate_contract_pdf_content(self.dispatch_contract)

        # Check that the mock was called
        self.assertTrue(mock_generate_pdf.called)

        # Get the arguments passed to the mock
        positional_args = mock_generate_pdf.call_args[0]
        items = positional_args[3]

        # Convert items to a dict for easier lookup
        items_dict = {item['title']: item['text'] for item in items}

        # Assertions
        self.assertIn("派遣先指揮命令者", items_dict)
        self.assertEqual(items_dict["派遣先指揮命令者"], "Client Div　Leader　Hakensaki Tantou")

        self.assertIn("派遣先苦情申出先", items_dict)
        self.assertEqual(items_dict["派遣先苦情申出先"], "Client Div　Leader　Hakensaki Tantou 電話番号：03-3333-4444")

        self.assertIn("派遣元責任者", items_dict)
        self.assertEqual(items_dict["派遣元責任者"], "Test Div　Manager　Hakenmoto Tantou 電話番号：03-1111-2222")

        self.assertIn("協定対象派遣労働者に限定するか否かの別", items_dict)
        self.assertEqual(items_dict["協定対象派遣労働者に限定するか否かの別"], "限定する")

        self.assertIn("無期雇用派遣労働者又は60歳以上の者に限定するか否かの別", items_dict)
        self.assertEqual(items_dict["無期雇用派遣労働者又は60歳以上の者に限定するか否かの別"], "限定しない")


    @patch('apps.contract.utils.generate_contract_pdf')
    def test_normal_contract_pdf_does_not_include_haken_info(self, mock_generate_pdf):
        """Test that PDF for normal contract does not include haken specific information."""
        generate_contract_pdf_content(self.normal_contract)

        self.assertTrue(mock_generate_pdf.called)
        positional_args = mock_generate_pdf.call_args[0]
        items = positional_args[3]
        items_dict = {item['title']: item['text'] for item in items}

        # Assert that haken-specific fields are NOT present
        self.assertNotIn("派遣先指揮命令者", items_dict)
        self.assertNotIn("派遣元責任者", items_dict)
        self.assertNotIn("協定対象派遣労働者に限定するか否かの別", items_dict)
