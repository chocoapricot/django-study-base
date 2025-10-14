from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.master.models import StaffRegistStatus

User = get_user_model()

class StaffRegistStatusModelTest(TestCase):
    """スタッフ登録状況モデルのテスト"""

    def test_str_method(self):
        """__str__メソッドのテスト"""
        staff_regist_status = StaffRegistStatus.objects.create(name='登録済み')
        self.assertEqual(str(staff_regist_status), '登録済み')

class StaffRegistStatusViewTest(TestCase):
    """スタッフ登録状況ビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.staff_regist_status = StaffRegistStatus.objects.create(name='テスト登録状況')

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(StaffRegistStatus)
        self.view_perm = Permission.objects.get(codename='view_staffregiststatus', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_staffregiststatus', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_staffregiststatus', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_staffregiststatus', content_type=content_type)
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('master:staff_regist_status_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト登録状況')

    def test_list_view_redirects_for_anonymous_user(self):
        """一覧ビュー（未ログイン）"""
        response = self.client.get(reverse('master:staff_regist_status_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_view_forbidden_for_user_without_permission(self):
        """一覧ビュー（ログイン済み・権限なし）"""
        self.user.user_permissions.remove(self.view_perm)
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('master:staff_regist_status_list'))
        self.assertEqual(response.status_code, 403)

    def test_create_view_post(self):
        """作成ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'name': '新しい登録状況',
            'display_order': 1,
            'is_active': True,
        }
        response = self.client.post(reverse('master:staff_regist_status_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffRegistStatus.objects.filter(name='新しい登録状況').exists())

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'name': '更新された登録状況',
            'display_order': self.staff_regist_status.display_order,
            'is_active': self.staff_regist_status.is_active,
        }
        response = self.client.post(reverse('master:staff_regist_status_update', kwargs={'pk': self.staff_regist_status.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.staff_regist_status.refresh_from_db()
        self.assertEqual(self.staff_regist_status.name, '更新された登録状況')

    def test_delete_view_post(self):
        """削除ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('master:staff_regist_status_delete', kwargs={'pk': self.staff_regist_status.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffRegistStatus.objects.filter(pk=self.staff_regist_status.pk).exists())
