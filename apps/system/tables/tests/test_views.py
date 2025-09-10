from django.test import TestCase, Client as DjangoClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.client.models import Client

User = get_user_model()

class TableViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """テスト用の初期データをクラスレベルで設定"""
        cls.user = User.objects.create_user(username='testuser', password='password')
        # ソート順をテストするために、明確な順序を持つデータを作成
        cls.client_b = Client.objects.create(name='Client B', name_furigana='クライアントＢ', created_by=cls.user)
        cls.client_a = Client.objects.create(name='Client A', name_furigana='クライアントＡ', created_by=cls.user)

    def setUp(self):
        """各テストの前にクライアントをセットアップ"""
        self.client = DjangoClient()
        # ほとんどのテストで認証が必要なので、ここでログイン
        self.client.login(username='testuser', password='password')

    def test_table_list_view_unauthenticated(self):
        """未認証のユーザーはログインページにリダイレクトされることをテスト"""
        # 未認証のクライアントを別途作成
        unauthenticated_client = DjangoClient()
        response = unauthenticated_client.get(reverse('system_tables:table_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/system/tables/')

    def test_table_list_view_authenticated(self):
        """認証済みのユーザーは正常にページを表示できることをテスト"""
        response = self.client.get(reverse('system_tables:table_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'system/tables/table_list.html')
        self.assertIn('tables', response.context)
        self.assertEqual(len(response.context['tables']), 60)

    def test_table_data_view_unauthenticated(self):
        """未認証のユーザーはデータ表示ページでリダイレクトされることをテスト"""
        unauthenticated_client = DjangoClient()
        response = unauthenticated_client.get(reverse('system_tables:table_data', kwargs={'table_name': 'apps_client'}))
        self.assertEqual(response.status_code, 302)

    def test_table_data_view_authenticated(self):
        """認証済みのユーザーはデータ表示ページを正常に表示できることをテスト"""
        response = self.client.get(reverse('system_tables:table_data', kwargs={'table_name': 'apps_client'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'system/tables/table_data.html')
        self.assertEqual(response.context['table_name'], 'apps_client')
        self.assertIn('headers', response.context)
        self.assertIn('rows', response.context)

    def test_table_data_view_sorting(self):
        """データ表示ページのサーバーサイドソート機能が正しく動作することをテスト"""
        # 'name' 列で降順ソート
        response = self.client.get(reverse('system_tables:table_data', kwargs={'table_name': 'apps_client'}), {'sort_by': 'name', 'order': 'desc'})
        self.assertEqual(response.status_code, 200)
        rows = response.context['rows']
        headers = response.context['headers']

        # 'name' 列のインデックスを取得
        try:
            name_index = headers.index('name')
        except ValueError:
            self.fail("'name' header not found in context")

        # 返された行の'name'が降順になっていることを確認
        self.assertGreater(len(rows), 1, "テストには2つ以上の行が必要です")
        self.assertEqual(rows[0][name_index], 'Client B')
        self.assertEqual(rows[1][name_index], 'Client A')

        # 'name' 列で昇順ソート
        response = self.client.get(reverse('system_tables:table_data', kwargs={'table_name': 'apps_client'}), {'sort_by': 'name', 'order': 'asc'})
        self.assertEqual(response.status_code, 200)
        rows = response.context['rows']

        # 返された行の'name'が昇順になっていることを確認
        self.assertEqual(rows[0][name_index], 'Client A')
        self.assertEqual(rows[1][name_index], 'Client B')

    def test_table_data_view_invalid_table(self):
        """存在しないテーブル名で404が返されることをテスト"""
        response = self.client.get(reverse('system_tables:table_data', kwargs={'table_name': 'invalid_table_name'}))
        self.assertEqual(response.status_code, 404)
