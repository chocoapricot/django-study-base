from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.contract.models import ClientContract, StaffContract, ContractAssignment
from apps.client.models import Client
from apps.staff.models import Staff, StaffPayroll
from apps.master.models import ContractPattern, EmploymentType
from apps.common.constants import Constants
from datetime import date

User = get_user_model()

class PayrollValidationTest(TestCase):
    def setUp(self):
        self.client_test = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client_test.login(username='testuser', password='testpassword')

        # 権限を付与
        content_type = ContentType.objects.get_for_model(ClientContract)
        permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*permissions)

        staff_content_type = ContentType.objects.get_for_model(StaffContract)
        staff_permissions = Permission.objects.filter(content_type=staff_content_type)
        self.user.user_permissions.add(*staff_permissions)

        # 必要なドロップダウンデータを作成
        from apps.system.settings.models import Dropdowns
        
        # 契約状況のドロップダウン
        Dropdowns.objects.get_or_create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.DRAFT,
            defaults={'name': '作成中', 'active': True, 'disp_seq': 1}
        )
        Dropdowns.objects.get_or_create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.PENDING,
            defaults={'name': '申請', 'active': True, 'disp_seq': 2}
        )
        Dropdowns.objects.get_or_create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.APPROVED,
            defaults={'name': '承認済', 'active': True, 'disp_seq': 3}
        )
        
        # 請求単位のドロップダウン
        Dropdowns.objects.get_or_create(
            category='bill_unit',
            value=Constants.BILL_UNIT.HOURLY_RATE,
            defaults={'name': '時間単価', 'active': True, 'disp_seq': 1}
        )

        # テストデータ作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            basic_contract_date_haken=date(2023, 1, 1)
        )

        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
            hire_date=date(2023, 1, 1),
            employee_no='EMP001'
        )

        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False,
            is_active=True
        )

        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain=Constants.DOMAIN.CLIENT,
            contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            is_active=True
        )

        self.staff_contract_pattern = ContractPattern.objects.create(
            name='スタッフ契約パターン',
            domain=Constants.DOMAIN.STAFF,
            is_active=True
        )
        
        # 就業時間パターン
        from apps.master.models import WorkTimePattern
        self.worktime_pattern = WorkTimePattern.objects.create(name='標準勤務', is_active=True)

        # クライアント契約作成
        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_name='テスト派遣契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),  # 6ヶ月以内に修正
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            worktime_pattern=self.worktime_pattern,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='テストスタッフ契約',
            contract_pattern=self.staff_contract_pattern,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),  # 6ヶ月以内に修正
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            created_by=self.user,
            updated_by=self.user
        )

        # 契約アサイン
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            created_by=self.user,
            updated_by=self.user
        )

        # 派遣情報を作成（派遣契約の場合に必要）
        from apps.contract.models import ClientContractHaken
        from apps.company.models import CompanyUser
        from apps.client.models import ClientUser, ClientDepartment
        
        # 会社ユーザーを作成
        self.company_user = CompanyUser.objects.create(
            name_last='会社',
            name_first='担当者',
            email='company@example.com',
            department_code='001',
            display_order=1
        )
        
        # クライアント部署を作成
        self.client_department = ClientDepartment.objects.create(
            client=self.client_obj,
            name='テスト部署',
            department_code='001'
        )
        
        # クライアントユーザーを作成
        self.client_user = ClientUser.objects.create(
            client=self.client_obj,
            name_last='クライアント',
            name_first='担当者',
            email='client@example.com'
        )
        
        self.haken_info = ClientContractHaken.objects.create(
            client_contract=self.client_contract,
            haken_office=self.client_department,
            haken_unit=self.client_department,
            commander=self.client_user,
            complaint_officer_client=self.client_user,
            responsible_person_client=self.client_user,
            complaint_officer_company=self.company_user,
            responsible_person_company=self.company_user,
            limit_by_agreement=0,
            limit_indefinite_or_senior=0,
            created_by=self.user,
            updated_by=self.user
        )

    def test_client_contract_pending_without_payroll_error(self):
        """派遣契約を申請状態にする際、給与関連情報が未登録の場合エラーになることをテスト"""
        data = {
            'client': self.client_obj.pk,
            'client_contract_type_code': Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            'contract_name': 'テスト派遣契約',
            'contract_pattern': self.contract_pattern.pk,
            'start_date': '2024-01-01',
            'end_date': '2024-06-30',  # 6ヶ月以内に修正
            'contract_status': Constants.CONTRACT_STATUS.PENDING,  # 申請状態
            'bill_unit': Constants.BILL_UNIT.HOURLY_RATE,  # 時間単価
            'contract_amount': '2000',
            'worktime_pattern': self.worktime_pattern.pk,
            # 派遣情報フィールド（有効な値を設定）
            'haken_office': str(self.client_department.pk),
            'haken_unit': str(self.client_department.pk),
            'commander': str(self.client_user.pk),
            'complaint_officer_client': str(self.client_user.pk),
            'responsible_person_client': str(self.client_user.pk),
            'complaint_officer_company': str(self.company_user.pk),
            'responsible_person_company': str(self.company_user.pk),
            'limit_by_agreement': '0',
            'limit_indefinite_or_senior': '0',
        }
        
        response = self.client_test.post(
            reverse('contract:client_contract_update', args=[self.client_contract.pk]), 
            data
        )
        
        # フォームエラーで再表示される
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '派遣契約を申請するには、割当されたスタッフの給与関連情報が必要です')
        self.assertContains(response, '山田 太郎')

    def test_client_contract_pending_with_payroll_success(self):
        """派遣契約を申請状態にする際、給与関連情報が登録済みの場合成功することをテスト"""
        # 給与関連情報を登録
        StaffPayroll.objects.create(
            staff=self.staff,
            health_insurance_join_date=date(2024, 1, 1),
            pension_insurance_non_enrollment_reason='年金制度対象外',
            employment_insurance_join_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )

        data = {
            'client': self.client_obj.pk,
            'client_contract_type_code': Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            'contract_name': 'テスト派遣契約',
            'contract_pattern': self.contract_pattern.pk,
            'start_date': '2024-01-01',
            'end_date': '2024-06-30',  # 6ヶ月以内に修正
            'contract_status': Constants.CONTRACT_STATUS.PENDING,  # 申請状態
            'bill_unit': Constants.BILL_UNIT.HOURLY_RATE,  # 時間単価
            'contract_amount': '2000',
            'worktime_pattern': self.worktime_pattern.pk,
            # 派遣情報フィールド（有効な値を設定）
            'haken_office': str(self.client_department.pk),
            'haken_unit': str(self.client_department.pk),
            'commander': str(self.client_user.pk),
            'complaint_officer_client': str(self.client_user.pk),
            'responsible_person_client': str(self.client_user.pk),
            'complaint_officer_company': str(self.company_user.pk),
            'responsible_person_company': str(self.company_user.pk),
            'limit_by_agreement': '0',
            'limit_indefinite_or_senior': '0',
        }
        
        response = self.client_test.post(
            reverse('contract:client_contract_update', args=[self.client_contract.pk]), 
            data
        )
        
        # 成功してリダイレクト
        self.assertEqual(response.status_code, 302)
        
        # 契約状況が更新されていることを確認
        self.client_contract.refresh_from_db()
        self.assertEqual(self.client_contract.contract_status, Constants.CONTRACT_STATUS.PENDING)

    def test_client_contract_approve_without_payroll_error(self):
        """派遣契約を承認する際、給与関連情報が未登録の場合エラーになることをテスト"""
        # 契約を申請状態にする（給与情報チェックを回避するため直接更新）
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.PENDING
        self.client_contract.save()

        response = self.client_test.post(
            reverse('contract:client_contract_approve', args=[self.client_contract.pk]),
            {'is_approved': 'true'}
        )
        
        # エラーメッセージが表示されてリダイレクト
        self.assertEqual(response.status_code, 302)
        
        # 契約状況が変更されていないことを確認
        self.client_contract.refresh_from_db()
        self.assertEqual(self.client_contract.contract_status, Constants.CONTRACT_STATUS.PENDING)

    def test_client_contract_approve_with_payroll_success(self):
        """派遣契約を承認する際、給与関連情報が登録済みの場合成功することをテスト"""
        # 給与関連情報を登録
        StaffPayroll.objects.create(
            staff=self.staff,
            health_insurance_join_date=date(2024, 1, 1),
            pension_insurance_non_enrollment_reason='年金制度対象外',
            employment_insurance_join_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )

        # 契約を申請状態にする
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.PENDING
        self.client_contract.save()

        response = self.client_test.post(
            reverse('contract:client_contract_approve', args=[self.client_contract.pk]),
            {'is_approved': 'true'}
        )
        
        # 成功してリダイレクト
        self.assertEqual(response.status_code, 302)
        
        # 契約状況が承認済みに更新されていることを確認
        self.client_contract.refresh_from_db()
        self.assertEqual(self.client_contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)

    def test_non_dispatch_contract_no_payroll_check(self):
        """派遣以外の契約では給与関連情報チェックが行われないことをテスト"""
        # 業務委託契約パターンを作成
        outsourcing_pattern = ContractPattern.objects.create(
            name='業務委託契約パターン',
            domain=Constants.DOMAIN.CLIENT,
            contract_type_code='10',  # 派遣以外
            is_active=True
        )

        # 業務委託契約を作成
        outsourcing_contract = ClientContract.objects.create(
            client=self.client_obj,
            client_contract_type_code='10',  # 派遣以外
            contract_name='テスト業務委託契約',
            contract_pattern=outsourcing_pattern,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            worktime_pattern=self.worktime_pattern,
            created_by=self.user,
            updated_by=self.user
        )

        data = {
            'client': self.client_obj.pk,
            'client_contract_type_code': '10',  # 派遣以外
            'contract_name': 'テスト業務委託契約',
            'contract_pattern': outsourcing_pattern.pk,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',  # 派遣以外なので12ヶ月でも問題なし
            'contract_status': Constants.CONTRACT_STATUS.PENDING,  # 申請状態
            'bill_unit': Constants.BILL_UNIT.HOURLY_RATE,  # 時間単価
            'contract_amount': '2000',
            'worktime_pattern': self.worktime_pattern.pk,
        }
        
        response = self.client_test.post(
            reverse('contract:client_contract_update', args=[outsourcing_contract.pk]), 
            data
        )
        
        # 給与関連情報チェックが行われず、成功してリダイレクト
        self.assertEqual(response.status_code, 302)
        
        # 契約状況が更新されていることを確認
        outsourcing_contract.refresh_from_db()
        self.assertEqual(outsourcing_contract.contract_status, Constants.CONTRACT_STATUS.PENDING)