from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import MinimumPay
from apps.system.settings.models import Dropdowns
from datetime import date

User = get_user_model()


class MinimumPayViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True,
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='master',
            codename__in=[
                'add_minimumpay', 'view_minimumpay',
                'change_minimumpay', 'delete_minimumpay'
            ]
        )
        self.user.user_permissions.set(permissions)

        # テスト用都道府県データ作成
        Dropdowns.objects.create(category='pref', name='東京都', value='13', disp_seq=1)
        Dropdowns.objects.create(category='pref', name='神奈川県', value='14', disp_seq=2)

        # テスト用最低賃金データ作成
        self.minimum_pay = MinimumPay.objects.create(
            pref='13',
            start_date=date(2023, 10, 1),
            hourly_wage=1113,
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()
        self.test_client.login(username='testuser', password='testpass123')

    def test_minimum_pay_list_view(self):
        """最低賃金一覧ビューのテスト"""
        response = self.test_client.get(reverse('master:minimum_pay_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '東京都')
        self.assertContains(response, '1,113')

    def test_minimum_pay_create_view_get(self):
        """最低賃金作成ビューGETのテスト"""
        response = self.test_client.get(reverse('master:minimum_pay_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '最低賃金作成')

    def test_minimum_pay_create_post(self):
        """最低賃金作成POSTのテスト"""
        form_data = {
            'pref': '14',
            'start_date': '2023-10-01',
            'hourly_wage': 1112,
            'is_active': True,
            'display_order': 1
        }

        response = self.test_client.post(
            reverse('master:minimum_pay_create'),
            data=form_data
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(MinimumPay.objects.filter(pref='14').exists())

    def test_minimum_pay_update_view_get(self):
        """最低賃金更新ビューGETのテスト"""
        response = self.test_client.get(
            reverse('master:minimum_pay_update', kwargs={'pk': self.minimum_pay.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '最低賃金編集')

    def test_minimum_pay_update_post(self):
        """最低賃金更新POSTのテスト"""
        form_data = {
            'pref': '13',
            'start_date': '2023-10-01',
            'hourly_wage': 1200,
            'is_active': True,
            'display_order': 1
        }

        response = self.test_client.post(
            reverse('master:minimum_pay_update', kwargs={'pk': self.minimum_pay.pk}),
            data=form_data
        )

        self.assertEqual(response.status_code, 302)
        self.minimum_pay.refresh_from_db()
        self.assertEqual(self.minimum_pay.hourly_wage, 1200)

    def test_minimum_pay_delete_post(self):
        """最低賃金削除POSTのテスト"""
        response = self.test_client.post(
            reverse('master:minimum_pay_delete', kwargs={'pk': self.minimum_pay.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            MinimumPay.objects.filter(pk=self.minimum_pay.pk).exists()
        )
