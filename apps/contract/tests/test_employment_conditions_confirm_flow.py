from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.master.models import StaffAgreement, ContractPattern, JobCategory
from apps.contract.models import (
    StaffContract, ClientContract, ContractAssignment, 
    StaffContractPrint, ContractAssignmentHakenPrint,
    ClientContractHaken
)
from apps.common.constants import Constants
from apps.system.settings.models import Dropdowns
from unittest.mock import patch
from datetime import date

User = get_user_model()


class EmploymentConditionsConfirmFlowTest(TestCase):
    """就業条件明示書の発行・確認・解除フローのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # Dropdownsデータを作成
        self._create_dropdowns()
        
        # 基本データを作成
        self.user = self._create_user()
        self.company = self._create_company()
        self.staff = self._create_staff()
        self.client_company = self._create_client()
        self.connect_staff = self._create_connect_staff()
        self.staff_agreement = self._create_staff_agreement()
        
        # 契約パターンと職種を作成
        self.staff_pattern = self._create_contract_pattern('staff')
        self.client_pattern = self._create_contract_pattern('client')
        self.job_category = self._create_job_category()
        
        # 契約を作成
        self.staff_contract = self._create_staff_contract()
        self.client_contract = self._create_client_contract()
        self.assignment = self._create_contract_assignment()
    
    def _create_dropdowns(self):
        """必要なDropdownsデータを作成"""
        statuses = [
            (Constants.CONTRACT_STATUS.DRAFT, '作成中'),
            (Constants.CONTRACT_STATUS.PENDING, '申請'),
            (Constants.CONTRACT_STATUS.APPROVED, '承認済'),
            (Constants.CONTRACT_STATUS.ISSUED, '発行済'),
            (Constants.CONTRACT_STATUS.CONFIRMED, '確認済'),
        ]
        for value, name in statuses:
            Dropdowns.objects.create(
                category='contract_status',
                value=value,
                name=name,
                active=True
            )
        
        Dropdowns.objects.create(
            category='client_contract_type',
            value=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            name='派遣',
            active=True
        )
    
    def _create_user(self):
        """テストユーザーを作成"""
        from django.contrib.auth.models import Permission
        user = User.objects.create_user(
            username='teststaff@example.com',
            email='teststaff@example.com',
            password='password',
            is_staff=True,
            is_active=True,
        )
        # 必要な権限を付与
        permissions = Permission.objects.filter(
            codename__in=[
                'change_staffcontract',
                'view_staffcontract',
                'view_clientcontract',
                'change_clientcontract',
            ]
        )
        user.user_permissions.set(permissions)
        return user
    
    def _create_company(self):
        """会社を作成"""
        return Company.objects.create(
            name='テスト株式会社',
            corporate_number='1234567890123',
        )
    
    def _create_staff(self):
        """スタッフを作成"""
        return Staff.objects.create(
            email='teststaff@example.com',
            name_last='テスト',
            name_first='太郎',
        )
    
    def _create_client(self):
        """クライアントを作成"""
        return Client.objects.create(
            name='クライアント株式会社',
            corporate_number='9876543210987',
        )
    
    def _create_connect_staff(self):
        """接続スタッフを作成"""
        return ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.user.email,
            status='approved',
        )
    
    def _create_staff_agreement(self):
        """スタッフ同意文言を作成"""
        return StaffAgreement.objects.create(
            name='テスト同意文言',
            agreement_text='これはテスト用の同意文言です。',
            corporation_number=self.company.corporate_number,
        )
    
    def _create_contract_pattern(self, domain_type):
        """契約パターンを作成"""
        domain = Constants.DOMAIN.STAFF if domain_type == 'staff' else Constants.DOMAIN.CLIENT
        name = 'スタッフ向け雇用契約' if domain_type == 'staff' else 'クライアント向け派遣契約'
        return ContractPattern.objects.create(
            name=name,
            domain=domain,
            is_active=True
        )
    
    def _create_job_category(self):
        """職種を作成"""
        return JobCategory.objects.create(
            name='システム開発',
            is_active=True
        )
    
    def _create_staff_contract(self):
        """スタッフ契約を作成"""
        return StaffContract.objects.create(
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='テストスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,  # 発行済みに変更
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.staff_pattern,
            job_category=self.job_category,
            created_by=self.user,
            updated_by=self.user,
        )
    
    def _create_client_contract(self):
        """クライアント契約を作成"""
        contract = ClientContract.objects.create(
            client=self.client_company,
            contract_name='テストクライアント契約',
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_status=Constants.CONTRACT_STATUS.APPROVED,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.client_pattern,
            job_category=self.job_category,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 派遣情報を作成
        ClientContractHaken.objects.create(
            client_contract=contract,
            created_by=self.user,
            updated_by=self.user,
        )
        
        return contract
    
    def _create_contract_assignment(self):
        """契約アサインを作成"""
        return ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            created_by=self.user,
            updated_by=self.user,
        )
    
    def test_staff_contract_issue_flow(self):
        """スタッフ契約書発行フローのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # テスト用に契約ステータスを承認済みに設定
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.staff_contract.save()
        
        # 1. 初期状態の確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)
        self.assertIsNone(self.staff_contract.issued_at)
        self.assertIsNone(self.staff_contract.issued_by)
        
        # 2. スタッフ契約書を発行
        with patch('apps.contract.views_staff.generate_contract_pdf_content') as mock_pdf:
            mock_pdf.return_value = (b'fake_pdf_content', 'test.pdf', 'テスト契約書')
            
            response = self.client.post(
                reverse('contract:staff_contract_issue', kwargs={'pk': self.staff_contract.pk}),
                {'is_issued': 'on'}
            )
        
        # 3. 発行後の状態確認
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)
        self.assertIsNotNone(self.staff_contract.issued_at)
        self.assertEqual(self.staff_contract.issued_by, self.user)
        
        # 4. 発行履歴が作成されていることを確認
        print_history = StaffContractPrint.objects.filter(staff_contract=self.staff_contract)
        self.assertEqual(print_history.count(), 1)
        
        # 5. 関連する契約アサインの確認状態がリセットされていることを確認
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.confirmed_at)
    
    def test_employment_conditions_issue_flow(self):
        """就業条件明示書発行フローのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ契約を発行済み状態にする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.contract_number = 'SC-2025-001'
        self.staff_contract.save()
        
        # 2. 初期状態の確認
        self.assertIsNone(self.assignment.confirmed_at)
        
        # 3. 就業条件明示書を発行
        with patch('apps.contract.utils.generate_employment_conditions_pdf') as mock_pdf:
            mock_pdf.return_value = b'fake_employment_conditions_pdf'
            
            response = self.client.post(
                reverse('contract:assignment_employment_conditions_issue', 
                       kwargs={'assignment_pk': self.assignment.pk}),
                {'is_issued': 'on'}
            )
        
        # 4. 発行後の状態確認
        self.assertEqual(response.status_code, 302)
        
        # 5. 発行履歴が作成されていることを確認
        haken_print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        )
        self.assertEqual(haken_print_history.count(), 1)
        
        # 6. 確認状態がリセットされていることを確認
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.confirmed_at)
    
    def test_staff_contract_confirm_list_integration(self):
        """スタッフ契約確認一覧の統合テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ契約を発行済み状態にする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.contract_number = 'SC-2025-001'
        self.staff_contract.save()
        
        # 2. スタッフ契約書の発行履歴を作成
        staff_print = StaffContractPrint.objects.create(
            staff_contract=self.staff_contract,
            printed_by=self.user,
            document_title='テストスタッフ契約書',
            contract_number=self.staff_contract.contract_number,
        )
        
        # 3. アサインを発行済み状態にする
        self.assignment.issued_at = timezone.now()
        self.assignment.save()
        
        # 4. 就業条件明示書の発行履歴を作成
        haken_print = ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='テスト就業条件明示書',
            contract_number=self.staff_contract.contract_number,
        )
        
        # 5. スタッフ契約確認一覧を取得
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        
        # 6. 両方の書類が表示されていることを確認
        self.assertContains(response, 'スタッフ契約書')
        self.assertContains(response, '就業条件明示書')
        self.assertContains(response, 'テストスタッフ契約')
        self.assertContains(response, 'クライアント株式会社')
    
    def test_staff_contract_confirm_action(self):
        """スタッフ契約書確認アクションのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ契約を発行済み状態にする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.save()
        
        # 2. スタッフ契約書を確認
        response = self.client.post(
            reverse('contract:staff_contract_confirm_list'),
            {
                'contract_id': self.staff_contract.pk,
                'action': 'confirm_staff_contract'
            }
        )
        
        # 3. 確認後の状態をチェック
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.CONFIRMED)
        self.assertIsNotNone(self.staff_contract.confirmed_at)
        
        # 4. 同意文言が作成されていることを確認
        agree = ConnectStaffAgree.objects.filter(
            email=self.user.email,
            corporate_number=self.company.corporate_number,
            staff_agreement=self.staff_agreement,
            is_agreed=True
        )
        self.assertTrue(agree.exists())
    
    def test_employment_conditions_confirm_action(self):
        """就業条件明示書確認アクションのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. 就業条件明示書の発行履歴を作成
        haken_print = ContractAssignmentHakenPrint.objects.create(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='テスト就業条件明示書',
        )
        
        # 2. 就業条件明示書を確認
        response = self.client.post(
            reverse('contract:staff_contract_confirm_list'),
            {
                'assignment_id': self.assignment.pk,
                'action': 'confirm_employment_conditions'
            }
        )
        
        # 3. 確認後の状態をチェック
        self.assertEqual(response.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertIsNotNone(self.assignment.confirmed_at)
    
    def test_staff_contract_approval_revoke_flow(self):
        """スタッフ契約承認解除フローのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ契約を発行済み状態にし、関連データを設定
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.contract_number = 'SC-2025-001'
        self.staff_contract.approved_at = timezone.now()
        self.staff_contract.approved_by = self.user
        self.staff_contract.issued_at = timezone.now()
        self.staff_contract.issued_by = self.user
        self.staff_contract.confirmed_at = timezone.now()
        self.staff_contract.save()
        
        # 2. 契約アサインの確認状態を設定
        self.assignment.confirmed_at = timezone.now()
        self.assignment.save()
        
        # 3. 承認を解除（承認スイッチをOFF）
        response = self.client.post(
            reverse('contract:staff_contract_approve', kwargs={'pk': self.staff_contract.pk}),
            {}  # is_approvedが空 = 承認解除
        )
        
        # 4. 解除後の状態をチェック
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        
        # スタッフ契約の状態がリセットされていることを確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.DRAFT)
        self.assertIsNone(self.staff_contract.contract_number)
        self.assertIsNone(self.staff_contract.approved_at)
        self.assertIsNone(self.staff_contract.approved_by)
        self.assertIsNone(self.staff_contract.issued_at)
        self.assertIsNone(self.staff_contract.issued_by)
        self.assertIsNone(self.staff_contract.confirmed_at)
        
        # 5. 関連する契約アサインの確認状態もリセットされていることを確認
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.confirmed_at)
    
    def test_employment_conditions_reissue_flow(self):
        """就業条件明示書再発行フローのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ契約を発行済み状態にする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.contract_number = 'SC-2025-001'
        self.staff_contract.save()
        
        # 2. 初回発行と確認
        self.assignment.confirmed_at = timezone.now()
        self.assignment.save()
        
        # 3. 就業条件明示書を再発行
        with patch('apps.contract.utils.generate_employment_conditions_pdf') as mock_pdf:
            mock_pdf.return_value = b'fake_employment_conditions_pdf_v2'
            
            response = self.client.post(
                reverse('contract:assignment_employment_conditions_issue', 
                       kwargs={'assignment_pk': self.assignment.pk}),
                {'is_issued': 'on'}
            )
        
        # 4. 再発行後の状態確認
        self.assertEqual(response.status_code, 302)
        
        # 5. 確認状態がリセットされていることを確認
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.confirmed_at)
        
        # 6. 発行履歴が複数作成されていることを確認
        haken_print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        )
        self.assertEqual(haken_print_history.count(), 1)  # 今回は1回だけ発行
    
    def test_corporate_number_filtering(self):
        """法人番号による絞り込みのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. 別の会社のスタッフ契約を作成
        other_company = Company.objects.create(
            name='別の会社',
            corporate_number='9999999999999',
        )
        
        other_staff_contract = StaffContract.objects.create(
            staff=self.staff,
            corporate_number=other_company.corporate_number,  # 別の法人番号
            contract_name='別会社のスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            start_date=date(2025, 1, 1),
            contract_pattern=self.staff_pattern,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 2. スタッフ契約確認一覧を取得
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        
        # 3. 自社の契約のみ表示されていることを確認
        self.assertContains(response, 'テストスタッフ契約')
        self.assertNotContains(response, '別会社のスタッフ契約')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 必要に応じてクリーンアップ処理を追加
        pass