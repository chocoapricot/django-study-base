from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.master.models import StaffGrade
from apps.common.constants import Constants

User = get_user_model()

class StaffGradeModelTest(TestCase):
    """スタッフ等級モデルのテスト"""

    def test_str_method(self):
        """__str__メソッドのテスト"""
        staff_grade = StaffGrade.objects.create(
            code='G1',
            name='等級1',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000
        )
        self.assertEqual(str(staff_grade), '等級1')

class StaffGradeViewTest(TestCase):
    """スタッフ等級ビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.staff_grade = StaffGrade.objects.create(
            code='G1',
            name='テスト等級',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000
        )

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(StaffGrade)
        self.view_perm = Permission.objects.get(codename='view_staffgrade', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_staffgrade', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_staffgrade', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_staffgrade', content_type=content_type)
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)

    def test_list_view_for_logged_in_user(self):
        """一覧ビュー（ログイン済み・権限あり）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('master:staff_grade_list'))
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
        response = self.client.post(reverse('master:staff_grade_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffGrade.objects.filter(code='G2').exists())

    def test_update_view_post(self):
        """更新ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'code': 'G1-MOD',
            'name': '更新された等級',
            'salary_type': self.staff_grade.salary_type,
            'amount': 1200,
            'display_order': self.staff_grade.display_order,
            'is_active': self.staff_grade.is_active,
        }
        response = self.client.post(reverse('master:staff_grade_update', kwargs={'pk': self.staff_grade.pk}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.staff_grade.refresh_from_db()
        self.assertEqual(self.staff_grade.name, '更新された等級')
        self.assertEqual(self.staff_grade.code, 'G1-MOD')

    def test_delete_view_post(self):
        """削除ビュー（POST）"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('master:staff_grade_delete', kwargs={'pk': self.staff_grade.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffGrade.objects.filter(pk=self.staff_grade.pk).exists())
