from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.system.logs.models import AccessLog

User = get_user_model()

class AccessLogMiddlewareTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        AccessLog.objects.all().delete()

    def test_start_page_is_not_logged(self):
        """
        /start/へのアクセスがログに記録されないことを確認する
        """
        self.client.get(reverse('home:start_page'))
        self.assertEqual(AccessLog.objects.count(), 0)

    def test_other_page_is_logged(self):
        """
        他のページへのアクセスがログに記録されることを確認する
        """
        self.client.get(reverse('home:home'))
        self.assertEqual(AccessLog.objects.count(), 1)
        self.assertEqual(AccessLog.objects.first().url, '/')

    def test_admin_page_is_not_logged(self):
        """
        /admin/へのアクセスがログに記録されないことを確認する
        """
        self.client.get('/admin/')
        self.assertEqual(AccessLog.objects.count(), 0)
