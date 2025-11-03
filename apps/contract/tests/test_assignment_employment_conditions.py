"""
契約アサイン就業条件明示書のテストケース
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta

from apps.common.constants import Constants
from apps.contract.models import (
    ClientContract, StaffContract, ContractAssignment, 
    ContractAssignmentHakenPrint
)
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from apps.master.models import ContractPattern, EmploymentType

User = get_user_model()


class AssignmentEmploymentConditionsTest(TestCase):
    """就業条件明示書発行のテストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # クライアント作成
        self.client_obj = ClientModel.objects.create(
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
        
        # テストクライアント
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_draft_status_switch_disabled(self):
        """作成中状態ではスイッチが無効化されることをテスト"""
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'disabled')
        self.assertFalse(response.context['employment_conditions_issued'])
    
    def test_pending_status_switch_disabled(self):
        """申請状態ではスイッチが無効化されることをテスト"""
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.PENDING
        self.staff_contract.save()
        
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'disabled')
        self.assertFalse(response.context['employment_conditions_issued'])
    
    def test_approved_status_switch_enabled_no_history(self):
        """承認済み状態で発行履歴がない場合、スイッチが有効でOFFになることをテスト"""
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.staff_contract.contract_number = 'TEST-001'
        self.staff_contract.save()
        
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'disabled')
        self.assertFalse(response.context['employment_conditions_issued'])
    
    def test_approved_status_switch_disabled_with_history(self):
        """承認済み状態で同じ契約番号の発行履歴がある場合、スイッチが無効でONになることをテスト"""
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.staff_contract.contract_number = 'TEST-001'
        self.staff_contract.save()
        
        # 発行履歴を作成
        ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='就業条件明示書',
            contract_number='TEST-001'
        )
        
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'disabled')
        self.assertTrue(response.context['employment_conditions_issued'])
    
    def test_issue_employment_conditions_success(self):
        """就業条件明示書の発行が成功することをテスト"""
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.staff_contract.contract_number = 'TEST-001'
        self.staff_contract.save()
        
        url = reverse('contract:assignment_employment_conditions_issue', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.post(url)
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 発行履歴が作成されることを確認
        history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            contract_number='TEST-001'
        ).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.contract_number, 'TEST-001')
    
    def test_issue_employment_conditions_draft_status_error(self):
        """作成中状態では発行できないことをテスト"""
        url = reverse('contract:assignment_employment_conditions_issue', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.post(url)
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 発行履歴が作成されないことを確認
        history_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment
        ).count()
        self.assertEqual(history_count, 0)
    
    def test_issue_employment_conditions_duplicate_error(self):
        """同じ契約番号で重複発行できないことをテスト"""
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.staff_contract.contract_number = 'TEST-001'
        self.staff_contract.save()
        
        # 最初の発行履歴を作成
        ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='就業条件明示書',
            contract_number='TEST-001'
        )
        
        url = reverse('contract:assignment_employment_conditions_issue', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.post(url)
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 発行履歴が1件のままであることを確認
        history_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            contract_number='TEST-001'
        ).count()
        self.assertEqual(history_count, 1)
    
    def test_reissue_after_contract_number_change(self):
        """契約番号が変更された場合は再発行可能であることをテスト"""
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.staff_contract.contract_number = 'TEST-001'
        self.staff_contract.save()
        
        # 最初の発行履歴を作成
        ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='就業条件明示書',
            contract_number='TEST-001'
        )
        
        # 契約番号を変更
        self.staff_contract.contract_number = 'TEST-002'
        self.staff_contract.save()
        
        # 詳細画面で発行可能状態になることを確認
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['employment_conditions_issued'])
        
        # 新しい契約番号で発行可能であることを確認
        issue_url = reverse('contract:assignment_employment_conditions_issue', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.post(issue_url)
        
        self.assertEqual(response.status_code, 302)
        
        # 新しい契約番号の発行履歴が作成されることを確認
        new_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            contract_number='TEST-002'
        ).first()
        self.assertIsNotNone(new_history)
        
        # 合計2件の履歴があることを確認
        total_history_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment
        ).count()
        self.assertEqual(total_history_count, 2)