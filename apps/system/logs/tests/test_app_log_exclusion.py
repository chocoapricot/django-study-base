from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.system.logs.models import AccessLog, AppLog

User = get_user_model()

class AppLogExclusionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_access_log_does_not_create_app_log(self):
        """
        AccessLogの作成がAppLogに記録されないことを確認するテスト。
        """
        # AppLogとAccessLogをクリア
        AppLog.objects.all().delete()
        AccessLog.objects.all().delete()

        # ホームページにアクセス
        self.client.get(reverse('home:home'))

        # AccessLogが1件作成されていることを確認
        self.assertEqual(AccessLog.objects.count(), 1)
        access_log_entry = AccessLog.objects.first()
        self.assertEqual(access_log_entry.url, reverse('home:home'))
        self.assertEqual(access_log_entry.user, self.user)

        # AccessLogモデルに対するAppLogが作成されていないことを確認
        app_log_count = AppLog.objects.filter(model_name='AccessLog').count()
        self.assertEqual(app_log_count, 0)
