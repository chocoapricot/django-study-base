"""
勤怠登録状況管理画面のテスト
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.client.models import Client
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
            name_last_kana='ヤマダ',
            name_first_kana='タロウ',
            tenant_id=self.tenant_id
        )
        
        # スタッフ契約を作成
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            client=self.client_obj,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
            tenant_id=self.tenant_id
        )
        
        # テストクライアントを作成
        self.test_client = Client()

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
