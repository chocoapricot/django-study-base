from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.contract.models import StaffContract, ContractStaffFlag
from apps.staff.models import Staff
from apps.company.models import CompanyDepartment, CompanyUser, Company
from apps.master.models_other import FlagStatus
from apps.common.middleware import set_current_tenant_id
from apps.master.models import ContractPattern
from apps.common.constants import Constants
import datetime

User = get_user_model()

class ContractStaffFlagTest(TestCase):
    def setUp(self):
        # 会社データの作成
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        # テナントIDをスレッドローカルに設定
        set_current_tenant_id(self.company.tenant_id)

        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password',
            tenant_id=self.company.tenant_id
        )
        self.client.login(email='admin@example.com', password='password')

        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # マスターデータの作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            email='test@example.com',
            tenant_id=self.company.tenant_id
        )

        self.contract_pattern = ContractPattern.objects.create(
            name='Test Pattern',
            domain=Constants.DOMAIN.STAFF,
            is_active=True,
            tenant_id=self.company.tenant_id
        )

        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Test Contract',
            contract_pattern=self.contract_pattern,
            start_date=datetime.date.today(),
            tenant_id=self.company.tenant_id
        )

        self.dept = CompanyDepartment.objects.create(
            name='Test Dept',
            department_code='D001',
            tenant_id=self.company.tenant_id
        )
        self.comp_user = CompanyUser.objects.create(
            name_last='担当',
            name_first='者',
            tenant_id=self.company.tenant_id
        )
        self.status = FlagStatus.objects.create(
            name='Test Status',
            display_order=1,
            tenant_id=self.company.tenant_id
        )

    def test_contract_staff_flag_list_view(self):
        """スタッフ契約フラッグ一覧画面のテスト"""
        response = self.client.get(reverse('contract:staff_contract_flag_list', kwargs={'contract_pk': self.staff_contract.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contract/staff_contract_flag_list.html')

    def test_contract_staff_flag_create_view(self):
        """スタッフ契約フラッグ登録画面のテスト"""
        response = self.client.get(reverse('contract:staff_contract_flag_create', kwargs={'contract_pk': self.staff_contract.pk}))
        self.assertEqual(response.status_code, 200)

        # 登録処理
        data = {
            'staff_contract': self.staff_contract.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        }
        response = self.client.post(reverse('contract:staff_contract_flag_create', kwargs={'contract_pk': self.staff_contract.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ContractStaffFlag.objects.filter(staff_contract=self.staff_contract, flag_status=self.status).exists())

    def test_contract_staff_flag_update_view(self):
        """スタッフ契約フラッグ編集画面のテスト"""
        flag = ContractStaffFlag.objects.create(
            staff_contract=self.staff_contract,
            company_department=self.dept,
            company_user=self.comp_user,
            flag_status=self.status,
            tenant_id=self.company.tenant_id
        )

        # 編集画面
        response = self.client.get(reverse('contract:staff_contract_flag_update', kwargs={'pk': flag.pk}))
        self.assertEqual(response.status_code, 200)

        # 更新処理
        new_status = FlagStatus.objects.create(
            name='New Status',
            display_order=2,
            tenant_id=self.company.tenant_id
        )
        data = {
            'staff_contract': self.staff_contract.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': new_status.pk,
        }
        response = self.client.post(reverse('contract:staff_contract_flag_update', kwargs={'pk': flag.pk}), data)
        self.assertEqual(response.status_code, 302)
        flag.refresh_from_db()
        self.assertEqual(flag.flag_status, new_status)

    def test_contract_staff_flag_delete_view(self):
        """スタッフ契約フラッグ削除画面のテスト"""
        flag = ContractStaffFlag.objects.create(
            staff_contract=self.staff_contract,
            company_department=self.dept,
            company_user=self.comp_user,
            flag_status=self.status,
            tenant_id=self.company.tenant_id
        )

        # 削除確認画面
        response = self.client.get(reverse('contract:staff_contract_flag_delete', kwargs={'pk': flag.pk}))
        self.assertEqual(response.status_code, 200)

        # 削除実行
        response = self.client.post(reverse('contract:staff_contract_flag_delete', kwargs={'pk': flag.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ContractStaffFlag.objects.filter(pk=flag.pk).exists())
