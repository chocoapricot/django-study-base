from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.client.models import Client

class ClientExportTest(TestCase):
    def setUp(self):
        self.test_client = TestClient()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser',
            password='password'
        )
        # Give permission to view client
        permission = Permission.objects.get(codename='view_client')
        self.user.user_permissions.add(permission)
        self.test_client.login(username='testuser', password='password')

        # Create some client data
        self.client1 = Client.objects.create(
            corporate_number='1234567890123',
            name='株式会社テスト',
            name_furigana='カブシキガイシャテスト',
            address='東京都テスト区'
        )
        self.client2 = Client.objects.create(
            corporate_number='9876543210987',
            name='サンプル商事',
            name_furigana='サンプルショウジ',
            address='大阪府サンプル市',
            client_regist_status=1 # Example filter value
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
        """Test exporting with client_regist_status filter."""
        url = reverse('client:client_export') + '?format=csv&client_regist_status=1'
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertNotIn('株式会社テスト', content)
        self.assertIn('サンプル商事', content)
