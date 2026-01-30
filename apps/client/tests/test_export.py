from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.client.models import Client
from apps.company.models import Company
from apps.master.models import ClientRegistStatus

class ClientExportTest(TestCase):
    def setUp(self):
        self.test_client = TestClient()
        self.company = Company.objects.create(name='Test Company', tenant_id=1)
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser',
            password='password',
            tenant_id=1
        )
        # Give permission to view client
        permission = Permission.objects.get(codename='view_client')
        self.user.user_permissions.add(permission)
        self.test_client.login(username='testuser', password='password')

        # セッションにテナントIDを設定
        session = self.test_client.session
        session['current_tenant_id'] = 1
        session.save()

        # テスト用登録区分作成
        self.regist_status = ClientRegistStatus.objects.create(
            name='正社員',
            display_order=1,
            is_active=True,
            tenant_id=1
        )
        
        # Create some client data
        self.client1 = Client.objects.create(
            corporate_number='1234567890123',
            name='株式会社テスト',
            name_furigana='カブシキガイシャテスト',
            address='東京都テスト区',
            tenant_id=1
        )
        self.client2 = Client.objects.create(
            corporate_number='9876543210987',
            name='サンプル商事',
            name_furigana='サンプルショウジ',
            address='大阪府サンプル市',
            regist_status=self.regist_status, # Example filter value
            tenant_id=1
        )

    def test_client_export_csv(self):
        """Test exporting client data as CSV."""
        url = reverse('client:client_export') + '?format=csv'
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

        content = response.content.decode('utf-8')
        self.assertIn('株式会社テスト', content)
        self.assertIn('サンプル商事', content)
        self.assertIn('corporate_number', content) # Check for header

    def test_client_export_excel(self):
        """Test exporting client data as Excel."""
        url = reverse('client:client_export') + '?format=excel'
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_client_export_with_filter(self):
        """Test exporting filtered client data."""
        url = reverse('client:client_export') + '?format=csv&q=テスト'
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertIn('株式会社テスト', content)
        self.assertNotIn('サンプル商事', content)

    def test_client_export_with_regist_status_filter(self):
        """Test exporting with regist_status filter."""
        url = reverse('client:client_export') + f'?format=csv&regist_status={self.regist_status.pk}'
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertNotIn('株式会社テスト', content)
        self.assertIn('サンプル商事', content)
