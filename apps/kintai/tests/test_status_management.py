"""
勤怠登録状況管理画面のテスト
"""
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.contract.models import StaffContract, ContractAssignment
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company
from apps.master.models import ContractPattern
from apps.common.constants import Constants
from datetime import date

User = get_user_model()


class KintaiStatusManagementTest(TestCase):
    """勤怠登録状況管理画面のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        # テナントIDを設定
        self.tenant_id = 1
        
        # テストユーザーを作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            tenant_id=self.tenant_id
        )
        
        # 必要な権限を付与
        permission = Permission.objects.get(
            codename='view_stafftimesheet',
            content_type__app_label='kintai'
        )
        self.user.user_permissions.add(permission)

        # 会社（テナント）を作成
        self.company = Company.objects.create(
            name='テスト会社',
            tenant_id=self.tenant_id
        )

        # 契約書パターンを作成
        self.pattern = ContractPattern.objects.create(
            name='テストパターン',
            domain=Constants.DOMAIN.STAFF,
            tenant_id=self.tenant_id
        )
        
        # クライアントを作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            tenant_id=self.tenant_id
        )
        
        # スタッフを作成
        self.staff = Staff.objects.create(
            employee_no='001',
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            tenant_id=self.tenant_id
        )
        
        # スタッフ契約を作成
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
            contract_name='テスト契約',
            contract_pattern=self.pattern,
            tenant_id=self.tenant_id
        )
        
        # テストクライアントを作成
        self.test_client = TestClient()

    def test_kintai_status_management_access(self):
        """勤怠登録状況管理画面にアクセスできることを確認"""
        self.test_client.login(username='testuser', password='testpass123')
        response = self.test_client.get(reverse('kintai:kintai_status_management'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/kintai_status_management.html')

    def test_kintai_status_management_without_permission(self):
        """権限がない場合はアクセスできないことを確認"""
        # 権限を削除
        self.user.user_permissions.clear()
        self.test_client.login(username='testuser', password='testpass123')
        response = self.test_client.get(reverse('kintai:kintai_status_management'))
        # 権限がない場合は403または302（リダイレクト）が返される
        self.assertIn(response.status_code, [302, 403])

    def test_kintai_status_management_contract_display(self):
        """契約が表示されることを確認"""
        self.test_client.login(username='testuser', password='testpass123')
        response = self.test_client.get(reverse('kintai:kintai_status_management'))
        self.assertEqual(response.status_code, 200)
        
        # コンテキストに契約リストが含まれることを確認
        self.assertIn('contract_status_list', response.context)
        contract_list = response.context['contract_status_list']
        
        # 作成した契約が含まれることを確認
        self.assertEqual(len(contract_list), 1)
        self.assertEqual(contract_list[0]['contract'], self.contract)

    def test_kintai_status_management_with_target_month(self):
        """対象年月を指定してアクセスできることを確認"""
        self.test_client.login(username='testuser', password='testpass123')
        response = self.test_client.get(
            reverse('kintai:kintai_status_management'),
            {'target_month': '2026-02'}
        )
        self.assertEqual(response.status_code, 200)
        
        # コンテキストに正しい年月が設定されることを確認
        self.assertEqual(response.context['year'], 2026)
        self.assertEqual(response.context['month'], 2)

    def test_kintai_status_management_issued_contract(self):
        """発行済の契約も表示されることを確認"""
        StaffContract.objects.create(
            staff=self.staff,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            contract_name='発行済契約',
            contract_pattern=self.pattern,
            tenant_id=self.tenant_id
        )
        self.test_client.login(username='testuser', password='testpass123')
        response = self.test_client.get(reverse('kintai:kintai_status_management'), {'target_month': '2026-01'})
        contract_list = response.context['contract_status_list']
        # setUpで作った分と合わせて2件
        self.assertEqual(len(contract_list), 2)

    def test_kintai_status_management_unregistered_attendance(self):
        """未登録の勤怠（アサインあり、タイムシートなし）が表示されることを確認"""
        # アサインメントを作成
        client_contract = Client.objects.create(name='別のクライアント', tenant_id=self.tenant_id)
        # 実際にはClientContractモデルを使う必要があるが、ここでは簡易的に
        from apps.contract.models import ClientContract
        cc = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='クライアント契約',
            contract_pattern=self.pattern, # 本来は別のパターンだがテスト用
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            tenant_id=self.tenant_id
        )

        ContractAssignment.objects.create(
            staff_contract=self.contract,
            client_contract=cc,
            assignment_start_date=date(2026, 1, 1),
            assignment_end_date=date(2026, 12, 31),
            tenant_id=self.tenant_id
        )

        self.test_client.login(username='testuser', password='testpass123')
        response = self.test_client.get(reverse('kintai:kintai_status_management'), {'target_month': '2026-01'})

        self.assertContains(response, '未作成')

        contract_list = response.context['contract_status_list']
        client_ts_list = contract_list[0]['client_timesheet_list']
        self.assertEqual(len(client_ts_list), 1)
        self.assertFalse(client_ts_list[0]['is_created'])
        self.assertEqual(client_ts_list[0]['status_display'], '未作成')
