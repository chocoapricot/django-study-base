import datetime
import io
import fitz  # PyMuPDF
from django.test import TestCase
from unittest.mock import patch

from apps.accounts.models import MyUser
from apps.client.models import Client, ClientDepartment, ClientUser
from apps.company.models import Company, CompanyDepartment as CompanyDept, CompanyUser
from apps.contract.models import ClientContract, ClientContractHaken, StaffContract
from apps.master.models import ContractPattern, BillPayment, ContractTerms
from apps.staff.models import Staff
from apps.contract.utils import generate_contract_pdf_content, generate_clash_day_notification_pdf

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

        # Staff
        self.staff = Staff.objects.create(
            name_last="Test",
            name_first="Staff",
            employee_no="S001",
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
        self.staff_pattern = ContractPattern.objects.create(
            name="Staff Contract Pattern",
            domain='20', # Staff contract
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

        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name="Test Staff Contract",
            contract_pattern=self.staff_pattern,
            start_date=datetime.date(2023, 6, 1),
            end_date=datetime.date(2024, 5, 31),
            contract_number="S-STA-001",
            corporate_number=self.company.corporate_number,
        )

        self.test_user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password'
        )
        self.test_user.name_last = 'Test'
        self.test_user.name_first = 'User'
        self.test_user.save()


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

    def test_generate_clash_day_notification_pdf_content(self):
        """抵触日通知書PDFが正しい内容で生成されることをテストする"""
        # 派遣先事業所と抵触日を設定
        haken_office = ClientDepartment.objects.create(
            client=self.client,
            name="名古屋支社",
            postal_code="450-0002",
            address="名古屋市中村区名駅４丁目２７−１",
            is_haken_office=True,
            haken_jigyosho_teishokubi=datetime.date(2025, 10, 1)
        )
        self.haken_info.haken_office = haken_office
        self.haken_info.save()

        issued_at = datetime.datetime.now(datetime.timezone.utc)
        pdf_content, _, pdf_title = generate_clash_day_notification_pdf(self.dispatch_contract, self.test_user, issued_at)

        self.assertIsNotNone(pdf_content)
        self.assertEqual(pdf_title, "抵触日通知書")

        # PDFからテキストを抽出
        pdf_document = fitz.open(stream=io.BytesIO(pdf_content), filetype="pdf")
        text = ""
        for page in pdf_document:
            text += page.get_text()
        pdf_document.close()

        # PDF内容の検証
        self.assertIn("派遣可能期間の制限（事業所単位の期間制限）に抵触する日の通知", text)
        self.assertIn("（派遣元）", text)
        self.assertIn(f"{self.company.name} 御中", text)
        self.assertIn("（派遣先）", text)
        self.assertIn(self.client.name, text)
        self.assertIn(f"役職 {self.client_user.position}", text)
        self.assertIn(f"氏名 {self.client_user.name}", text)
        self.assertIn("労働者派遣法第２６条第４項に基づき", text)
        self.assertIn("記", text)
        self.assertIn("１．労働者派遣の役務の提供を受ける事業所", text)
        self.assertIn(haken_office.name, text)
        self.assertIn(haken_office.address, text)
        self.assertIn("２．上記事業所の抵触日", text)
        self.assertIn("2025年10月01日", text)
        self.assertIn("３．その他", text)
        self.assertIn("事業所単位の派遣可能期間を延長した場合は", text)

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_contract_term_placeholders_are_replaced(self, mock_generate_pdf):
        """
        Test that {{company_name}} and {{client_name}} placeholders in ContractTerms
        are replaced with actual names in the generated PDF content.
        """
        # Create contract terms with placeholders
        ContractTerms.objects.create(
            contract_pattern=self.normal_pattern,
            display_position=1, # Preamble
            contract_terms="This agreement is between {{company_name}} and {{client_name}}."
        )
        ContractTerms.objects.create(
            contract_pattern=self.normal_pattern,
            display_position=2, # Body
            display_order=1,
            contract_clause="Clause 1",
            contract_terms="The service provider, {{company_name}}, agrees to deliver the services."
        )
        ContractTerms.objects.create(
            contract_pattern=self.normal_pattern,
            display_position=3, # Postamble
            contract_terms="Signed by {{company_name}} and {{client_name}}."
        )

        # Generate the PDF content
        generate_contract_pdf_content(self.normal_contract)

        # Check that the mock was called
        self.assertTrue(mock_generate_pdf.called)

        # Get the arguments passed to the mock
        positional_args = mock_generate_pdf.call_args[0]
        intro_text = positional_args[2]
        items = positional_args[3]
        postamble_text = mock_generate_pdf.call_args[1]['postamble_text']

        # Assertions for placeholder replacement
        expected_company_name = self.company.name
        expected_client_name = self.client.name

        # Check intro_text (preamble)
        self.assertIn(f"This agreement is between {expected_company_name} and {expected_client_name}", intro_text)

        # Check items (body)
        items_dict = {item['title']: item['text'] for item in items}
        self.assertIn("Clause 1", items_dict)
        self.assertEqual(items_dict["Clause 1"], f"The service provider, {expected_company_name}, agrees to deliver the services.")

        # Check postamble_text
        self.assertEqual(postamble_text, f"Signed by {expected_company_name} and {expected_client_name}.")

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_staff_contract_term_placeholders_are_replaced(self, mock_generate_pdf):
        """
        Test that {{company_name}} and {{staff_name}} placeholders in ContractTerms
        are replaced with actual names in the generated PDF content for staff contracts.
        """
        # Create contract terms with placeholders for staff
        ContractTerms.objects.create(
            contract_pattern=self.staff_pattern,
            display_position=1, # Preamble
            contract_terms="This is an agreement between {{company_name}} and our staff member, {{staff_name}}."
        )
        ContractTerms.objects.create(
            contract_pattern=self.staff_pattern,
            display_position=2, # Body
            display_order=1,
            contract_clause="Article 1",
            contract_terms="Our company, {{company_name}}, hires {{staff_name}}."
        )
        ContractTerms.objects.create(
            contract_pattern=self.staff_pattern,
            display_position=3, # Postamble
            contract_terms="Signatures: {{company_name}} and {{staff_name}}."
        )

        # Generate the PDF content
        generate_contract_pdf_content(self.staff_contract)

        # Check that the mock was called
        self.assertTrue(mock_generate_pdf.called)

        # Get the arguments passed to the mock
        positional_args = mock_generate_pdf.call_args[0]
        intro_text = positional_args[2]
        items = positional_args[3]
        postamble_text = mock_generate_pdf.call_args[1]['postamble_text']

        # Assertions for placeholder replacement
        expected_company_name = self.company.name
        expected_staff_name = f"{self.staff.name_last} {self.staff.name_first}"

        # Check intro_text (preamble)
        self.assertIn(f"This is an agreement between {expected_company_name} and our staff member, {expected_staff_name}", intro_text)

        # Check items (body)
        items_dict = {item['title']: item['text'] for item in items}
        self.assertIn("Article 1", items_dict)
        self.assertEqual(items_dict["Article 1"], f"Our company, {expected_company_name}, hires {expected_staff_name}.")

        # Assertions
        self.assertEqual(pdf_title, "抵触日通知書")
        self.assertEqual(intro_text, f"{self.dispatch_contract.client.name} 様")
        self.assertEqual(items_dict["件名"], self.dispatch_contract.contract_name)
        self.assertEqual(items_dict["発行日"], issued_at.strftime('%Y年%m月%d日'))
        self.assertEqual(items_dict["発行者"], self.test_user.get_full_name_japanese())

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_contract_term_placeholders_are_replaced(self, mock_generate_pdf):
        """
        Test that {{company_name}} and {{client_name}} placeholders in ContractTerms
        are replaced with actual names in the generated PDF content.
        """
        # Create contract terms with placeholders
        ContractTerms.objects.create(
            contract_pattern=self.normal_pattern,
            display_position=1, # Preamble
            contract_terms="This agreement is between {{company_name}} and {{client_name}}."
        )
        ContractTerms.objects.create(
            contract_pattern=self.normal_pattern,
            display_position=2, # Body
            display_order=1,
            contract_clause="Clause 1",
            contract_terms="The service provider, {{company_name}}, agrees to deliver the services."
        )
        ContractTerms.objects.create(
            contract_pattern=self.normal_pattern,
            display_position=3, # Postamble
            contract_terms="Signed by {{company_name}} and {{client_name}}."
        )

        # Generate the PDF content
        generate_contract_pdf_content(self.normal_contract)

        # Check that the mock was called
        self.assertTrue(mock_generate_pdf.called)

        # Get the arguments passed to the mock
        positional_args = mock_generate_pdf.call_args[0]
        intro_text = positional_args[2]
        items = positional_args[3]
        postamble_text = mock_generate_pdf.call_args[1]['postamble_text']

        # Assertions for placeholder replacement
        expected_company_name = self.company.name
        expected_client_name = self.client.name

        # Check intro_text (preamble)
        self.assertIn(f"This agreement is between {expected_company_name} and {expected_client_name}", intro_text)

        # Check items (body)
        items_dict = {item['title']: item['text'] for item in items}
        self.assertIn("Clause 1", items_dict)
        self.assertEqual(items_dict["Clause 1"], f"The service provider, {expected_company_name}, agrees to deliver the services.")

        # Check postamble_text
        self.assertEqual(postamble_text, f"Signed by {expected_company_name} and {expected_client_name}.")

    @patch('apps.contract.utils.generate_contract_pdf')
    def test_staff_contract_term_placeholders_are_replaced(self, mock_generate_pdf):
        """
        Test that {{company_name}} and {{staff_name}} placeholders in ContractTerms
        are replaced with actual names in the generated PDF content for staff contracts.
        """
        # Create contract terms with placeholders for staff
        ContractTerms.objects.create(
            contract_pattern=self.staff_pattern,
            display_position=1, # Preamble
            contract_terms="This is an agreement between {{company_name}} and our staff member, {{staff_name}}."
        )
        ContractTerms.objects.create(
            contract_pattern=self.staff_pattern,
            display_position=2, # Body
            display_order=1,
            contract_clause="Article 1",
            contract_terms="Our company, {{company_name}}, hires {{staff_name}}."
        )
        ContractTerms.objects.create(
            contract_pattern=self.staff_pattern,
            display_position=3, # Postamble
            contract_terms="Signatures: {{company_name}} and {{staff_name}}."
        )

        # Generate the PDF content
        generate_contract_pdf_content(self.staff_contract)

        # Check that the mock was called
        self.assertTrue(mock_generate_pdf.called)

        # Get the arguments passed to the mock
        positional_args = mock_generate_pdf.call_args[0]
        intro_text = positional_args[2]
        items = positional_args[3]
        postamble_text = mock_generate_pdf.call_args[1]['postamble_text']

        # Assertions for placeholder replacement
        expected_company_name = self.company.name
        expected_staff_name = f"{self.staff.name_last} {self.staff.name_first}"

        # Check intro_text (preamble)
        self.assertIn(f"This is an agreement between {expected_company_name} and our staff member, {expected_staff_name}", intro_text)

        # Check items (body)
        items_dict = {item['title']: item['text'] for item in items}
        self.assertIn("Article 1", items_dict)
        self.assertEqual(items_dict["Article 1"], f"Our company, {expected_company_name}, hires {expected_staff_name}.")

        # Check postamble_text
        self.assertEqual(postamble_text, f"Signatures: {expected_company_name} and {expected_staff_name}.")

    def test_generate_client_contract_pdf_removes_unwanted_preamble(self):
        """クライアント契約書PDFから不要な前文が削除されていることを確認する"""
        pdf_content, _, _ = generate_contract_pdf_content(self.normal_contract)
        self.assertIsNotNone(pdf_content)

        # PDFからテキストを抽出
        pdf_document = fitz.open(stream=io.BytesIO(pdf_content), filetype="pdf")
        text = ""
        for page in pdf_document:
            text += page.get_text()
        pdf_document.close()

        # 不要な文言が含まれていないことを確認
        unwanted_text = f"{self.normal_contract.client.name}様との間で、以下の通り業務委託契約を締結します。"
        self.assertNotIn(unwanted_text, text)

    def test_generate_staff_contract_pdf_removes_unwanted_preamble(self):
        """スタッフ契約書PDFから不要な前文が削除されていることを確認する"""
        pdf_content, _, _ = generate_contract_pdf_content(self.staff_contract)
        self.assertIsNotNone(pdf_content)

        # PDFからテキストを抽出
        pdf_document = fitz.open(stream=io.BytesIO(pdf_content), filetype="pdf")
        text = ""
        for page in pdf_document:
            text += page.get_text()
        pdf_document.close()

        # 不要な文言が含まれていないことを確認
        full_name = f"{self.staff_contract.staff.name_last} {self.staff_contract.staff.name_first}"
        unwanted_text = f"{full_name}様との間で、以下の通り雇用契約を締結します。"
        self.assertNotIn(unwanted_text, text)
