from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.master.models import StaffTag, ClientTag

User = get_user_model()

class StaffTagModelTest(TestCase):
    """スタッフタグモデルのテスト"""

    def test_str_method(self):
        """__str__メソッドのテスト"""
        tag = StaffTag.objects.create(name='タグA')
        self.assertEqual(str(tag), 'タグA')

class StaffTagViewTest(TestCase):
    """スタッフタグビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='stafftestuser',
            password='testpassword'
        )
        self.tag = StaffTag.objects.create(name='テストスタッフタグ')

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(StaffTag)
        self.view_perm = Permission.objects.get(codename='view_stafftag', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_stafftag', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_stafftag', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_stafftag', content_type=content_type)
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        self.client.login(username='stafftestuser', password='testpassword')
        response = self.client.get(reverse('master:staff_tag_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストスタッフタグ')

    def test_create_view_post(self):
        """作成ビュー（POST）"""
        self.client.login(username='stafftestuser', password='testpassword')
        form_data = {
            'name': '新しいスタッフタグ',
            'display_order': 1,
            'is_active': True,
        }
        response = self.client.post(reverse('master:staff_tag_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffTag.objects.filter(name='新しいスタッフタグ').exists())

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        self.client.login(username='stafftestuser', password='testpassword')
        form_data = {
            'name': '更新されたスタッフタグ',
            'display_order': self.tag.display_order,
            'is_active': self.tag.is_active,
        }
        response = self.client.post(reverse('master:staff_tag_update', kwargs={'pk': self.tag.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, '更新されたスタッフタグ')

    def test_delete_view_post(self):
        """削除ビュー（POST）"""
        self.client.login(username='stafftestuser', password='testpassword')
        response = self.client.post(reverse('master:staff_tag_delete', kwargs={'pk': self.tag.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffTag.objects.filter(pk=self.tag.pk).exists())

class ClientTagViewTest(TestCase):
    """クライアントタグビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='clienttestuser',
            password='testpassword'
        )
        self.tag = ClientTag.objects.create(name='テストクライアントタグ')

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(ClientTag)
        self.view_perm = Permission.objects.get(codename='view_clienttag', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_clienttag', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_clienttag', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_clienttag', content_type=content_type)
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        self.client.login(username='clienttestuser', password='testpassword')
        response = self.client.get(reverse('master:client_tag_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストクライアントタグ')

    def test_create_view_post(self):
        """作成ビュー（POST）"""
        self.client.login(username='clienttestuser', password='testpassword')
        form_data = {
            'name': '新しいクライアントタグ',
            'display_order': 1,
            'is_active': True,
        }
        response = self.client.post(reverse('master:client_tag_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientTag.objects.filter(name='新しいクライアントタグ').exists())

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        self.client.login(username='clienttestuser', password='testpassword')
        form_data = {
            'name': '更新されたクライアントタグ',
            'display_order': self.tag.display_order,
            'is_active': self.tag.is_active,
        }
        response = self.client.post(reverse('master:client_tag_update', kwargs={'pk': self.tag.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, '更新されたクライアントタグ')

    def test_delete_view_post(self):
        """削除ビュー（POST）"""
        self.client.login(username='clienttestuser', password='testpassword')
        response = self.client.post(reverse('master:client_tag_delete', kwargs={'pk': self.tag.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClientTag.objects.filter(pk=self.tag.pk).exists())
