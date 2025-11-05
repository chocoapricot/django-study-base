"""
スタッフ契約承認解除時の関連データクリアテスト
"""
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.utils import timezone
from datetime import date

from apps.accounts.models import MyUser as User
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company
from apps.connect.models import ConnectStaff
from apps.contract.models import (
    StaffContract, ClientContract, ContractAssignment, 
    ContractAssignmentHakenPrint
)
from apps.master.models_contract import ContractPattern
from apps.master.models_staff import StaffAgreement
from apps.master.models import JobCategory, Dropdowns
from apps.common.constants import Constants


class StaffContractApprovalRevokeTest(TestCase):
    """スタッフ契約承認解除時の関連データクリアテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self._create_dropdowns()
        self.user = self._create_user()
        self.company = self._create_company()
        self.staff = self._create_staff()
        self.client_company = self._create_client()
        self.connect_staff = self._create_connect_staff()
        self.staff_agreement = self._create_staff_agreement()
        self.job_category = self._create_job_category()
        self.staff_pattern = self._create_contract_pattern('staff')
        self.client_pattern = self._create_contract_pattern('client')
        self.staff_contract = self._create_staff_contract()
        self.client_contract = self._create_client_contract()
        self.assignment = self._create_assignment()
        
        self.client = TestClient()
    
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
        """スタッフ契約を作成（承認済み状態）"""
        return StaffContract.objects.create(
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='テストスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.APPROVED,  # 承認済み
            contract_number='SC-2025-001',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.staff_pattern,
            job_category=self.job_category,
            approved_at=timezone.now(),
            approved_by=self.user,
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
        return contract
    
    def _create_assignment(self):
        """契約アサインを作成"""
        assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 就業条件明示書を発行済みにする
        haken_print = ContractAssignmentHakenPrint.objects.create(
            contract_assignment=assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='テスト就業条件明示書',
            contract_number=self.staff_contract.contract_number,
        )
        
        # 就業条件明示書を発行・確認済みにする
        assignment.issued_at = timezone.now()
        assignment.confirmed_at = timezone.now()
        assignment.save()
        
        return assignment
    
    def test_staff_contract_approval_revoke_clears_assignment_status(self):
        """スタッフ契約承認解除時に契約アサインの発行・確認状態がリセットされることをテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. 初期状態の確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)
        self.assertIsNotNone(self.assignment.issued_at)
        self.assertIsNotNone(self.assignment.confirmed_at)
        
        # 就業条件明示書の発行履歴が存在することを確認
        haken_prints = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        )
        self.assertEqual(haken_prints.count(), 1)
        
        # 2. スタッフ契約の承認を解除する（is_approvedなしでPOST）
        response = self.client.post(
            reverse('contract:staff_contract_approve', kwargs={'pk': self.staff_contract.pk}),
            {}  # is_approvedが空 = 承認解除
        )
        
        # 3. 承認解除後の状態確認
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        self.assignment.refresh_from_db()
        
        # スタッフ契約が作成中に戻っていることを確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.DRAFT)
        self.assertIsNone(self.staff_contract.approved_at)
        self.assertIsNone(self.staff_contract.approved_by)
        self.assertIsNone(self.staff_contract.issued_at)
        self.assertIsNone(self.staff_contract.issued_by)
        
        # 関連する契約アサインの発行・確認状態がリセットされていることを確認
        self.assertIsNone(self.assignment.issued_at)
        self.assertIsNone(self.assignment.confirmed_at)
        
        # 就業条件明示書の発行履歴は保持されていることを確認
        haken_prints_after = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        )
        self.assertEqual(haken_prints_after.count(), 1)  # 発行履歴は保持される
    
    def test_staff_contract_approval_revoke_from_issued_status(self):
        """発行済み状態からの承認解除テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # スタッフ契約を発行済み状態にする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.issued_at = timezone.now()
        self.staff_contract.issued_by = self.user
        self.staff_contract.save()
        
        # 1. 初期状態の確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)
        
        # 2. スタッフ契約の承認を解除する
        response = self.client.post(
            reverse('contract:staff_contract_approve', kwargs={'pk': self.staff_contract.pk}),
            {}  # is_approvedが空 = 承認解除
        )
        
        # 3. 承認解除後の状態確認
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        self.assignment.refresh_from_db()
        
        # スタッフ契約が作成中に戻っていることを確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.DRAFT)
        self.assertIsNone(self.staff_contract.approved_at)
        self.assertIsNone(self.staff_contract.approved_by)
        self.assertIsNone(self.staff_contract.issued_at)
        self.assertIsNone(self.staff_contract.issued_by)
        
        # 関連する契約アサインの発行・確認状態がリセットされていることを確認
        self.assertIsNone(self.assignment.issued_at)
        self.assertIsNone(self.assignment.confirmed_at)
        
        # 就業条件明示書の発行履歴は保持されていることを確認
        haken_prints_after = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        )
        self.assertEqual(haken_prints_after.count(), 1)  # 発行履歴は保持される
    
    def test_multiple_assignments_approval_revoke(self):
        """複数の契約アサインがある場合の承認解除テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 追加のクライアント契約を作成
        additional_client = Client.objects.create(
            name='追加クライアント株式会社',
            corporate_number='1111111111111',
        )
        
        additional_client_contract = ClientContract.objects.create(
            client=additional_client,
            contract_name='追加テストクライアント契約',
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_status=Constants.CONTRACT_STATUS.APPROVED,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.client_pattern,
            job_category=self.job_category,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 追加の契約アサインを作成
        additional_assignment = ContractAssignment.objects.create(
            client_contract=additional_client_contract,
            staff_contract=self.staff_contract,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 追加の就業条件明示書を発行
        ContractAssignmentHakenPrint.objects.create(
            contract_assignment=additional_assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='追加テスト就業条件明示書',
            contract_number=self.staff_contract.contract_number,
        )
        
        additional_assignment.issued_at = timezone.now()
        additional_assignment.confirmed_at = timezone.now()
        additional_assignment.save()
        
        # 1. 初期状態の確認
        total_haken_prints = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment__staff_contract=self.staff_contract,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        ).count()
        self.assertEqual(total_haken_prints, 2)
        
        # 2. スタッフ契約の承認を解除する
        response = self.client.post(
            reverse('contract:staff_contract_approve', kwargs={'pk': self.staff_contract.pk}),
            {}  # is_approvedが空 = 承認解除
        )
        
        # 3. 承認解除後の状態確認
        self.assertEqual(response.status_code, 302)
        
        # 全ての関連する就業条件明示書の発行履歴は保持されていることを確認
        total_haken_prints_after = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment__staff_contract=self.staff_contract,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        ).count()
        self.assertEqual(total_haken_prints_after, 2)  # 発行履歴は保持される
        
        # 全ての関連する契約アサインの発行・確認状態がリセットされていることを確認
        self.assignment.refresh_from_db()
        additional_assignment.refresh_from_db()
        
        self.assertIsNone(self.assignment.issued_at)
        self.assertIsNone(self.assignment.confirmed_at)
        self.assertIsNone(additional_assignment.issued_at)
        self.assertIsNone(additional_assignment.confirmed_at)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        pass