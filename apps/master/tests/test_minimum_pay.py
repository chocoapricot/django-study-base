from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import MinimumPay
from apps.system.settings.models import Dropdowns
from datetime import date, timedelta

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
        Dropdowns.objects.create(category='pref', name='埼玉県', value='11', disp_seq=3)

        # テスト用最低賃金データ作成
        self.minimum_pay_past = MinimumPay.objects.create(
            pref='13', # Tokyo
            start_date=date.today() - timedelta(days=1),
            hourly_wage=1113,
        )
        self.minimum_pay_today = MinimumPay.objects.create(
            pref='11', # Saitama
            start_date=date.today(),
            hourly_wage=1000,
        )
        self.minimum_pay_future_near = MinimumPay.objects.create(
            pref='14', # Kanagawa
            start_date=date.today() + timedelta(days=30),
            hourly_wage=1200,
        )
        self.minimum_pay_future_far = MinimumPay.objects.create(
            pref='14', # Kanagawa
            start_date=date.today() + timedelta(days=60),
            hourly_wage=1300,
        )
        self.minimum_pay_future_tokyo = MinimumPay.objects.create(
            pref='13', # Tokyo
            start_date=date.today() + timedelta(days=10),
            hourly_wage=1150,
        )

        self.test_client = TestClient()
        self.test_client.login(username='testuser', password='testpass123')

    def test_minimum_pay_list_view_no_filter(self):
        """最低賃金一覧ビューのテスト（フィルタなし）"""
        response = self.test_client.get(reverse('master:minimum_pay_list'))
        self.assertEqual(response.status_code, 200)
        pays_in_context = response.context['minimum_pays']
        self.assertEqual(len(pays_in_context), 5)
        self.assertIn(self.minimum_pay_past, pays_in_context)
        self.assertIn(self.minimum_pay_today, pays_in_context)
        self.assertIn(self.minimum_pay_future_near, pays_in_context)
        self.assertIn(self.minimum_pay_future_far, pays_in_context)
        self.assertIn(self.minimum_pay_future_tokyo, pays_in_context)
        self.assertEqual(response.context['date_filter'], '')

    def test_minimum_pay_list_view_with_date_filter(self):
        """最低賃金一覧ビューのテスト（「現在以降」フィルタ）"""
        response = self.test_client.get(reverse('master:minimum_pay_list'), {'date_filter': 'future'})
        self.assertEqual(response.status_code, 200)
        pays_in_context = response.context['minimum_pays']

        # 過去と本日のレコードは含まれない
        self.assertNotIn(self.minimum_pay_past, pays_in_context)
        self.assertNotIn(self.minimum_pay_today, pays_in_context)

        # 各都道府県の最も近い未来のレコードのみが含まれる
        self.assertIn(self.minimum_pay_future_tokyo, pays_in_context) # Tokyo's next one
        self.assertIn(self.minimum_pay_future_near, pays_in_context) # Kanagawa's next one

        # 神奈川のさらに未来のレコードは含まれない
        self.assertNotIn(self.minimum_pay_future_far, pays_in_context)

        self.assertEqual(len(pays_in_context), 2)
        self.assertEqual(response.context['date_filter'], 'future')

    def test_minimum_pay_list_view_default_filter_from_master_index(self):
        """マスタ一覧からの遷移でデフォルトフィルタが適用されるかのテスト"""
        response = self.test_client.get(reverse('master:minimum_pay_list'), HTTP_REFERER='/master/')
        self.assertEqual(response.status_code, 200)
        pays_in_context = response.context['minimum_pays']

        self.assertNotIn(self.minimum_pay_past, pays_in_context)
        self.assertNotIn(self.minimum_pay_today, pays_in_context)
        self.assertIn(self.minimum_pay_future_tokyo, pays_in_context)
        self.assertIn(self.minimum_pay_future_near, pays_in_context)
        self.assertNotIn(self.minimum_pay_future_far, pays_in_context)
        self.assertEqual(len(pays_in_context), 2)
        self.assertEqual(response.context['date_filter'], 'future')

    def test_minimum_pay_create_view_get(self):
        """最低賃金作成ビューGETのテスト"""
        response = self.test_client.get(reverse('master:minimum_pay_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '最低賃金作成')

    def test_minimum_pay_create_post(self):
        """最低賃金作成POSTのテスト"""
        form_data = {
            'pref': '11', # Saitama
            'start_date': '2028-10-01',
            'hourly_wage': 1112,
            'is_active': True,
            'display_order': 1
        }
        response = self.test_client.post(reverse('master:minimum_pay_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MinimumPay.objects.filter(pref='11', hourly_wage=1112).exists())

    def test_minimum_pay_update_view_get(self):
        """最低賃金更新ビューGETのテスト"""
        response = self.test_client.get(
            reverse('master:minimum_pay_update', kwargs={'pk': self.minimum_pay_past.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '最低賃金編集')

    def test_minimum_pay_update_post(self):
        """最低賃金更新POSTのテスト"""
        form_data = {
            'pref': self.minimum_pay_past.pref,
            'start_date': self.minimum_pay_past.start_date,
            'hourly_wage': 9999,
            'is_active': True,
            'display_order': 1
        }
        response = self.test_client.post(
            reverse('master:minimum_pay_update', kwargs={'pk': self.minimum_pay_past.pk}),
            data=form_data
        )
        self.assertEqual(response.status_code, 302)
        self.minimum_pay_past.refresh_from_db()
        self.assertEqual(self.minimum_pay_past.hourly_wage, 9999)

    def test_minimum_pay_delete_post(self):
        """最低賃金削除POSTのテスト"""
        response = self.test_client.post(
            reverse('master:minimum_pay_delete', kwargs={'pk': self.minimum_pay_past.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            MinimumPay.objects.filter(pk=self.minimum_pay_past.pk).exists()
        )