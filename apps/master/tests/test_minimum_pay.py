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
        today = date.today()
        self.tokyo_past_old = MinimumPay.objects.create(pref='13', start_date=today - timedelta(days=100), hourly_wage=1100)
        self.tokyo_past_latest = MinimumPay.objects.create(pref='13', start_date=today - timedelta(days=1), hourly_wage=1113)
        self.tokyo_future = MinimumPay.objects.create(pref='13', start_date=today + timedelta(days=10), hourly_wage=1150)

        self.kanagawa_today = MinimumPay.objects.create(pref='14', start_date=today, hourly_wage=1200)
        self.kanagawa_future_1 = MinimumPay.objects.create(pref='14', start_date=today + timedelta(days=30), hourly_wage=1250)
        self.kanagawa_future_2 = MinimumPay.objects.create(pref='14', start_date=today + timedelta(days=60), hourly_wage=1300)

        self.saitama_past = MinimumPay.objects.create(pref='11', start_date=today - timedelta(days=5), hourly_wage=1000)

        self.all_pays = [
            self.tokyo_past_old, self.tokyo_past_latest, self.tokyo_future,
            self.kanagawa_today, self.kanagawa_future_1, self.kanagawa_future_2,
            self.saitama_past
        ]

        self.test_client = TestClient()
        self.test_client.login(username='testuser', password='testpass123')

    def test_minimum_pay_list_view_no_filter(self):
        """最低賃金一覧ビューのテスト（フィルタなし）"""
        response = self.test_client.get(reverse('master:minimum_pay_list'))
        self.assertEqual(response.status_code, 200)
        pays_in_context = response.context['minimum_pays']
        self.assertEqual(len(pays_in_context), len(self.all_pays))
        for pay in self.all_pays:
            self.assertIn(pay, pays_in_context)
        self.assertEqual(response.context['date_filter'], '')

    def test_minimum_pay_list_view_with_date_filter(self):
        """最低賃金一覧ビューのテスト（「現在以降」フィルタ）"""
        response = self.test_client.get(reverse('master:minimum_pay_list'), {'date_filter': 'future'})
        self.assertEqual(response.status_code, 200)
        pays_in_context = response.context['minimum_pays']

        # 期待されるレコード
        expected_pays = {
            self.tokyo_past_latest, # 最新の過去レコード
            self.tokyo_future,      # 未来のレコード
            self.kanagawa_today,    # 本日のレコード（最新の過去/現在）
            self.kanagawa_future_1, # 未来のレコード
            self.kanagawa_future_2, # 未来のレコード
            self.saitama_past,      # 最新の過去レコード
        }

        self.assertEqual(set(pays_in_context), expected_pays)
        self.assertEqual(len(pays_in_context), len(expected_pays))
        self.assertNotIn(self.tokyo_past_old, pays_in_context) # 古い過去レコードは含まれない
        self.assertEqual(response.context['date_filter'], 'future')

    def test_minimum_pay_list_view_default_filter_from_master_index(self):
        """マスタ一覧からの遷移でデフォルトフィルタが適用されるかのテスト"""
        response = self.test_client.get(reverse('master:minimum_pay_list'), HTTP_REFERER='/master/')
        self.assertEqual(response.status_code, 200)
        pays_in_context = response.context['minimum_pays']

        expected_pays = {
            self.tokyo_past_latest,
            self.tokyo_future,
            self.kanagawa_today,
            self.kanagawa_future_1,
            self.kanagawa_future_2,
            self.saitama_past,
        }

        self.assertEqual(set(pays_in_context), expected_pays)
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
            reverse('master:minimum_pay_update', kwargs={'pk': self.tokyo_past_latest.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '最低賃金編集')

    def test_minimum_pay_update_post(self):
        """最低賃金更新POSTのテスト"""
        form_data = {
            'pref': self.tokyo_past_latest.pref,
            'start_date': self.tokyo_past_latest.start_date,
            'hourly_wage': 9999,
            'is_active': True,
            'display_order': 1
        }
        response = self.test_client.post(
            reverse('master:minimum_pay_update', kwargs={'pk': self.tokyo_past_latest.pk}),
            data=form_data
        )
        self.assertEqual(response.status_code, 302)
        self.tokyo_past_latest.refresh_from_db()
        self.assertEqual(self.tokyo_past_latest.hourly_wage, 9999)

    def test_minimum_pay_delete_post(self):
        """最低賃金削除POSTのテスト"""
        response = self.test_client.post(
            reverse('master:minimum_pay_delete', kwargs={'pk': self.tokyo_past_latest.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            MinimumPay.objects.filter(pk=self.tokyo_past_latest.pk).exists()
        )