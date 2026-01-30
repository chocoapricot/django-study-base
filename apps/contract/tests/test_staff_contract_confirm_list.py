"""
スタッフ契約確認一覧のテスト
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
    ContractAssignmentHakenPrint, StaffContractPrint
)
from apps.master.models_contract import ContractPattern
from apps.master.models_staff import StaffAgreement
from apps.master.models import JobCategory, Dropdowns
from apps.common.constants import Constants
from apps.common.middleware import set_current_tenant_id


class StaffContractConfirmListTest(TestCase):
    """スタッフ契約確認一覧のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.company = self._create_company()
        set_current_tenant_id(self.company.id)

        self._create_dropdowns()
        self.user = self._create_user()
        self.staff = self._create_staff()
        self.client_company = self._create_client()
        self.connect_staff = self._create_connect_staff()
        self.staff_agreement = self._create_staff_agreement()
        self.job_category = self._create_job_category()
        self.staff_pattern = self._create_contract_pattern('staff')
        self.client_pattern = self._create_contract_pattern('client')
        
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
            tenant_id=self.company.id,
            username='teststaff@example.com',
            email='teststaff@example.com',
            password='password',
            is_staff=True,
            is_active=True,
        )
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
            tenant_id=self.company.id,
            email='teststaff@example.com',
            name_last='テスト',
            name_first='太郎',
        )
    
    def _create_client(self):
        """クライアントを作成"""
        return Client.objects.create(
            tenant_id=self.company.id,
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
            tenant_id=self.company.id,
            name='テスト同意文言',
            agreement_text='これはテスト用の同意文言です。',
            corporation_number=self.company.corporate_number,
        )
    
    def _create_contract_pattern(self, domain_type):
        """契約パターンを作成"""
        domain = Constants.DOMAIN.STAFF if domain_type == 'staff' else Constants.DOMAIN.CLIENT
        name = 'スタッフ向け雇用契約' if domain_type == 'staff' else 'クライアント向け派遣契約'
        return ContractPattern.objects.create(
            tenant_id=self.company.id,
            name=name,
            domain=domain,
            is_active=True
        )
    
    def _create_job_category(self):
        """職種を作成"""
        return JobCategory.objects.create(
            tenant_id=self.company.id,
            name='システム開発',
            is_active=True
        )
    
    def test_employment_conditions_display_with_issued_at(self):
        """issued_atがある就業条件明示書が表示されることをテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # スタッフ契約を作成（発行済み状態）
        staff_contract = StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='テストスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            contract_number='SC-2025-001',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.staff_pattern,
            job_category=self.job_category,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # クライアント契約を作成
        client_contract = ClientContract.objects.create(
            tenant_id=self.company.id,
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
        
        # 契約アサインを作成（issued_atあり）
        assignment = ContractAssignment.objects.create(
            tenant_id=self.company.id,
            client_contract=client_contract,
            staff_contract=staff_contract,
            issued_at=timezone.now(),  # 発行済み
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 就業条件明示書の発行履歴を作成
        ContractAssignmentHakenPrint.objects.create(
            tenant_id=self.company.id,
            contract_assignment=assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='テスト就業条件明示書',
            contract_number=staff_contract.contract_number,
        )
        
        # スタッフ契約確認一覧にアクセス
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        # レスポンスの確認
        self.assertEqual(response.status_code, 200)
        confirm_items = response.context['confirm_items']
        
        # 就業条件明示書が表示されていることを確認
        employment_conditions_items = [
            item for item in confirm_items 
            if item['type'] == 'employment_conditions'
        ]
        self.assertEqual(len(employment_conditions_items), 1)
        
        # ソート日時がissued_atになっていることを確認
        item = employment_conditions_items[0]
        self.assertEqual(item['sort_date'], assignment.issued_at)
    
    def test_employment_conditions_not_display_without_issued_at(self):
        """issued_atがない就業条件明示書が表示されないことをテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # スタッフ契約を作成（発行済み状態）
        staff_contract = StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='テストスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            contract_number='SC-2025-001',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.staff_pattern,
            job_category=self.job_category,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # クライアント契約を作成
        client_contract = ClientContract.objects.create(
            tenant_id=self.company.id,
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
        
        # 契約アサインを作成（issued_atなし）
        assignment = ContractAssignment.objects.create(
            tenant_id=self.company.id,
            client_contract=client_contract,
            staff_contract=staff_contract,
            # issued_at=None（未発行）
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 就業条件明示書の発行履歴を作成（履歴はあるがissued_atがない）
        ContractAssignmentHakenPrint.objects.create(
            tenant_id=self.company.id,
            contract_assignment=assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='テスト就業条件明示書',
            contract_number=staff_contract.contract_number,
        )
        
        # スタッフ契約確認一覧にアクセス
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        # レスポンスの確認
        self.assertEqual(response.status_code, 200)
        confirm_items = response.context['confirm_items']
        
        # 就業条件明示書が表示されていないことを確認
        employment_conditions_items = [
            item for item in confirm_items 
            if item['type'] == 'employment_conditions'
        ]
        self.assertEqual(len(employment_conditions_items), 0)
    
    def test_staff_contract_display(self):
        """スタッフ契約書が表示されることをテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # スタッフ契約を作成（発行済み状態）
        staff_contract = StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='テストスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            contract_number='SC-2025-001',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.staff_pattern,
            job_category=self.job_category,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # スタッフ契約書の発行履歴を作成
        staff_print = StaffContractPrint.objects.create(
            tenant_id=self.company.id,
            staff_contract=staff_contract,
            printed_by=self.user,
            document_title='テストスタッフ契約書',
        )
        
        # スタッフ契約確認一覧にアクセス
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        # レスポンスの確認
        self.assertEqual(response.status_code, 200)
        confirm_items = response.context['confirm_items']
        
        # スタッフ契約書が表示されていることを確認
        staff_contract_items = [
            item for item in confirm_items 
            if item['type'] == 'staff_contract'
        ]
        self.assertEqual(len(staff_contract_items), 1)
        
        # ソート日時が発行履歴の日時になっていることを確認
        item = staff_contract_items[0]
        self.assertEqual(item['sort_date'], staff_print.printed_at)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        pass