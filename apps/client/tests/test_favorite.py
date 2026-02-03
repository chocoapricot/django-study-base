from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.client.models import Client, ClientFavorite
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class ClientFavoriteTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        # スレッドローカルにテナントIDをセット
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(username='testuser', password='testpassword', tenant_id=self.company.tenant_id)
        self.client.login(username='testuser', password='testpassword')

        # 権限付与
        content_type = ContentType.objects.get_for_model(Client)
        self.user.user_permissions.add(Permission.objects.get(codename='view_client', content_type=content_type))

        self.test_client = Client.objects.create(
            name='テスト株式会社',
            name_furigana='テストカブシキガイシャ',
            corporate_number='1234567890123',
            tenant_id=self.company.tenant_id
        )

    def test_favorite_add_view(self):
        """お気に入り追加ビューのテスト"""
        url = reverse('client:client_favorite_add', args=[self.test_client.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientFavorite.objects.filter(client=self.test_client, user=self.user).exists())

    def test_favorite_remove_view(self):
        """お気に入り削除ビューのテスト"""
        ClientFavorite.objects.create(client=self.test_client, user=self.user, tenant_id=self.company.tenant_id)
        url = reverse('client:client_favorite_remove', args=[self.test_client.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClientFavorite.objects.filter(client=self.test_client, user=self.user).exists())

    def test_client_list_favorite_annotation(self):
        """クライアント一覧でお気に入り状況がアノテーションされているかテスト"""
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # お気に入りなし
        response = self.client.get(reverse('client:client_list'))
        self.assertEqual(response.status_code, 200)
        clients = response.context['clients']
        self.assertFalse(clients[0].is_favorite)

        # お気に入りあり
        ClientFavorite.objects.create(client=self.test_client, user=self.user, tenant_id=self.company.tenant_id)
        response = self.client.get(reverse('client:client_list'))
        self.assertEqual(response.status_code, 200)
        clients = response.context['clients']
        self.assertTrue(clients[0].is_favorite)

    def test_client_detail_favorite_context(self):
        """クライアント詳細にお気に入り状況が含まれているかテスト"""
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # お気に入りなし
        response = self.client.get(reverse('client:client_detail', args=[self.test_client.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get('is_favorite', False))
        self.assertContains(response, 'お気に入り追加')

        # お気に入りあり
        ClientFavorite.objects.create(client=self.test_client, user=self.user, tenant_id=self.company.tenant_id)
        response = self.client.get(reverse('client:client_detail', args=[self.test_client.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get('is_favorite', False))
        self.assertNotContains(response, 'お気に入り追加')
        self.assertContains(response, 'bi-star-fill')
        self.assertContains(response, 'お気に入り解除')
