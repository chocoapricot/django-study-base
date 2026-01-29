from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.client.models import Client
from apps.master.models import ClientTag

User = get_user_model()

class ClientTagSearchTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # ClientモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Client)
        # 必要な権限をユーザーに付与
        self.user.user_permissions.add(Permission.objects.get(codename='view_client', content_type=content_type))

        # タグを作成
        self.tag1 = ClientTag.objects.create(name='タグ1', display_order=1)
        self.tag2 = ClientTag.objects.create(name='タグ2', display_order=2)

        # クライアントを作成
        self.client1 = Client.objects.create(name='クライアント1', name_furigana='クライアント1')
        self.client1.tags.add(self.tag1)

        self.client2 = Client.objects.create(name='クライアント2', name_furigana='クライアント2')
        self.client2.tags.add(self.tag2)

        self.client3 = Client.objects.create(name='クライアント3', name_furigana='クライアント3')
        self.client3.tags.add(self.tag1, self.tag2)

        self.client4 = Client.objects.create(name='クライアント4', name_furigana='クライアント4')
        # クライアント4にはタグなし

    def test_client_list_filter_by_tag(self):
        """タグでの絞り込み機能をテスト"""
        # 1. タグ1で絞り込み
        response = self.client.get(reverse('client:client_list'), {'tag': self.tag1.pk})
        self.assertEqual(response.status_code, 200)
        clients = response.context['clients'].object_list
        self.assertEqual(len(clients), 2)
        self.assertIn(self.client1, clients)
        self.assertIn(self.client3, clients)
        self.assertNotIn(self.client2, clients)
        self.assertNotIn(self.client4, clients)

        # 2. タグ2で絞り込み
        response = self.client.get(reverse('client:client_list'), {'tag': self.tag2.pk})
        self.assertEqual(response.status_code, 200)
        clients = response.context['clients'].object_list
        self.assertEqual(len(clients), 2)
        self.assertIn(self.client2, clients)
        self.assertIn(self.client3, clients)
        self.assertNotIn(self.client1, clients)
        self.assertNotIn(self.client4, clients)

        # 3. タグフィルターなし（全て表示）
        response = self.client.get(reverse('client:client_list'))
        self.assertEqual(response.status_code, 200)
        clients = response.context['clients'].object_list
        self.assertEqual(len(clients), 4)

    def test_client_export_filter_by_tag(self):
        """エクスポートでのタグ絞り込み機能をテスト"""
        # 1. タグ1でエクスポート (CSV)
        response = self.client.get(reverse('client:client_export'), {'tag': self.tag1.pk, 'format': 'csv'})
        self.assertEqual(response.status_code, 200)
        # BOM付きCSVなのでデコードに注意
        content = response.content.decode('utf-8-sig')
        self.assertIn('クライアント1', content)
        self.assertIn('クライアント3', content)
        self.assertNotIn('クライアント2', content)
        self.assertNotIn('クライアント4', content)
