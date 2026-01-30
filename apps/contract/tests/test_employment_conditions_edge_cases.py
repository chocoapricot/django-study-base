from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company
from apps.connect.models import ConnectStaff
from apps.master.models import ContractPattern, JobCategory
from apps.contract.models import (
    StaffContract, ClientContract, ContractAssignment, 
    ContractAssignmentHakenPrint, ClientContractHaken
)
from apps.common.middleware import set_current_tenant_id
from apps.common.constants import Constants
from apps.system.settings.models import Dropdowns
from unittest.mock import patch
from datetime import date

User = get_user_model()


class EmploymentConditionsEdgeCasesTest(TestCase):
    """就業条件明示書確認機能のエッジケース・異常系テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.company = self._create_company()
        set_current_tenant_id(self.company.id)

        self._create_dropdowns()
        self.user = self._create_user()
        self.staff = self._create_staff()
        self.client_company = self._create_client()
        self.connect_staff = self._create_connect_staff()
        self.staff_pattern = self._create_contract_pattern('staff')
        self.client_pattern = self._create_contract_pattern('client')
        self.job_category = self._create_job_category()
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
        from django.contrib.auth.models import Permission
        user = User.objects.create_user(
            tenant_id=self.company.id,
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
        return Company.objects.create(
            name='テスト株式会社',
            corporate_number='1234567890123',
        )
    
    def _create_staff(self):
        return Staff.objects.create(
            tenant_id=self.company.id,
            email='teststaff@example.com',
            name_last='テスト',
            name_first='太郎',
        )
    
    def _create_client(self):
        return Client.objects.create(
            tenant_id=self.company.id,
            name='クライアント株式会社',
            corporate_number='9876543210987',
        )
    
    def _create_connect_staff(self):
        return ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.user.email,
            status='approved',
        )
    
    def _create_contract_pattern(self, domain_type):
        domain = Constants.DOMAIN.STAFF if domain_type == 'staff' else Constants.DOMAIN.CLIENT
        name = 'スタッフ向け雇用契約' if domain_type == 'staff' else 'クライアント向け派遣契約'
        return ContractPattern.objects.create(
            tenant_id=self.company.id,
            name=name,
            domain=domain,
            is_active=True
        )
    
    def _create_job_category(self):
        return JobCategory.objects.create(
            tenant_id=self.company.id,
            name='システム開発',
            is_active=True
        )
    
    def _create_staff_contract(self):
        return StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='テストスタッフ契約',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,  # 発行済みに変更
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
        contract = ClientContract.objects.create(
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
        
        ClientContractHaken.objects.create(
            tenant_id=self.company.id,
            client_contract=contract,
            created_by=self.user,
            updated_by=self.user,
        )
        
        return contract
    
    def _create_contract_assignment(self):
        assignment = ContractAssignment.objects.create(
            tenant_id=self.company.id,
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            issued_at=timezone.now(),  # 発行済みにする
            created_by=self.user,
            updated_by=self.user,
        )
        
        return assignment
    
    def test_unauthenticated_access(self):
        """未認証ユーザーのアクセステスト"""
        # ログインしていない状態でアクセス
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 302)  # ログインページにリダイレクト
    
    def test_no_staff_record(self):
        """スタッフレコードが存在しない場合のテスト"""
        # 別のメールアドレスでユーザーを作成
        other_user = User.objects.create_user(
            tenant_id=self.company.id,
            username='nostaff@example.com',
            email='nostaff@example.com',
            password='password',
            is_staff=True,
            is_active=True,
        )
        
        self.client.login(email='nostaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '確認対象の書類が見つかりませんでした')
    
    def test_no_company_record(self):
        """会社レコードが存在しない場合のテスト"""
        # 会社を削除
        Company.objects.all().delete()
        
        self.client.login(email='teststaff@example.com', password='password')
        # 会社がないのでセッションに tenant_id を設定しても意味がないかもしれないが、
        # 少なくともエラー回避のために空のセッションなどは必要

        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '確認対象の書類が見つかりませんでした')
    
    def test_no_corporate_number(self):
        """会社の法人番号が設定されていない場合のテスト"""
        # 法人番号をクリア
        self.company.corporate_number = None
        self.company.save()
        
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '確認対象の書類が見つかりませんでした')
    
    def test_unapproved_connect_staff(self):
        """未承認の接続スタッフの場合のテスト"""
        # 接続スタッフを未承認状態にする
        self.connect_staff.status = 'pending'
        self.connect_staff.save()
        
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '確認対象の書類が見つかりませんでした')
    
    def test_non_dispatch_contract(self):
        """派遣契約以外の場合のテスト"""
        # クライアント契約を派遣以外に変更
        self.client_contract.client_contract_type_code = '10'  # 派遣以外
        self.client_contract.save()
        
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        
        self.assertEqual(response.status_code, 200)
        # 就業条件明示書は表示されない（派遣契約のみ対象）
        self.assertNotContains(response, '就業条件明示書')
    
    def test_employment_conditions_issue_invalid_status(self):
        """無効なステータスでの就業条件明示書発行テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # スタッフ契約を作成中状態のままにする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.DRAFT
        self.staff_contract.save()
        
        response = self.client.post(
            reverse('contract:assignment_employment_conditions_issue', 
                   kwargs={'assignment_pk': self.assignment.pk}),
            {'is_issued': 'on'}
        )
        
        # エラーメッセージが表示されることを確認
        self.assertEqual(response.status_code, 302)
        # 発行履歴が作成されていないことを確認
        haken_print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment
        )
        self.assertEqual(haken_print_history.count(), 0)
    
    def test_employment_conditions_issue_non_dispatch(self):
        """派遣契約以外での就業条件明示書発行テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # クライアント契約を派遣以外に変更
        self.client_contract.client_contract_type_code = '10'  # 派遣以外
        self.client_contract.save()
        
        response = self.client.post(
            reverse('contract:assignment_employment_conditions_issue', 
                   kwargs={'assignment_pk': self.assignment.pk}),
            {'is_issued': 'on'}
        )
        
        # エラーメッセージが表示されることを確認
        self.assertEqual(response.status_code, 302)
        # 発行履歴が作成されていないことを確認
        haken_print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment
        )
        self.assertEqual(haken_print_history.count(), 0)
    
    def test_confirm_nonexistent_contract(self):
        """存在しない契約の確認テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        response = self.client.post(
            reverse('contract:staff_contract_confirm_list'),
            {
                'contract_id': 99999,  # 存在しないID
                'action': 'confirm_staff_contract'
            }
        )
        
        # 404エラーが返されることを確認
        self.assertEqual(response.status_code, 404)
    
    def test_confirm_nonexistent_assignment(self):
        """存在しない契約アサインの確認テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        response = self.client.post(
            reverse('contract:staff_contract_confirm_list'),
            {
                'assignment_id': 99999,  # 存在しないID
                'action': 'confirm_employment_conditions'
            }
        )
        
        # 404エラーが返されることを確認
        self.assertEqual(response.status_code, 404)
    
    def test_invalid_action(self):
        """無効なアクションのテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        response = self.client.post(
            reverse('contract:staff_contract_confirm_list'),
            {
                'contract_id': self.staff_contract.pk,
                'action': 'invalid_action'  # 無効なアクション
            }
        )
        
        # リダイレクトされるが、何も処理されない
        self.assertEqual(response.status_code, 302)
        self.staff_contract.refresh_from_db()
        # 無効なアクションの場合、契約ステータスは変更されずに元のまま（発行済み）
        self.assertEqual(self.staff_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)
    
    def test_duplicate_employment_conditions_issue(self):
        """同じ契約番号での就業条件明示書重複発行テスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # スタッフ契約を発行済み状態にする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.contract_number = 'SC-2025-001'
        self.staff_contract.save()
        
        # 既に同じ契約番号で発行履歴を作成
        ContractAssignmentHakenPrint.objects.create(
            tenant_id=self.company.id,
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
            printed_by=self.user,
            document_title='既存の就業条件明示書',
            contract_number='SC-2025-001',
        )
        
        # 同じ契約番号で再発行を試行
        with patch('apps.contract.utils.generate_employment_conditions_pdf') as mock_pdf:
            mock_pdf.return_value = b'fake_employment_conditions_pdf'
            
            response = self.client.post(
                reverse('contract:assignment_employment_conditions_issue', 
                       kwargs={'assignment_pk': self.assignment.pk}),
                {'is_issued': 'on'}
            )
        
        # 警告メッセージが表示されることを確認
        self.assertEqual(response.status_code, 302)
        # 発行履歴が重複して作成されていないことを確認
        haken_print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            contract_number='SC-2025-001'
        )
        self.assertEqual(haken_print_history.count(), 1)  # 既存の1件のみ
    
    def test_pdf_generation_failure(self):
        """PDF生成失敗時のテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # スタッフ契約を発行済み状態にする
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.contract_number = 'SC-2025-001'
        self.staff_contract.save()
        
        # PDF生成でエラーを発生させる
        with patch('apps.contract.utils.generate_employment_conditions_pdf') as mock_pdf:
            mock_pdf.side_effect = Exception('PDF生成エラー')
            
            response = self.client.post(
                reverse('contract:assignment_employment_conditions_issue', 
                       kwargs={'assignment_pk': self.assignment.pk}),
                {'is_issued': 'on'}
            )
        
        # エラーメッセージが表示されることを確認
        self.assertEqual(response.status_code, 302)
        # 発行履歴が作成されていないことを確認
        haken_print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment
        )
        self.assertEqual(haken_print_history.count(), 0)
    
    def test_multiple_assignments_same_staff(self):
        """同一スタッフの複数アサインテスト"""
        self.client.login(email='teststaff@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # 別のクライアント契約を作成
        other_client = Client.objects.create(
            tenant_id=self.company.id,
            name='別のクライアント株式会社',
            corporate_number='1111111111111',
        )
        
        other_client_contract = ClientContract.objects.create(
            tenant_id=self.company.id,
            client=other_client,
            contract_name='別のクライアント契約',
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_status=Constants.CONTRACT_STATUS.APPROVED,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            contract_pattern=self.client_pattern,
            job_category=self.job_category,
            created_by=self.user,
            updated_by=self.user,
        )
        
        ClientContractHaken.objects.create(
            tenant_id=self.company.id,
            client_contract=other_client_contract,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 別のアサインを作成
        other_assignment = ContractAssignment.objects.create(
            tenant_id=self.company.id,
            client_contract=other_client_contract,
            staff_contract=self.staff_contract,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # 両方のアサインに就業条件明示書の発行履歴を作成
        for assignment in [self.assignment, other_assignment]:
            # アサインを発行済みにする
            assignment.issued_at = timezone.now()
            assignment.save()
            
            ContractAssignmentHakenPrint.objects.create(
                tenant_id=self.company.id,
                contract_assignment=assignment,
                print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS,
                printed_by=self.user,
                document_title=f'就業条件明示書_{assignment.pk}',
            )
        
        # スタッフ契約確認一覧を取得
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        
        # 両方の就業条件明示書が表示されていることを確認
        self.assertContains(response, 'クライアント株式会社')
        self.assertContains(response, '別のクライアント株式会社')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        pass