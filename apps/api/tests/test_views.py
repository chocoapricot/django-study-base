from django.test import TestCase, Client as TestClient
from django.urls import reverse
from apps.accounts.models import MyUser
from apps.client.models import Client, ClientUser, ClientDepartment
from apps.company.models import Company

class ApiViewsTest(TestCase):
    def setUp(self):
        """テストデータのセットアップ"""
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        self.user = MyUser.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password123',
            tenant_id=self.company.tenant_id
        )
        self.client = TestClient()
        self.client.login(email='testuser@example.com', password='password123')
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        self.test_client1 = Client.objects.create(name='Test Client 1', corporate_number='1111111111111', tenant_id=self.company.tenant_id)
        department = ClientDepartment.objects.create(client=self.test_client1, name='Test Department', tenant_id=self.company.tenant_id)
        self.client_user1 = ClientUser.objects.create(client=self.test_client1, department=department, position='Manager', name_last='User', name_first='1', tenant_id=self.company.tenant_id)
        self.client_user2 = ClientUser.objects.create(client=self.test_client1, name_last='User', name_first='2', tenant_id=self.company.tenant_id)

        self.test_client2 = Client.objects.create(name='Test Client 2', corporate_number='2222222222222', tenant_id=self.company.tenant_id)

    def test_get_client_users_success(self):
        """クライアントに紐づくユーザーが正しく返されることを確認"""
        url = reverse('get_client_users', kwargs={'client_id': self.test_client1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(len(json_response), 2)

        # Check for the __str__ format
        self.assertEqual(json_response[0]['name'], str(self.client_user1))
        self.assertEqual(json_response[1]['name'], str(self.client_user2))
        self.assertEqual(json_response[0]['name'], 'Test Department - Manager - User 1')

    def test_get_client_users_no_users(self):
        """ユーザーがいないクライアントの場合に空のリストが返されることを確認"""
        url = reverse('get_client_users', kwargs={'client_id': self.test_client2.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_client_users_invalid_client(self):
        """存在しないクライアントIDの場合に空のリストが返されることを確認"""
        url = reverse('get_client_users', kwargs={'client_id': 999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_client_users_unauthenticated(self):
        """未認証のアクセスがリダイレクトされることを確認"""
        self.client.logout()
        url = reverse('get_client_users', kwargs={'client_id': self.test_client1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)
