from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from apps.master.models import DefaultValue

User = get_user_model()

class DefaultValueViewTest(TestCase):
    """初期値マスタビューのテスト"""

    @classmethod
    def setUpTestData(cls):
        """テストデータの設定"""
        # ユーザーと権限の設定
        cls.user = User.objects.create_user(username='testuser', password='testpassword')
        content_type = ContentType.objects.get_for_model(DefaultValue)

        # 権限が存在しない場合は作成
        view_perm, _ = Permission.objects.get_or_create(codename='view_defaultvalue', content_type=content_type, defaults={'name': 'Can view default value'})
        change_perm, _ = Permission.objects.get_or_create(codename='change_defaultvalue', content_type=content_type, defaults={'name': 'Can change default value'})

        cls.user.user_permissions.add(view_perm, change_perm)

        # サンプルデータのロード
        call_command('loaddata', '_sample_data/master_default_value.json', verbosity=0)
        cls.test_obj = DefaultValue.objects.first()

    def setUp(self):
        """各テスト前の設定"""
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')

    def test_sample_data_loaded(self):
        """サンプルデータが正しくロードされるかのテスト"""
        self.assertEqual(DefaultValue.objects.count(), 4)
        self.assertTrue(DefaultValue.objects.filter(pk='ClientContractTtp.contract_period').exists())

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        response = self.client.get(reverse('master:default_value_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.test_obj.target_item)
        # 「新規作成」ボタンがないことを確認
        self.assertNotContains(response, '新規作成')

    def test_list_view_redirects_for_anonymous_user(self):
        """一覧ビュー（未ログイン）"""
        self.client.logout()
        response = self.client.get(reverse('master:default_value_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('account_login')}?next={reverse('master:default_value_list')}")

    def test_list_view_forbidden_for_user_without_permission(self):
        """一覧ビュー（ログイン済み・権限なし）"""
        self.user.user_permissions.clear()
        response = self.client.get(reverse('master:default_value_list'))
        self.assertEqual(response.status_code, 403)

    def test_update_view_get(self):
        """更新ビュー（GET）"""
        response = self.client.get(reverse('master:default_value_update', kwargs={'pk': self.test_obj.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'readonly') # target_itemが読み取り専用であること

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        new_value = '新しいテスト値'
        form_data = {
            'target_item': self.test_obj.target_item,
            'format': self.test_obj.format,
            'value': new_value,
        }
        response = self.client.post(reverse('master:default_value_update', kwargs={'pk': self.test_obj.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('master:default_value_list'))

        self.test_obj.refresh_from_db()
        self.assertEqual(self.test_obj.value, new_value)

    def test_no_create_or_delete_view(self):
        """作成・削除ビューが存在しないことのテスト"""
        from django.urls.exceptions import NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('master:default_value_create')
        with self.assertRaises(NoReverseMatch):
            reverse('master:default_value_delete', kwargs={'pk': self.test_obj.pk})