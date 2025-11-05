"""
スタッフ契約未発行時の関連データリセットテスト
"""
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
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


class StaffContractUnissueFlowTest(TestCase):
    """スタッフ契約未発行フローのテスト"""
    
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
        """スタッフ契約を作成（発行済み状態）"""
        return StaffContract.objects.create(
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='テストスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,  # 発行済み
            contract_number='SC-2025-001',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.staff_pattern,
            job_category=self.job_category,
            issued_at=timezone.now(),
            issued_by=self.user,
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
        
        # 就業条件明示書を確認済みにする
        assignment.employment_conditions_confirmed_at = timezone.now()
        assignment.save()
        
        return assignment
    
    def test_staff_contract_unissue_resets_employment_conditions_confirmation(self):
        """スタッフ契約未発行時に就業条件明示書確認状態がリセットされることをテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. 初期状態の確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)
        self.assertIsNotNone(self.assignment.employment_conditions_confirmed_at)
        
        # 2. スタッフ契約確認一覧で就業条件明示書が表示されることを確認
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '就業条件明示書')
        
        # 3. スタッフ契約を未発行にする（is_issuedなしでPOST）
        response = self.client.post(
            reverse('contract:staff_contract_issue', kwargs={'pk': self.staff_contract.pk}),
            {}  # is_issuedが空 = 未発行
        )
        
        # 4. 未発行後の状態確認
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        self.assignment.refresh_from_db()
        
        # スタッフ契約が承認済みに戻っていることを確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)
        self.assertIsNone(self.staff_contract.issued_at)
        self.assertIsNone(self.staff_contract.issued_by)
        
        # 関連する契約アサインの確認状態がリセットされていることを確認
        self.assertIsNone(self.assignment.employment_conditions_confirmed_at)
        
        # 5. スタッフ契約確認一覧で就業条件明示書が表示されないことを確認
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '就業条件明示書')
        # 確認対象の書類が見つからないメッセージが表示されることを確認
        self.assertContains(response, '確認対象の書類が見つかりませんでした。')
    
    def test_staff_contract_reissue_after_unissue(self):
        """スタッフ契約を未発行→再発行した場合のテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ契約を未発行にする
        response = self.client.post(
            reverse('contract:staff_contract_issue', kwargs={'pk': self.staff_contract.pk}),
            {}  # is_issuedが空 = 未発行
        )
        
        # 2. 未発行後の状態確認
        self.staff_contract.refresh_from_db()
        self.assignment.refresh_from_db()
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)
        self.assertIsNone(self.assignment.employment_conditions_confirmed_at)
        
        # 3. スタッフ契約を再発行する
        from unittest.mock import patch
        with patch('apps.contract.views_staff.generate_contract_pdf_content') as mock_pdf:
            mock_pdf.return_value = (b'fake_pdf_content', 'test.pdf', 'テスト契約書')
            
            response = self.client.post(
                reverse('contract:staff_contract_issue', kwargs={'pk': self.staff_contract.pk}),
                {'is_issued': 'on'}
            )
        
        # 4. 再発行後の状態確認
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        self.assignment.refresh_from_db()
        
        # スタッフ契約が発行済みになっていることを確認
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)
        self.assertIsNotNone(self.staff_contract.issued_at)
        self.assertEqual(self.staff_contract.issued_by, self.user)
        
        # 関連する契約アサインの確認状態がリセットされていることを確認（再発行時もリセット）
        self.assertIsNone(self.assignment.employment_conditions_confirmed_at)
        
        # 5. スタッフ契約確認一覧で就業条件明示書が再び表示されることを確認
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '就業条件明示書')
        self.assertContains(response, 'テストスタッフ契約')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        pass