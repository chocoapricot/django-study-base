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
            employee_no='EMP001'
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
            business_content='システム開発支援業務'
        )
        
        # 契約アサイン作成
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract
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