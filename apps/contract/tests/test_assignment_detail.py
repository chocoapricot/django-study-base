from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.contract.models import ClientContract, StaffContract, ContractAssignment
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import ContractPattern
from apps.common.constants import Constants
from datetime import date

User = get_user_model()


class ContractAssignmentDetailViewTest(TestCase):
    """契約アサイン詳細画面のテストケース"""

    def setUp(self):
        """テストデータのセットアップ"""
        # テストユーザーを作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        all_permissions = []
        content_type_client = ContentType.objects.get_for_model(ClientContract)
        client_permissions = Permission.objects.filter(content_type=content_type_client)
        all_permissions.extend(client_permissions)

        content_type_staff = ContentType.objects.get_for_model(StaffContract)
        staff_permissions = Permission.objects.filter(content_type=content_type_staff)
        all_permissions.extend(staff_permissions)

        content_type_assignment = ContentType.objects.get_for_model(ContractAssignment)
        assignment_permissions = Permission.objects.filter(content_type=content_type_assignment)
        all_permissions.extend(assignment_permissions)
        self.user.user_permissions.set(all_permissions)
        
        # テストクライアント
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123'
        )
        
        # テストスタッフ
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com'
        )
        
        # 契約パターン
        self.client_pattern = ContractPattern.objects.create(
            name='クライアント契約パターン',
            domain=Constants.DOMAIN.CLIENT
        )
        
        self.staff_pattern = ContractPattern.objects.create(
            name='スタッフ契約パターン',
            domain=Constants.DOMAIN.STAFF
        )
        
        # クライアント契約
        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テストクライアント契約',
            contract_pattern=self.client_pattern,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_amount=1000000,
            contract_status=Constants.CONTRACT_STATUS.DRAFT
        )
        
        # スタッフ契約
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_amount=500000,
            contract_status=Constants.CONTRACT_STATUS.DRAFT
        )
        
        # 契約アサイン
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract
        )
        
        # Djangoテストクライアント
        self.test_client = TestClient()

    def test_assignment_detail_view_get(self):
        """アサイン詳細画面のGETリクエストテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストクライアント契約')
        self.assertContains(response, 'テストスタッフ契約')
        self.assertContains(response, 'テストクライアント')
        self.assertContains(response, 'テスト 太郎')
        # スタッフメールアドレスとクライアント法人番号は非表示になったことを確認
        self.assertNotContains(response, 'スタッフメールアドレス')
        self.assertNotContains(response, 'クライアント法人番号')

    def test_assignment_detail_view_context(self):
        """アサイン詳細画面のコンテキストテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.test_client.get(url)
        
        self.assertEqual(response.context['assignment'], self.assignment)
        self.assertEqual(response.context['client_contract'], self.client_contract)
        self.assertEqual(response.context['staff_contract'], self.staff_contract)

    def test_assignment_detail_view_unauthorized(self):
        """未認証ユーザーのアクセステスト"""
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        response = self.test_client.get(url)
        
        # ログインページにリダイレクトされることを確認
        self.assertEqual(response.status_code, 302)

    def test_assignment_detail_view_not_found(self):
        """存在しないアサインIDでのアクセステスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': 99999})
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_assignment_detail_referer_detection(self):
        """リファラー検出のテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        # クライアント契約詳細からのアクセス
        url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': self.assignment.pk})
        client_detail_url = 'http://testserver' + reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract.pk})
        
        response = self.test_client.get(url, HTTP_REFERER=client_detail_url)
        self.assertTrue(response.context['from_client'])
        self.assertFalse(response.context['from_staff'])
        
        # スタッフ契約詳細からのアクセス
        staff_detail_url = 'http://testserver' + reverse('contract:staff_contract_detail', kwargs={'pk': self.staff_contract.pk})
        
        response = self.test_client.get(url, HTTP_REFERER=staff_detail_url)
        self.assertFalse(response.context['from_client'])
        self.assertTrue(response.context['from_staff'])