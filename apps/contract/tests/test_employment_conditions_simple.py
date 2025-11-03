"""
就業条件明示書発行の簡単なテストケース
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from apps.common.constants import Constants
from apps.contract.models import (
    ClientContract, StaffContract, ContractAssignment, 
    ContractAssignmentHakenPrint
)
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import ContractPattern, EmploymentType

User = get_user_model()


class EmploymentConditionsSimpleTest(TestCase):
    """就業条件明示書発行の簡単なテストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # クライアント作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123'
        )
        
        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com'
        )
        
        # 契約パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain=Constants.DOMAIN.CLIENT
        )
        
        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )
        
        # クライアント契約作成（派遣）
        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テストクライアント契約',
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_pattern=self.contract_pattern,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            contract_status=Constants.CONTRACT_STATUS.APPROVED
        )
        
        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='テストスタッフ契約',
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            contract_number=None
        )
        
        # 契約アサイン作成
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract
        )
    
    def test_print_history_creation(self):
        """発行履歴の作成テスト"""
        # 発行履歴を作成
        print_history = ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='就業条件明示書',
            contract_number='TEST-001'
        )
        
        # 作成されたことを確認
        self.assertIsNotNone(print_history.pk)
        self.assertEqual(print_history.contract_number, 'TEST-001')
        self.assertEqual(print_history.document_title, '就業条件明示書')
    
    def test_same_contract_number_check(self):
        """同じ契約番号の発行履歴チェックテスト"""
        # 最初の発行履歴を作成
        ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='就業条件明示書',
            contract_number='TEST-001'
        )
        
        # 同じ契約番号の履歴があるかチェック
        existing_record = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            contract_number='TEST-001'
        ).first()
        
        self.assertIsNotNone(existing_record)
        
        # 異なる契約番号の履歴はないことを確認
        different_record = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            contract_number='TEST-002'
        ).first()
        
        self.assertIsNone(different_record)
    
    def test_multiple_contract_numbers(self):
        """複数の契約番号での発行履歴テスト"""
        # 最初の契約番号で発行
        ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='就業条件明示書',
            contract_number='TEST-001'
        )
        
        # 2番目の契約番号で発行
        ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='就業条件明示書',
            contract_number='TEST-002'
        )
        
        # 両方の履歴が存在することを確認
        total_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment
        ).count()
        self.assertEqual(total_count, 2)
        
        # 各契約番号の履歴が存在することを確認
        test001_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            contract_number='TEST-001'
        ).count()
        self.assertEqual(test001_count, 1)
        
        test002_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            contract_number='TEST-002'
        ).count()
        self.assertEqual(test002_count, 1)