from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.staff.models import Staff
from apps.client.models import Client as TestClient
from apps.company.models import Company
from ..models import StaffContractTeishokubi
import datetime

User = get_user_model()

class StaffContractTeishokubiListViewTest(TestCase):
    """個人抵触日管理一覧ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        self.company = Company.objects.create(name='Test Company', tenant_id=1)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            tenant_id=1
        )

        # The view only requires login, no special permissions needed.


        self.staff1 = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            email='taro.yamada@example.com',
            tenant_id=1
        )
        self.client1 = TestClient.objects.create(
            name='株式会社テスト',
            corporate_number='1234567890123',
            name_furigana='カブシキガイシャテスト',
            tenant_id=1
        )
        self.teishokubi1 = StaffContractTeishokubi.objects.create(
            staff_email=self.staff1.email,
            client_corporate_number=self.client1.corporate_number,
            organization_name='本社',
            dispatch_start_date=datetime.date(2024, 1, 1),
            conflict_date=datetime.date(2027, 1, 1),
            tenant_id=1
        )

        self.staff2 = Staff.objects.create(
            name_last='鈴木',
            name_first='花子',
            email='hanako.suzuki@example.com',
            tenant_id=1
        )
        self.client2 = TestClient.objects.create(
            name='鈴木商事株式会社',
            corporate_number='9876543210987',
            name_furigana='スズキショウジカブシキガイシャ',
            tenant_id=1
        )
        self.teishokubi2 = StaffContractTeishokubi.objects.create(
            staff_email=self.staff2.email,
            client_corporate_number=self.client2.corporate_number,
            organization_name='支社',
            dispatch_start_date=datetime.date(2023, 10, 1),
            conflict_date=datetime.date(2026, 10, 1),
            tenant_id=1
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # セッションにテナントIDを設定
        session = self.client.session
        session['current_tenant_id'] = 1
        session.save()

    def test_teishokubi_list_view_displays_names_and_links(self):
        """一覧にスタッフ名とクライアント名が表示され、詳細リンクが正しいかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'dispatch_filter': 'all'})
        self.assertEqual(response.status_code, 200)

        # スタッフ名が表示されることを確認
        self.assertContains(response, self.staff1.name)
        self.assertContains(response, self.staff2.name)

        # クライアント名が表示されることを確認
        self.assertContains(response, self.client1.name)
        self.assertContains(response, self.client2.name)

        # 組織名が表示されることを確認
        self.assertContains(response, self.teishokubi1.organization_name)
        self.assertContains(response, self.teishokubi2.organization_name)

        # 詳細ページへのリンクが存在することを確認（組織名と抵触日の両方にリンク）
        teishokubi1_detail_url = reverse('contract:staff_contract_teishokubi_detail', kwargs={'pk': self.teishokubi1.pk})
        teishokubi2_detail_url = reverse('contract:staff_contract_teishokubi_detail', kwargs={'pk': self.teishokubi2.pk})
        # 各レコードに対して2つのリンクがあることを確認（組織名と抵触日）
        self.assertContains(response, f'href="{teishokubi1_detail_url}"', count=2)  # 組織名、抵触日
        self.assertContains(response, f'href="{teishokubi2_detail_url}"', count=2)  # 組織名、抵触日

    def test_search_by_staff_name(self):
        """スタッフ名で検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '山田', 'dispatch_filter': 'all'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.staff1.name)
        self.assertNotContains(response, self.staff2.name)

    def test_search_by_client_name(self):
        """クライアント名で検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '鈴木商事', 'dispatch_filter': 'all'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.staff1.name)
        self.assertContains(response, self.staff2.name)

    def test_search_by_email(self):
        """メールアドレスで検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': 'taro.yamada', 'dispatch_filter': 'all'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.staff1.name)
        self.assertNotContains(response, self.staff2.name)

    def test_search_by_corporate_number(self):
        """法人番号で検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '9876543210987', 'dispatch_filter': 'all'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.client1.name)
        self.assertContains(response, self.client2.name)

    def test_no_results_found(self):
        """検索結果がない場合にメッセージが表示されるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '存在しない名前', 'dispatch_filter': 'all'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'データがありません。')

    def test_teishokubi_detail_view(self):
        """詳細ビューが正しく表示されるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_detail', kwargs={'pk': self.teishokubi1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.staff1.name)
        self.assertContains(response, self.client1.name)
        self.assertContains(response, self.teishokubi1.organization_name)
