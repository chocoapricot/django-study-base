from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.master.models import JobCategory
from apps.system.settings.models import Dropdowns

User = get_user_model()

class JobCategoryModelTest(TestCase):
    """職種モデルのテスト"""
    
    def test_str_method(self):
        """__str__メソッドのテスト"""
        job_category = JobCategory.objects.create(name='エンジニア')
        self.assertEqual(str(job_category), 'エンジニア')

class JobCategoryViewTest(TestCase):
    """職種ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='superpassword'
        )
        self.job_category = JobCategory.objects.create(name='テスト職種')

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(JobCategory)
        self.view_perm = Permission.objects.get(codename='view_jobcategory', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_jobcategory', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_jobcategory', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_jobcategory', content_type=content_type)
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('master:job_category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト職種')

    def test_list_view_redirects_for_anonymous_user(self):
        """一覧ビュー（未ログイン）"""
        response = self.client.get(reverse('master:job_category_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_view_forbidden_for_user_without_permission(self):
        """一覧ビュー（ログイン済み・権限なし）"""
        self.user.user_permissions.remove(self.view_perm)
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('master:job_category_list'))
        self.assertEqual(response.status_code, 403)

    def test_create_view_post(self):
        """作成ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'name': '新しい職種',
            'display_order': 1,
            'is_active': True,
        }
        response = self.client.post(reverse('master:job_category_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(JobCategory.objects.filter(name='新しい職種').exists())

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'name': '更新された職種',
            'display_order': self.job_category.display_order,
            'is_active': self.job_category.is_active,
        }
        response = self.client.post(reverse('master:job_category_update', kwargs={'pk': self.job_category.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.job_category.refresh_from_db()
        self.assertEqual(self.job_category.name, '更新された職種')

    def test_delete_view_post(self):
        """削除ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('master:job_category_delete', kwargs={'pk': self.job_category.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(JobCategory.objects.filter(pk=self.job_category.pk).exists())
