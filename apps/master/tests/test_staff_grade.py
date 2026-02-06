from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.master.models import Grade
from apps.common.constants import Constants

User = get_user_model()

class GradeModelTest(TestCase):
    """スタッフ等級モデルのテスト"""

    def test_str_method(self):
        """__str__メソッドのテスト"""
        grade = Grade.objects.create(
            code='G1',
            name='等級1',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000
        )
        self.assertEqual(str(grade), '等級1')

class GradeViewTest(TestCase):
    """スタッフ等級ビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.grade = Grade.objects.create(
            code='G1',
            name='テスト等級',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000
        )

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(Grade)
        self.view_perm = Permission.objects.get(codename='view_grade', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_grade', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_grade', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_grade', content_type=content_type)
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('master:grade_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト等級')

    def test_create_view_post(self):
        """作成ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'code': 'G2',
            'name': '新しい等級',
            'salary_type': Constants.PAY_UNIT.DAILY,
            'amount': 8000,
            'display_order': 1,
            'is_active': True,
        }
        response = self.client.post(reverse('master:grade_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Grade.objects.filter(code='G2').exists())

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'code': 'G1-MOD',
            'name': '更新された等級',
            'salary_type': self.grade.salary_type,
            'amount': 1200,
            'display_order': self.grade.display_order,
            'is_active': self.grade.is_active,
        }
        response = self.client.post(reverse('master:grade_update', kwargs={'pk': self.grade.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.name, '更新された等級')
        self.assertEqual(self.grade.code, 'G1-MOD')

    def test_delete_view_post(self):
        """削除ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('master:grade_delete', kwargs={'pk': self.grade.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Grade.objects.filter(pk=self.grade.pk).exists())
