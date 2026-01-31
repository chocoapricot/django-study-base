from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.master.models import FlagStatus
from apps.company.models import Company

User = get_user_model()

class FlagStatusModelTest(TestCase):
    """フラッグステータスモデルのテスト"""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", corporate_number="1234567890123")

    def test_str_method(self):
        """__str__メソッドのテスト"""
        flag_status = FlagStatus.objects.create(name='テストステータス', tenant_id=self.company.id)
        self.assertEqual(str(flag_status), 'テストステータス')

class FlagStatusViewTest(TestCase):
    """フラッグステータスビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.company = Company.objects.create(name="Test Company", corporate_number="1234567890123")
        self.flag_status = FlagStatus.objects.create(name='テストフラッグステータス', tenant_id=self.company.id)

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(FlagStatus)
        self.view_perm = Permission.objects.get(codename='view_flagstatus', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_flagstatus', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_flagstatus', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_flagstatus', content_type=content_type)
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        self.client.login(username='testuser', password='testpassword')
        # Session should have current_tenant_id
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.get(reverse('master:flag_status_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストフラッグステータス')

    def test_list_view_redirects_for_anonymous_user(self):
        """一覧ビュー（未ログイン）"""
        response = self.client.get(reverse('master:flag_status_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_view_forbidden_for_user_without_permission(self):
        """一覧ビュー（ログイン済み・権限なし）"""
        self.user.user_permissions.remove(self.view_perm)
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('master:flag_status_list'))
        self.assertEqual(response.status_code, 403)

    def test_create_view_post(self):
        """作成ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        form_data = {
            'name': '新しいフラッグステータス',
            'display_order': 1,
            'is_active': True,
        }
        response = self.client.post(reverse('master:flag_status_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FlagStatus.objects.filter(name='新しいフラッグステータス').exists())

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        form_data = {
            'name': '更新されたフラッグステータス',
            'display_order': self.flag_status.display_order,
            'is_active': self.flag_status.is_active,
        }
        response = self.client.post(reverse('master:flag_status_update', kwargs={'pk': self.flag_status.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.flag_status.refresh_from_db()
        self.assertEqual(self.flag_status.name, '更新されたフラッグステータス')

    def test_delete_view_post(self):
        """削除ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.post(reverse('master:flag_status_delete', kwargs={'pk': self.flag_status.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FlagStatus.objects.filter(pk=self.flag_status.pk).exists())
