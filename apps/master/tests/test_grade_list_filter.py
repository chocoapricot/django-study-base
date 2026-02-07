from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from datetime import date, timedelta, datetime
from apps.master.models import Grade
from apps.common.constants import Constants

User = get_user_model()

class GradeListFilterTest(TestCase):
    """スタッフ等級一覧のフィルタリング機能のテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(Grade)
        view_perm = Permission.objects.get(codename='view_grade', content_type=content_type)
        self.user.user_permissions.add(view_perm)
        self.client.login(username='testuser', password='testpassword')

        today = date.today()

        # 今日有効な等級
        self.grade_today = Grade.objects.create(
            code='G-TODAY',
            name='今日有効',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000,
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=5),
            is_active=True
        )

        # 過去に有効だった等級
        self.grade_past = Grade.objects.create(
            code='G-PAST',
            name='過去に有効',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000,
            start_date=today - timedelta(days=20),
            end_date=today - timedelta(days=10),
            is_active=True
        )

        # 未来に有効になる等級
        self.grade_future = Grade.objects.create(
            code='G-FUTURE',
            name='未来に有効',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=20),
            is_active=True
        )

        # 期間指定なし
        self.grade_no_date = Grade.objects.create(
            code='G-NODATE',
            name='期間指定なし',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000,
            start_date=None,
            end_date=None,
            is_active=True
        )

    def test_initial_display_defaults_to_today(self):
        """初期表示（基準日指定なし）で今日の有効データが表示されること"""
        response = self.client.get(reverse('master:grade_list'))
        self.assertEqual(response.status_code, 200)

        # 今日の日付
        today_str = date.today().isoformat()
        self.assertEqual(response.context['reference_date'], today_str)

        # 含まれるべきデータ
        self.assertContains(response, '今日有効')
        self.assertContains(response, '期間指定なし')

        # 含まれないべきデータ
        self.assertNotContains(response, '過去に有効')
        self.assertNotContains(response, '未来に有効')

    def test_filter_by_past_date(self):
        """過去の日付を指定してフィルタリング"""
        past_date = date.today() - timedelta(days=15)
        response = self.client.get(reverse('master:grade_list'), {'reference_date': past_date.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['reference_date'], past_date.isoformat())

        self.assertContains(response, '過去に有効')
        self.assertContains(response, '期間指定なし')
        self.assertNotContains(response, '今日有効')
        self.assertNotContains(response, '未来に有効')

    def test_filter_by_future_date(self):
        """未来の日付を指定してフィルタリング"""
        future_date = date.today() + timedelta(days=15)
        response = self.client.get(reverse('master:grade_list'), {'reference_date': future_date.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['reference_date'], future_date.isoformat())

        self.assertContains(response, '未来に有効')
        self.assertContains(response, '期間指定なし')
        self.assertNotContains(response, '今日有効')
        self.assertNotContains(response, '過去に有効')

    def test_blank_date_shows_all(self):
        """基準日が空の場合は全データが表示されること"""
        response = self.client.get(reverse('master:grade_list'), {'reference_date': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['reference_date'], '')

        self.assertContains(response, '今日有効')
        self.assertContains(response, '過去に有効')
        self.assertContains(response, '未来に有効')
        self.assertContains(response, '期間指定なし')
