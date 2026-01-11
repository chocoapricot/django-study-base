from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff, StaffEvaluation
from apps.master.models import StaffRegistStatus, EmploymentType
import datetime
from unittest.mock import patch

User = get_user_model()

class StaffEvaluationViewTests(TestCase):
    def setUp(self):
        # ユーザー作成 (権限あり)
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        
        # 権限付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(content_type__app_label='staff')
        self.user.user_permissions.add(*permissions)

        # マスタデータ作成 (外部キー制約回避のため)
        self.status = StaffRegistStatus.objects.create(name='TestStatus', display_order=1)
        self.etype = EmploymentType.objects.create(name='TestType', display_order=1)

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='Test',
            name_first='Staff',
            regist_status=self.status,
            employment_type=self.etype
        )

    def test_evaluation_create(self):
        """評価登録のテスト"""
        url = reverse('staff:staff_evaluation_create', kwargs={'staff_pk': self.staff.pk})
        data = {
            'evaluation_date': datetime.date.today(),
            'rating': 5,
            'comment': 'Good job!'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # リダイレクト
        self.assertTrue(StaffEvaluation.objects.filter(staff=self.staff, rating=5).exists())

    def test_evaluation_list(self):
        """評価一覧のテスト"""
        StaffEvaluation.objects.create(staff=self.staff, rating=4, comment='Nice')
        url = reverse('staff:staff_evaluation_list', kwargs={'staff_pk': self.staff.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nice')

    def test_evaluation_update(self):
        """評価更新のテスト"""
        eval = StaffEvaluation.objects.create(staff=self.staff, rating=3, comment='Okay')
        url = reverse('staff:staff_evaluation_update', kwargs={'pk': eval.pk})
        data = {
            'evaluation_date': datetime.date.today(),
            'rating': 2, # 下げる
            'comment': 'Needs improvement'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        eval.refresh_from_db()
        self.assertEqual(eval.rating, 2)
        self.assertEqual(eval.comment, 'Needs improvement')

    def test_evaluation_delete(self):
        """評価削除のテスト"""
        eval = StaffEvaluation.objects.create(staff=self.staff, rating=1, comment='Bad')
        url = reverse('staff:staff_evaluation_delete', kwargs={'pk': eval.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffEvaluation.objects.filter(pk=eval.pk).exists())

    @patch('apps.staff.views_evaluation.run_ai_check')
    def test_evaluation_list_ai_check(self, mock_run_ai_check):
        """評価一覧ページでのAI要約機能のテスト"""
        mock_run_ai_check.return_value = ('AIによる要約結果です', None)
        StaffEvaluation.objects.create(staff=self.staff, evaluation_date=datetime.date.today(), rating=5, comment='素晴らしい')

        url = reverse('staff:staff_evaluation_list', kwargs={'staff_pk': self.staff.pk})

        # GETリクエストではAI要約は実行されない
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_evaluation_list.html')
        self.assertNotContains(response, 'AIによる要約結果です')
        mock_run_ai_check.assert_not_called()

        # POSTリクエストでAI要約が実行される
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_evaluation_list.html')
        self.assertContains(response, 'AIによる要約結果です')
        mock_run_ai_check.assert_called_once()
