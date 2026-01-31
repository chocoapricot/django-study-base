from django.test import TestCase, Client
from django.urls import reverse
from apps.contract.models import ClientContract, ContractClientFlag
from apps.client.models import Client as ClientModel
from apps.master.models import ContractPattern, FlagStatus
from apps.accounts.models import MyUser
from apps.company.models import Company, CompanyDepartment, CompanyUser
from apps.common.constants import Constants
from datetime import date

class ContractClientFlagTest(TestCase):
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

        # 契約パターン
        self.pattern = ContractPattern.objects.create(
            name="テストパターン",
            domain=Constants.DOMAIN.CLIENT,
            contract_type_code=Constants.CLIENT_CONTRACT_TYPE.CONTRACT,
            tenant_id=self.company.id
        )

        # クライアント契約
        self.contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name="テスト契約",
            contract_pattern=self.pattern,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            tenant_id=self.company.id
        )

        # マスター等
        self.dept = CompanyDepartment.objects.create(name="テスト部", department_code="D001", tenant_id=self.company.id)
        self.comp_user = CompanyUser.objects.create(name_last="担当者", name_first="太郎", tenant_id=self.company.id)
        self.status = FlagStatus.objects.create(name="要確認", tenant_id=self.company.id)

    def test_flag_crud(self):
        # 一覧表示
        response = self.client.get(reverse('contract:client_contract_flag_list', args=[self.contract.pk]))
        self.assertEqual(response.status_code, 200)

        # 作成
        response = self.client.post(reverse('contract:client_contract_flag_create', args=[self.contract.pk]), {
            'client_contract': self.contract.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ContractClientFlag.objects.filter(client_contract=self.contract).exists())

        flag = ContractClientFlag.objects.get(client_contract=self.contract)

        # 更新
        response = self.client.post(reverse('contract:client_contract_flag_update', args=[flag.pk]), {
            'client_contract': self.contract.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        })
        self.assertEqual(response.status_code, 302)

        # 削除
        response = self.client.post(reverse('contract:client_contract_flag_delete', args=[flag.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ContractClientFlag.objects.filter(pk=flag.pk).exists())
