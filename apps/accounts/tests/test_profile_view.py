from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.system.logs.models import AppLog
from django.utils import timezone

User = get_user_model()

class ProfileViewTest(TestCase):
    """プロフィールビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password=self.password
        )
        # 15件のログイン履歴を作成（10件制限のテスト用）
        for i in range(15):
            AppLog.objects.create(
                user=self.user,
                action='login',
                model_name='User',
                object_id=str(self.user.id),
                object_repr=f'{self.user.username} がログイン',
                timestamp=timezone.now()
            )

    def test_profile_page_access_requires_login(self):
        """プロフィールページへのアクセスにログインが必要"""
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertIn('/accounts/login/', response.url)

    def test_profile_page_displays_user_info(self):
        """プロフィールページにユーザー情報が表示される"""
        self.client.login(email='test@example.com', password=self.password)
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/profile.html')
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'ログイン履歴')
        self.assertContains(response, '直近10件まで表示')

    def test_profile_update_post(self):
        """プロフィール更新のPOSTリクエストをテスト"""
        self.client.login(email='test@example.com', password=self.password)

        # プロフィール更新ページにPOSTリクエスト
        response = self.client.post(reverse('accounts:profile'), {
            'username': 'testuser2',
            'email': 'testuser2@example.com',
            'first_name': 'test',
            'last_name': 'user',
        }, follow=True)

        # 成功時のレスポンスを検証
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/profile.html')
        self.assertContains(response, 'ユーザ情報を保存しました。')

        # ユーザー情報が更新されていることを確認
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser2')
        self.assertEqual(self.user.email, 'testuser2@example.com')
        self.assertEqual(self.user.first_name, 'test')
        self.assertEqual(self.user.last_name, 'user')

    def test_login_history_limit_to_10(self):
        """ログイン履歴が10件に制限されることをテスト"""
        self.client.login(email='test@example.com', password=self.password)
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('login_history', response.context)
        self.assertEqual(len(response.context['login_history']), 10)

    def test_login_history_order(self):
        """ログイン履歴が新しい順に並んでいることをテスト"""
        self.client.login(email='test@example.com', password=self.password)
        response = self.client.get(reverse('accounts:profile'))

        login_history = response.context['login_history']
        if len(login_history) > 1:
            for i in range(len(login_history) - 1):
                self.assertGreaterEqual(
                    login_history[i].timestamp,
                    login_history[i + 1].timestamp
                )
