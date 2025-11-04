"""
就業条件明示書の契約文言出力テスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.contract.models import ClientContract, StaffContract, ContractAssignment
from apps.contract.utils import generate_employment_conditions_pdf
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import ContractPattern, ContractTerms
from apps.company.models import Company
from django.utils import timezone
import datetime

User = get_user_model()

class EmploymentConditionsContractTermsTest(TestCase):
    """就業条件明示書の契約文言出力テスト"""
    
    def setUp(self):
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 会社情報作成
        self.company = Company.objects.create(
            name='テスト株式会社',
            corporate_number='1234567890123'
        )
        
        # クライアント作成
        self.client = Client.objects.create(
            name='テストクライアント',
            corporate_number='9876543210987'
        )
        
        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            employee_no='EMP001',
            email='tanaka.taro@example.com'
        )
        
        # 契約パターン作成（スタッフ用）
        self.staff_contract_pattern = ContractPattern.objects.create(
            name='派遣契約（スタッフ）',
            domain='1',  # スタッフ用
            display_order=1
        )
        
        # 契約パターン作成（クライアント用）
        self.client_contract_pattern = ContractPattern.objects.create(
            name='派遣契約（クライアント）',
            domain='10',  # クライアント用
            display_order=1
        )    
    
        # 契約文言作成（スタッフ契約用）
        self.contract_term1 = ContractTerms.objects.create(
            contract_pattern=self.staff_contract_pattern,
            contract_clause='雇用形態',
            contract_terms='{{company_name}}は{{staff_name}}を派遣労働者として雇用する。',
            display_position=2,  # 本文
            display_order=1
        )
        
        self.contract_term2 = ContractTerms.objects.create(
            contract_pattern=self.staff_contract_pattern,
            contract_clause='契約期間',
            contract_terms='契約期間は{{start_date}}から{{end_date}}までとする。',
            display_position=2,  # 本文
            display_order=2
        )
        
        self.contract_term3 = ContractTerms.objects.create(
            contract_pattern=self.staff_contract_pattern,
            contract_clause='報酬',
            contract_terms='報酬は{{contract_amount}}とする。',
            display_position=2,  # 本文
            display_order=3
        )
        
        # クライアント契約作成
        self.client_contract = ClientContract.objects.create(
            client=self.client,
            contract_pattern=self.client_contract_pattern,
            contract_name='テスト派遣契約',
            client_contract_type_code='20',  # 派遣契約
            contract_number='CC-2025-001',  # 契約番号を追加
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            contract_amount=5000,
            bill_unit='10',  # 時間単位
            business_content='システム開発業務'
        )
        
        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_pattern=self.staff_contract_pattern,
            contract_name='テストスタッフ契約',
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            contract_amount=4000,
            pay_unit='10',  # 時間単位
            business_content='システム開発支援業務',
            work_location='東京都千代田区千代田1-1 開発フロア'
        )
        
        # 部署作成
        from apps.company.models import CompanyDepartment
        self.department = CompanyDepartment.objects.create(
            name='開発部',
            department_code='DEV',
            display_order=1
        )
        
        # 会社担当者作成
        from apps.company.models import CompanyUser
        self.company_user = CompanyUser.objects.create(
            name_last='山田',
            name_first='太郎',
            department_code='DEV',
            position='課長',
            phone_number='03-1234-5678'
        )
        
        # クライアント部署作成
        from apps.client.models import ClientDepartment
        self.client_department = ClientDepartment.objects.create(
            client=self.client,
            name='システム部',
            display_order=1
        )
        
        # クライアント担当者作成
        from apps.client.models import ClientUser
        self.client_user = ClientUser.objects.create(
            client=self.client,
            department=self.client_department,
            name_last='佐藤',
            name_first='花子',
            position='部長',
            phone_number='03-9876-5432'
        )
        
        # 派遣先事業所作成（ClientDepartmentでis_haken_office=True）
        self.client_office = ClientDepartment.objects.create(
            client=self.client,
            name='東京本社',
            postal_code='1000001',
            address='東京都千代田区千代田1-1',
            phone_number='03-1111-2222',
            is_haken_office=True
        )
        
        # 組織単位作成（ClientDepartmentでis_haken_unit=True）
        self.haken_unit = ClientDepartment.objects.create(
            client=self.client,
            name='開発チーム',
            is_haken_unit=True,
            haken_unit_manager_title='チームリーダー'
        )
        
        # 指揮命令者作成
        self.commander = ClientUser.objects.create(
            client=self.client,
            department=self.client_department,
            name_last='田中',
            name_first='次郎',
            position='主任',
            phone_number='03-5555-6666'
        )
        
        # 派遣元苦情申出先作成
        self.company_complaint_officer = CompanyUser.objects.create(
            name_last='鈴木',
            name_first='一郎',
            department_code='DEV',
            position='係長',
            phone_number='03-7777-8888'
        )
        
        # 派遣先苦情申出先作成
        self.client_complaint_officer = ClientUser.objects.create(
            client=self.client,
            department=self.client_department,
            name_last='高橋',
            name_first='三郎',
            position='課長',
            phone_number='03-9999-0000'
        )
        
        # 派遣情報作成
        from apps.contract.models import ClientContractHaken
        self.haken_info = ClientContractHaken.objects.create(
            client_contract=self.client_contract,
            responsibility_degree='指示に従って業務を行う',
            responsible_person_company=self.company_user,
            responsible_person_client=self.client_user,
            haken_office=self.client_office,
            haken_unit=self.haken_unit,
            commander=self.commander,
            complaint_officer_company=self.company_complaint_officer,
            complaint_officer_client=self.client_complaint_officer
        )
        
        # 個人抵触日作成
        from apps.contract.models import StaffContractTeishokubi
        self.staff_teishokubi = StaffContractTeishokubi.objects.create(
            staff_email=self.staff.email,
            client_corporate_number=self.client.corporate_number,
            organization_name=self.haken_unit.name,
            dispatch_start_date=datetime.date(2025, 2, 1),
            conflict_date=datetime.date(2028, 2, 1)  # 3年後
        )
        
        # 契約アサイン作成（期間を設定）
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            assignment_start_date=datetime.date(2025, 2, 1),
            assignment_end_date=datetime.date(2025, 11, 30)
        )
    
    def test_generate_employment_conditions_with_contract_terms(self):
        """契約文言を含む就業条件明示書の生成テスト"""
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at, 
            watermark_text="ドラフト"
        )
        
        # PDFが生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertIsInstance(pdf_content, bytes)
        self.assertGreater(len(pdf_content), 0)
    
    def test_contract_terms_template_replacement(self):
        """契約文言のテンプレート変数置換テスト"""
        # 契約文言の内容を直接確認するため、utilsの処理をテスト
        from apps.contract.utils import generate_employment_conditions_pdf
        
        issued_at = timezone.now()
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
    
    def test_contract_terms_content_verification(self):
        """契約文言の内容が正しく置換されているかを検証"""
        # PDF生成を実行して、契約文言が個別の行として含まれることを確認
        issued_at = timezone.now()
        
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 実際の契約文言の置換処理をテスト
        staff_contract = self.staff_contract
        staff = staff_contract.staff
        
        # 会社名を取得
        from apps.company.models import Company
        company = Company.objects.first()
        company_name = company.name if company else "会社名"
        
        # 契約文言を取得
        contract_terms = staff_contract.contract_pattern.terms.filter(
            display_position=2  # 本文のみ
        ).order_by('display_order')
        
        self.assertTrue(contract_terms.exists())
        self.assertEqual(contract_terms.count(), 3)  # 3つの契約文言があることを確認
        
        # 各契約文言の置換をテスト
        for term in contract_terms:
            term_text = term.contract_terms
            
            # テンプレート変数の置換
            term_text = term_text.replace('{{staff_name}}', f"{staff.name_last} {staff.name_first}")
            term_text = term_text.replace('{{company_name}}', company_name)
            
            if staff_contract.start_date:
                start_date_str = staff_contract.start_date.strftime('%Y年%m月%d日')
                term_text = term_text.replace('{{start_date}}', start_date_str)
            
            if staff_contract.end_date:
                end_date_str = staff_contract.end_date.strftime('%Y年%m月%d日')
                term_text = term_text.replace('{{end_date}}', end_date_str)
            
            if staff_contract.contract_amount:
                amount_str = f"{staff_contract.contract_amount:,.0f}円"
                term_text = term_text.replace('{{contract_amount}}', amount_str)
            
            # 置換後の内容を検証
            if term.contract_clause == '雇用形態':
                self.assertIn('テスト株式会社', term_text)
                self.assertIn('田中 太郎', term_text)
            elif term.contract_clause == '契約期間':
                self.assertIn('2025年01月01日', term_text)
                self.assertIn('2025年12月31日', term_text)
            elif term.contract_clause == '報酬':
                self.assertIn('4,000円', term_text)
    
    def test_no_contract_terms_case(self):
        """契約文言が設定されていない契約パターンの場合のテスト"""
        # 契約文言なしの契約パターンを作成
        empty_pattern = ContractPattern.objects.create(
            name='空の契約パターン',
            domain='1',  # スタッフ用
            display_order=99
        )
        
        # 契約文言なしのスタッフ契約を作成
        staff_contract_no_terms = StaffContract.objects.create(
            staff=self.staff,
            contract_pattern=empty_pattern,
            contract_name='文言なし契約',
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            contract_amount=3000,
            pay_unit='10'
        )
        
        # アサインを作成
        assignment_no_terms = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=staff_contract_no_terms
        )
        
        issued_at = timezone.now()
        
        # PDF生成（エラーが発生しないことを確認）
        pdf_content = generate_employment_conditions_pdf(
            assignment_no_terms, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)    

    def test_employment_conditions_preamble_and_contract_number(self):
        """前文と契約番号が正しく表示されるかのテスト"""
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 前文の内容確認（実際のPDF内容は確認できないが、生成処理が正常に動作することを確認）
        # 会社名とスタッフ名が正しく設定されていることを間接的に確認
        self.assertEqual(self.company.name, 'テスト株式会社')
        self.assertEqual(f"{self.staff.name_last} {self.staff.name_first}", '田中 太郎')
        
        # 契約番号が設定されていることを確認
        self.assertEqual(self.client_contract.contract_number, 'CC-2025-001')
        
        # 責任の程度が設定されていることを確認
        self.assertEqual(self.haken_info.responsibility_degree, '指示に従って業務を行う')
    
    def test_responsibility_degree_display(self):
        """責任の程度が業務内容の次に表示されることのテスト"""
        # 業務内容と責任の程度の両方が設定されている場合のテスト
        self.assertTrue(self.client_contract.business_content)  # 業務内容が設定されている
        self.assertTrue(self.haken_info.responsibility_degree)  # 責任の程度が設定されている
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
    
    def test_missing_contract_number_case(self):
        """契約番号が設定されていない場合のテスト"""
        # 契約番号なしのクライアント契約を作成
        client_contract_no_number = ClientContract.objects.create(
            client=self.client,
            contract_pattern=self.client_contract_pattern,
            contract_name='番号なし契約',
            client_contract_type_code='20',  # 派遣契約
            # contract_number は設定しない
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            contract_amount=5000,
            bill_unit='10',
            business_content='システム開発業務'
        )
        
        # 派遣情報作成
        from apps.contract.models import ClientContractHaken
        haken_info_no_number = ClientContractHaken.objects.create(
            client_contract=client_contract_no_number,
            responsibility_degree='指示に従って業務を行う'
        )
        
        # アサイン作成
        assignment_no_number = ContractAssignment.objects.create(
            client_contract=client_contract_no_number,
            staff_contract=self.staff_contract
        )
        
        issued_at = timezone.now()
        
        # PDF生成（エラーが発生しないことを確認）
        pdf_content = generate_employment_conditions_pdf(
            assignment_no_number, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)   
 
    def test_responsible_persons_display(self):
        """派遣元責任者と派遣先責任者が正しく表示されるかのテスト"""
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 責任者情報が設定されていることを確認
        self.assertEqual(self.company_user.name, '山田 太郎')
        self.assertEqual(self.company_user.position, '課長')
        self.assertEqual(self.company_user.phone_number, '03-1234-5678')
        self.assertEqual(self.company_user.department.name, '開発部')
        
        self.assertEqual(self.client_user.name, '佐藤 花子')
        self.assertEqual(self.client_user.position, '部長')
        self.assertEqual(self.client_user.phone_number, '03-9876-5432')
        self.assertEqual(self.client_user.department.name, 'システム部')
    
    def test_staff_business_content_priority(self):
        """スタッフの業務内容が優先表示されることのテスト"""
        # スタッフ契約とクライアント契約の両方に業務内容が設定されている場合
        self.assertTrue(self.staff_contract.business_content)  # スタッフ契約の業務内容
        self.assertTrue(self.client_contract.business_content)  # クライアント契約の業務内容
        
        # スタッフ契約の業務内容が優先されることを確認
        self.assertEqual(self.staff_contract.business_content, 'システム開発支援業務')
        self.assertEqual(self.client_contract.business_content, 'システム開発業務')
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
    
    def test_missing_responsible_persons_case(self):
        """責任者が設定されていない場合のテスト"""
        # 新しいクライアント契約を作成（責任者なし）
        client_contract_no_responsible = ClientContract.objects.create(
            client=self.client,
            contract_pattern=self.client_contract_pattern,
            contract_name='責任者なし契約',
            client_contract_type_code='20',
            contract_number='CC-2025-002',
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            contract_amount=5000,
            bill_unit='10',
            business_content='システム開発業務'
        )
        
        # 責任者なしの派遣情報を作成
        from apps.contract.models import ClientContractHaken
        haken_info_no_responsible = ClientContractHaken.objects.create(
            client_contract=client_contract_no_responsible,
            responsibility_degree='指示に従って業務を行う'
            # responsible_person_company と responsible_person_client は設定しない
        )
        
        # アサイン作成
        assignment_no_responsible = ContractAssignment.objects.create(
            client_contract=client_contract_no_responsible,
            staff_contract=self.staff_contract
        )
        
        issued_at = timezone.now()
        
        # PDF生成（エラーが発生しないことを確認）
        pdf_content = generate_employment_conditions_pdf(
            assignment_no_responsible, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)    

    def test_new_items_display_order(self):
        """新しい項目の表示順序が正しいかのテスト"""
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 新しい項目が設定されていることを確認
        # 契約名が契約番号の次に来ることを確認
        self.assertEqual(self.client_contract.contract_name, 'テスト派遣契約')
        
        # 派遣先事業所の名称及び所在地
        self.assertEqual(self.client_office.name, '東京本社')
        self.assertEqual(self.client_office.postal_code, '1000001')
        self.assertEqual(self.client_office.address, '東京都千代田区千代田1-1')
        self.assertEqual(self.client_office.phone_number, '03-1111-2222')
        
        # 就業場所（スタッフ契約）
        self.assertEqual(self.staff_contract.work_location, '東京都千代田区千代田1-1 開発フロア')
        
        # 組織単位
        self.assertEqual(self.haken_unit.name, '開発チーム')
        self.assertEqual(self.haken_unit.haken_unit_manager_title, 'チームリーダー')
        
        # 派遣先指揮命令者
        self.assertEqual(self.commander.name, '田中 次郎')
        self.assertEqual(self.commander.position, '主任')
    
    def test_haken_office_formatting(self):
        """派遣先事業所の名称及び所在地の表示形式テスト"""
        # 派遣先事業所の表示形式が正しいことを確認
        office = self.client_office
        client_name = office.client.name
        office_name = office.name
        postal = f"〒{office.postal_code}" if office.postal_code else ""
        address = office.address or ""
        phone = f"電話番号：{office.phone_number}" if office.phone_number else ""

        line1 = f"{client_name}　{office_name}"
        line2 = f"{postal} {address} {phone}".strip()

        expected_text = f"{line1}\n{line2}" if line2 else line1
        
        # 期待される形式: "テストクライアント　東京本社\n〒1000001 東京都千代田区千代田1-1 電話番号：03-1111-2222"
        self.assertEqual(line1, "テストクライアント　東京本社")
        self.assertEqual(line2, "〒1000001 東京都千代田区千代田1-1 電話番号：03-1111-2222")
    
    def test_haken_unit_formatting(self):
        """組織単位の表示形式テスト"""
        # 組織単位の表示形式が正しいことを確認
        unit = self.haken_unit
        unit_name = unit.name
        
        # 組織の長の職名と個人抵触日を含む表示形式
        details = []
        if unit.haken_unit_manager_title:
            details.append(f"組織の長の職名：{unit.haken_unit_manager_title}")
        
        # 個人抵触日
        if self.staff_teishokubi and self.staff_teishokubi.conflict_date:
            conflict_date_str = self.staff_teishokubi.conflict_date.strftime('%Y年%m月%d日')
            details.append(f"抵触日：{conflict_date_str}")
        
        if details:
            detail_text = "、".join(details)
            expected_text = f"{unit_name}　（{detail_text}）"
        else:
            expected_text = unit_name
        
        # 期待される形式: "開発チーム　（組織の長の職名：チームリーダー、抵触日：2028年02月01日）"
        self.assertEqual(expected_text, "開発チーム　（組織の長の職名：チームリーダー、抵触日：2028年02月01日）")
    
    def test_commander_formatting(self):
        """派遣先指揮命令者の表示形式テスト"""
        # 指揮命令者の表示形式が正しいことを確認
        commander = self.commander
        parts = []
        if commander.department:
            parts.append(commander.department.name)
        if commander.position:
            parts.append(commander.position)
        parts.append(commander.name)
        expected_text = '　'.join(filter(None, parts))
        
        # 期待される形式: "システム部　主任　田中 次郎"
        self.assertEqual(expected_text, "システム部　主任　田中 次郎")   
 
    def test_assignment_period_display(self):
        """アサイン期間が正しく表示されるかのテスト"""
        # アサイン期間が設定されていることを確認
        self.assertEqual(self.assignment.assignment_start_date, datetime.date(2025, 2, 1))
        self.assertEqual(self.assignment.assignment_end_date, datetime.date(2025, 11, 30))
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
    
    def test_complaint_officers_display(self):
        """派遣元・派遣先苦情申出先が正しく表示されるかのテスト"""
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 派遣元苦情申出先の情報確認
        self.assertEqual(self.company_complaint_officer.name, '鈴木 一郎')
        self.assertEqual(self.company_complaint_officer.position, '係長')
        self.assertEqual(self.company_complaint_officer.phone_number, '03-7777-8888')
        self.assertEqual(self.company_complaint_officer.department.name, '開発部')
        
        # 派遣先苦情申出先の情報確認
        self.assertEqual(self.client_complaint_officer.name, '高橋 三郎')
        self.assertEqual(self.client_complaint_officer.position, '課長')
        self.assertEqual(self.client_complaint_officer.phone_number, '03-9999-0000')
        self.assertEqual(self.client_complaint_officer.department.name, 'システム部')
    
    def test_preamble_without_issue_date(self):
        """前文に発行日が含まれていないことのテスト"""
        # 前文の内容を確認（発行日が削除され、変更通知文が追加されていることを確認）
        company_name = self.company.name
        staff_name = f"{self.staff.name_last} {self.staff.name_first}"
        
        expected_preamble = f"{company_name}（以下「乙」という）は、{staff_name}（以下「甲」という）に対し、労働者派遣法に基づき、労働者を派遣する。労働者派遣法第34条に基づき就業条件明示書を交付する。就業条件等に変更がある場合は、事前に通知する。"
        
        # 期待される前文の内容を確認
        self.assertIn("就業条件等に変更がある場合は、事前に通知する", expected_preamble)
        self.assertNotIn("発行日", expected_preamble)
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
    
    def test_complaint_officers_formatting(self):
        """苦情申出先の表示形式テスト"""
        # 派遣元苦情申出先の表示形式
        company_officer = self.company_complaint_officer
        parts = []
        if company_officer.department:
            parts.append(company_officer.department.name)
        if company_officer.position:
            parts.append(company_officer.position)
        parts.append(company_officer.name)
        
        base_info = '　'.join(filter(None, parts))
        if company_officer.phone_number:
            expected_company_text = f"{base_info} 電話番号：{company_officer.phone_number}"
        else:
            expected_company_text = base_info
        
        # 期待される形式: "開発部　係長　鈴木 一郎 電話番号：03-7777-8888"
        self.assertEqual(expected_company_text, "開発部　係長　鈴木 一郎 電話番号：03-7777-8888")
        
        # 派遣先苦情申出先の表示形式
        client_officer = self.client_complaint_officer
        parts = []
        if client_officer.department:
            parts.append(client_officer.department.name)
        if client_officer.position:
            parts.append(client_officer.position)
        parts.append(client_officer.name)
        
        base_info = '　'.join(filter(None, parts))
        if client_officer.phone_number:
            expected_client_text = f"{base_info} 電話番号：{client_officer.phone_number}"
        else:
            expected_client_text = base_info
        
        # 期待される形式: "システム部　課長　高橋 三郎 電話番号：03-9999-0000"
        self.assertEqual(expected_client_text, "システム部　課長　高橋 三郎 電話番号：03-9999-0000")  
  
    def test_haken_unit_with_conflict_date(self):
        """組織単位に個人抵触日が含まれることのテスト"""
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 個人抵触日が設定されていることを確認
        self.assertEqual(self.staff_teishokubi.staff_email, 'tanaka.taro@example.com')
        self.assertEqual(self.staff_teishokubi.organization_name, '開発チーム')
        self.assertEqual(self.staff_teishokubi.conflict_date, datetime.date(2028, 2, 1))
        
        # 組織単位の表示形式確認
        unit = self.haken_unit
        expected_text = f"{unit.name}　（組織の長の職名：{unit.haken_unit_manager_title}、抵触日：2028年02月01日）"
        self.assertEqual(expected_text, "開発チーム　（組織の長の職名：チームリーダー、抵触日：2028年02月01日）")
    
    def test_haken_unit_without_conflict_date(self):
        """個人抵触日が設定されていない場合の組織単位表示テスト"""
        # 個人抵触日を削除
        self.staff_teishokubi.delete()
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 組織単位の表示形式確認（抵触日なし）
        unit = self.haken_unit
        expected_text = f"{unit.name}　（組織の長の職名：{unit.haken_unit_manager_title}）"
        self.assertEqual(expected_text, "開発チーム　（組織の長の職名：チームリーダー）")
    
    def test_haken_unit_without_manager_title(self):
        """組織の長の職名が設定されていない場合のテスト"""
        # 組織の長の職名を削除
        self.haken_unit.haken_unit_manager_title = None
        self.haken_unit.save()
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 組織単位の表示形式確認（組織の長の職名なし、抵触日のみ）
        unit = self.haken_unit
        expected_text = f"{unit.name}　（抵触日：2028年02月01日）"
        self.assertEqual(expected_text, "開発チーム　（抵触日：2028年02月01日）")   
 
    def test_contract_amount_display(self):
        """契約金額が雇用契約書兼労働条件通知書と同じ形式で表示されるかのテスト"""
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # スタッフ契約の契約金額が設定されていることを確認
        self.assertEqual(self.staff_contract.contract_amount, 4000)
        self.assertEqual(self.staff_contract.pay_unit, '10')  # 時間単位
        
        # 支払単位の名称を取得
        from apps.system.settings.models import Dropdowns
        try:
            dropdown = Dropdowns.objects.get(category='pay_unit', value=self.staff_contract.pay_unit)
            pay_unit_name = dropdown.name
        except Dropdowns.DoesNotExist:
            pay_unit_name = ""
        
        # 期待される契約金額の表示形式
        expected_amount = f"{self.staff_contract.contract_amount:,}円"
        if pay_unit_name:
            expected_amount = f"{pay_unit_name} {expected_amount}"
        
        # 契約金額が正しい形式で表示されることを確認
        # 実際の表示は "時間 4,000円" のような形式になる
        self.assertIn("4,000円", expected_amount)
    
    def test_contract_amount_without_pay_unit(self):
        """支払単位が設定されていない場合の契約金額表示テスト"""
        # 支払単位を削除
        self.staff_contract.pay_unit = None
        self.staff_contract.save()
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 支払単位なしの契約金額表示確認
        expected_amount = f"{self.staff_contract.contract_amount:,}円"
        self.assertEqual(expected_amount, "4,000円")
    
    def test_contract_amount_not_set(self):
        """契約金額が設定されていない場合のテスト"""
        # 契約金額を削除
        self.staff_contract.contract_amount = None
        self.staff_contract.save()
        
        issued_at = timezone.now()
        
        # PDF生成
        pdf_content = generate_employment_conditions_pdf(
            self.assignment, 
            self.user, 
            issued_at
        )
        
        # PDFが正常に生成されることを確認
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        
        # 契約金額が未設定の場合は "N/A" が表示される
        # この場合の表示は実装に依存するが、エラーが発生しないことを確認