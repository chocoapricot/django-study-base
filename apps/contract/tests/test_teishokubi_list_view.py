from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.staff.models import Staff
from apps.client.models import Client as TestClient
from ..models import StaffContractTeishokubi
import datetime

User = get_user_model()

class StaffContractTeishokubiListViewTest(TestCase):
    """個人抵触日管理一覧ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # The view only requires login, no special permissions needed.


        self.staff1 = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            email='taro.yamada@example.com',
        )
        self.client1 = TestClient.objects.create(
            name='株式会社テスト',
            corporate_number='1234567890123',
            name_furigana='カブシキガイシャテスト',
        )
        self.teishokubi1 = StaffContractTeishokubi.objects.create(
            staff_email=self.staff1.email,
            client_corporate_number=self.client1.corporate_number,
            organization_name='本社',
            dispatch_start_date=datetime.date(2024, 1, 1),
            conflict_date=datetime.date(2027, 1, 1),
        )

        self.staff2 = Staff.objects.create(
            name_last='鈴木',
            name_first='花子',
            email='hanako.suzuki@example.com',
        )
        self.client2 = TestClient.objects.create(
            name='鈴木商事株式会社',
            corporate_number='9876543210987',
            name_furigana='スズキショウジカブシキガイシャ',
        )
        self.teishokubi2 = StaffContractTeishokubi.objects.create(
            staff_email=self.staff2.email,
            client_corporate_number=self.client2.corporate_number,
            organization_name='支社',
            dispatch_start_date=datetime.date(2023, 10, 1),
            conflict_date=datetime.date(2026, 10, 1),
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_teishokubi_list_view_displays_names_and_links(self):
        """一覧にスタッフ名とクライアント名が表示され、リンクが正しいかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Staff 1
        staff1_url = reverse('staff:staff_detail', kwargs={'pk': self.staff1.pk})
        self.assertContains(response, f'<a href="{staff1_url}">{self.staff1.name}</a>')

        # Client 1
        client1_url = reverse('client:client_detail', kwargs={'pk': self.client1.pk})
        self.assertContains(response, f'<a href="{client1_url}">{self.client1.name}</a>')

        # Staff 2
        staff2_url = reverse('staff:staff_detail', kwargs={'pk': self.staff2.pk})
        self.assertContains(response, f'<a href="{staff2_url}">{self.staff2.name}</a>')

        # Client 2
        client2_url = reverse('client:client_detail', kwargs={'pk': self.client2.pk})
        self.assertContains(response, f'<a href="{client2_url}">{self.client2.name}</a>')

    def test_search_by_staff_name(self):
        """スタッフ名で検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '山田'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.staff1.name)
        self.assertNotContains(response, self.staff2.name)

    def test_search_by_client_name(self):
        """クライアント名で検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '鈴木商事'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.staff1.name)
        self.assertContains(response, self.staff2.name)

    def test_search_by_email(self):
        """メールアドレスで検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': 'taro.yamada'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.staff1.name)
        self.assertNotContains(response, self.staff2.name)

    def test_search_by_corporate_number(self):
        """法人番号で検索できるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '9876543210987'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.client1.name)
        self.assertContains(response, self.client2.name)

    def test_no_results_found(self):
        """検索結果がない場合にメッセージが表示されるかテスト"""
        url = reverse('contract:staff_contract_teishokubi_list')
        response = self.client.get(url, {'q': '存在しない名前'})
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
