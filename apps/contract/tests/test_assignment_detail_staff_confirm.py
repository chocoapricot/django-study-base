"""
契約アサイン詳細画面のスタッフ確認表示テスト
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


class AssignmentDetailStaffConfirmTest(TestCase):
    """契約アサイン詳細画面のスタッフ確認表示テスト"""
    
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
                'view_clientcontract',
                'view_staffcontract',
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
        
        return assignment
    
    def test_staff_confirm_display_unchecked(self):
        """スタッフ確認が未確認の場合の表示テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. 初期状態の確認（未確認）
        self.assertIsNone(self.assignment.employment_conditions_confirmed_at)
        
        # 2. 契約アサイン詳細画面を取得
        response = self.client.get(
            reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        )
        
        # 3. レスポンスの確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ確認')
        
        # 4. スタッフ確認スイッチが未チェック状態であることを確認
        self.assertNotContains(response, 'id="staffConfirmSwitch" name="is_staff_confirmed" checked')
        
        # 5. スタッフ確認の確認日時が表示されていないことを確認（就業条件明示書の発行日時は別）
        # スタッフ確認の部分のみをチェック
        self.assertNotContains(response, 'スタッフ確認\n                            （')
    
    def test_staff_confirm_display_checked(self):
        """スタッフ確認が確認済みの場合の表示テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ確認を実行
        confirmed_at = timezone.now()
        self.assignment.employment_conditions_confirmed_at = confirmed_at
        self.assignment.save()
        
        # 2. 契約アサイン詳細画面を取得
        response = self.client.get(
            reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        )
        
        # 3. レスポンスの確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ確認')
        
        # 4. スタッフ確認スイッチがチェック状態であることを確認
        self.assertContains(response, 'checked')
        
        # 5. 確認日時が表示されていることを確認（年月日のみチェック）
        expected_date_part = confirmed_at.strftime('%Y/%m/%d')
        self.assertContains(response, expected_date_part)
    
    def test_context_variables(self):
        """ビューからテンプレートに渡されるコンテキスト変数のテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        
        # 1. スタッフ確認を実行
        confirmed_at = timezone.now()
        self.assignment.employment_conditions_confirmed_at = confirmed_at
        self.assignment.save()
        
        # 2. 契約アサイン詳細画面を取得
        response = self.client.get(
            reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        )
        
        # 3. コンテキスト変数の確認
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['employment_conditions_confirmed'])
        self.assertEqual(response.context['employment_conditions_confirmed_at'], confirmed_at)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        pass