from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import patch

from apps.common.constants import Constants
from apps.contract.models import (
    StaffContract, ClientContract, ContractAssignment, 
    ContractAssignmentHakenPrint, ClientContractHaken
)
from apps.staff.models import Staff
from apps.client.models import Client, ClientDepartment
from apps.master.models import EmploymentType, ContractPattern, JobCategory
from apps.company.models import Company

User = get_user_model()


class StaffContractEmploymentConditionsIssueTest(TestCase):
    """スタッフ契約の状況カードからの就業条件明示書発行テスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 権限を付与
        from django.contrib.auth.models import Permission
        change_permission = Permission.objects.get(codename='change_staffcontract')
        view_permission = Permission.objects.get(codename='view_staffcontract')
        self.user.user_permissions.add(change_permission, view_permission)
        
        self.test_client = TestClient()
        self.test_client.force_login(self.user)

        # 会社作成
        self.company = Company.objects.create(
            name='テスト会社',
            corporate_number='1234567890123'
        )

        # 雇用形態作成（有期雇用）
        self.employment_type_fixed = EmploymentType.objects.create(
            name='有期雇用',
            is_fixed_term=True,
            is_active=True
        )

        # 雇用形態作成（無期雇用）
        self.employment_type_indefinite = EmploymentType.objects.create(
            name='無期雇用',
            is_fixed_term=False,
            is_active=True
        )

        # 契約パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain=Constants.DOMAIN.STAFF,
            is_active=True
        )

        # 職種作成
        self.job_category = JobCategory.objects.create(
            name='テスト職種',
            is_active=True
        )

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            email='staff@example.com',
            employment_type=self.employment_type_fixed
        )

        # クライアント作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='9876543210987'
        )

        # クライアント部署作成
        self.client_department = ClientDepartment.objects.create(
            client=self.client_obj,
            name='テスト部署',
            postal_code='1000001',
            address='東京都千代田区千代田1-1'
        )

        # スタッフ契約作成（有期雇用）
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type_fixed,
            contract_name='テストスタッフ契約',
            contract_pattern=self.contract_pattern,
            job_category=self.job_category,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            contract_amount=2000,
            pay_unit=Constants.PAY_UNIT.HOURLY,
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            contract_number='S2024001',
            created_by=self.user,
            updated_by=self.user
        )

        # クライアント契約作成（派遣）
        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_name='テストクライアント契約',
            contract_pattern=self.contract_pattern,
            job_category=self.job_category,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            contract_amount=3000,
            bill_unit=Constants.BILL_UNIT.HOURLY_RATE,
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            contract_number='C2024001',
            created_by=self.user,
            updated_by=self.user
        )

        # 派遣情報作成
        self.haken_info = ClientContractHaken.objects.create(
            client_contract=self.client_contract,
            haken_office=self.client_department,
            created_by=self.user,
            updated_by=self.user
        )

        # 契約アサイン作成
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            created_by=self.user,
            updated_by=self.user
        )

    @patch('apps.contract.utils.generate_employment_conditions_pdf')
    def test_employment_conditions_issue_success(self, mock_pdf_gen):
        """有期雇用かつ派遣契約の場合、就業条件明示書発行が成功することをテスト"""
        # PDF生成をモック
        mock_pdf_gen.return_value = b'fake pdf content'
        
        url = reverse('contract:staff_contract_assignment_employment_conditions_issue', 
                     kwargs={'contract_pk': self.staff_contract.pk, 'assignment_pk': self.assignment.pk})
        
        response = self.test_client.get(url)
        
        # 発行が成功し、スタッフ契約詳細画面にリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:staff_contract_detail', kwargs={'pk': self.staff_contract.pk}))
        
        # 発行履歴が作成されることを確認
        print_history = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        ).first()
        self.assertIsNotNone(print_history)
        self.assertEqual(print_history.contract_number, 'S2024001')
        self.assertEqual(print_history.printed_by, self.user)

        # アサインの発行日時が設定されることを確認
        self.assignment.refresh_from_db()
        self.assertIsNotNone(self.assignment.issued_at)

    def test_employment_conditions_issue_indefinite_employment_error(self):
        """無期雇用の場合はエラーになることをテスト"""
        # スタッフ契約を無期雇用に変更
        self.staff_contract.employment_type = self.employment_type_indefinite
        self.staff_contract.save()

        url = reverse('contract:staff_contract_assignment_employment_conditions_issue', 
                     kwargs={'contract_pk': self.staff_contract.pk, 'assignment_pk': self.assignment.pk})
        
        response = self.test_client.get(url)
        
        # エラーメッセージが表示され、スタッフ契約詳細画面にリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:staff_contract_detail', kwargs={'pk': self.staff_contract.pk}))
        
        # 発行履歴が作成されないことを確認
        print_history_count = ContractAssignmentHakenPrint.objects.filter(
            contract_assignment=self.assignment,
            print_type=ContractAssignmentHakenPrint.PrintType.EMPLOYMENT_CONDITIONS
        ).count()
        self.assertEqual(print_history_count, 0)

    def test_employment_conditions_issue_unauthorized(self):
        """未認証ユーザーのアクセステスト"""
        self.test_client.logout()
        
        url = reverse('contract:staff_contract_assignment_employment_conditions_issue', 
                     kwargs={'contract_pk': self.staff_contract.pk, 'assignment_pk': self.assignment.pk})
        
        response = self.test_client.get(url)
        
        # ログインページにリダイレクトされることを確認
        self.assertRedirects(response, f'/accounts/login/?next={url}')