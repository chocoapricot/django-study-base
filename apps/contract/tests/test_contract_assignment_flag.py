from django.test import TestCase, Client
from django.urls import reverse
from apps.contract.models import ClientContract, StaffContract, ContractAssignment, ContractAssignmentFlag
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from apps.master.models import ContractPattern, FlagStatus, EmploymentType
from apps.accounts.models import MyUser
from apps.company.models import Company, CompanyDepartment, CompanyUser
from apps.common.constants import Constants
from datetime import date

class ContractAssignmentFlagTest(TestCase):
    def setUp(self):
        # 会社情報
        self.company = Company.objects.create(name="テスト会社", corporate_number="1234567890123")

        # ユーザー
        self.user = MyUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123',
            tenant_id=self.company.id
        )
        self.client = Client()
        self.client.login(email='admin@example.com', password='password123')

        # セッションにテナントIDを設定
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        # クライアント
        self.client_obj = ClientModel.objects.create(name="テストクライアント", tenant_id=self.company.id)

        # スタッフ
        self.staff_obj = Staff.objects.create(name_last="スタッフ", name_first="太郎", email="staff@example.com", tenant_id=self.company.id)

        # 雇用形態
        self.employment_type = EmploymentType.objects.create(name="正社員", tenant_id=self.company.id)

        # 契約パターン
        self.client_pattern = ContractPattern.objects.create(
            name="クライアントパターン",
            domain=Constants.DOMAIN.CLIENT,
            contract_type_code=Constants.CLIENT_CONTRACT_TYPE.CONTRACT,
            tenant_id=self.company.id
        )
        self.staff_pattern = ContractPattern.objects.create(
            name="スタッフパターン",
            domain=Constants.DOMAIN.STAFF,
            tenant_id=self.company.id
        )

        # クライアント契約
        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name="テストクライアント契約",
            contract_pattern=self.client_pattern,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            tenant_id=self.company.id
        )

        # スタッフ契約
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff_obj,
            contract_name="テストスタッフ契約",
            contract_pattern=self.staff_pattern,
            employment_type=self.employment_type,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            tenant_id=self.company.id
        )

        # 契約アサイン
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            tenant_id=self.company.id
        )

        # マスター等
        self.dept = CompanyDepartment.objects.create(name="テスト部", department_code="D001", tenant_id=self.company.id)
        self.comp_user = CompanyUser.objects.create(
            name_last="担当者",
            name_first="太郎",
            department_code="D001",
            tenant_id=self.company.id
        )
        self.status = FlagStatus.objects.create(name="要確認", tenant_id=self.company.id)

    def test_flag_crud(self):
        # 一覧表示
        response = self.client.get(reverse('contract:contract_assignment_flag_list', args=[self.assignment.pk]))
        self.assertEqual(response.status_code, 200)

        # 作成
        response = self.client.post(reverse('contract:contract_assignment_flag_create', args=[self.assignment.pk]), {
            'contract_assignment': self.assignment.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ContractAssignmentFlag.objects.filter(contract_assignment=self.assignment).exists())

        flag = ContractAssignmentFlag.objects.get(contract_assignment=self.assignment)

        # 更新
        response = self.client.post(reverse('contract:contract_assignment_flag_update', args=[flag.pk]), {
            'contract_assignment': self.assignment.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        })
        self.assertEqual(response.status_code, 302)

        # 削除
        response = self.client.post(reverse('contract:contract_assignment_flag_delete', args=[flag.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ContractAssignmentFlag.objects.filter(pk=flag.pk).exists())

    def test_flag_validation(self):
        # ステータス必須
        response = self.client.post(reverse('contract:contract_assignment_flag_create', args=[self.assignment.pk]), {
            'contract_assignment': self.assignment.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': '',
        })
        self.assertFormError(response.context['form'], 'flag_status', 'このフィールドは必須です。')

        # 担当者入力時の組織必須
        response = self.client.post(reverse('contract:contract_assignment_flag_create', args=[self.assignment.pk]), {
            'contract_assignment': self.assignment.pk,
            'company_department': '',
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        })
        self.assertFormError(response.context['form'], 'company_department', '会社担当者を入力するときは、会社組織を必須にしてください。')

        # 組織不一致
        other_dept = CompanyDepartment.objects.create(name="他部署", department_code="D002", tenant_id=self.company.id)
        response = self.client.post(reverse('contract:contract_assignment_flag_create', args=[self.assignment.pk]), {
            'contract_assignment': self.assignment.pk,
            'company_department': other_dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        })
        self.assertFormError(response.context['form'], 'company_user', '会社組織と、会社担当者の所属する組織が違います。')

    def test_details_save(self):
        # 詳細保存
        response = self.client.post(reverse('contract:contract_assignment_flag_create', args=[self.assignment.pk]), {
            'contract_assignment': self.assignment.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
            'details': 'テスト詳細'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ContractAssignmentFlag.objects.filter(contract_assignment=self.assignment, details='テスト詳細').exists())
