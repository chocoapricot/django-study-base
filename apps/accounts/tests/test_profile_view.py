from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.system.logs.models import AppLog
from django.utils import timezone

User = get_user_model()

class ProfileViewTest(TestCase):
    """プロフィールビューのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        
        # 25件のログイン履歴を作成（20件制限のテスト用）
        for i in range(25):
            AppLog.objects.create(
                user=self.user,
                action='login',
                model_name='User',
                object_id=str(self.user.id),
                object_repr=f'{self.user.username} がログイン',
                timestamp=timezone.now()
            )
    
    def test_login_history_limit_to_20(self):
        """ログイン履歴が20件に制限されることをテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('login_history', response.context)
        
        # ログイン履歴が20件以下であることを確認
        login_history = response.context['login_history']
        self.assertLessEqual(len(login_history), 20)
        
        # 実際に25件作成したが、20件のみ取得されることを確認
        total_login_logs = AppLog.objects.filter(user=self.user, action='login').count()
        self.assertGreaterEqual(total_login_logs, 20)  # 25件以上あることを確認
        self.assertEqual(len(login_history), 20)  # 取得は20件のみ
    
    def test_login_history_order(self):
        """ログイン履歴が新しい順に並んでいることをテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        
        login_history = response.context['login_history']
        if len(login_history) > 1:
            # 最初の項目が最新であることを確認
            for i in range(len(login_history) - 1):
                self.assertGreaterEqual(
                    login_history[i].timestamp,
                    login_history[i + 1].timestamp
                )
    
    def test_profile_page_access_requires_login(self):
        """プロフィールページへのアクセスにログインが必要"""
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertIn('/accounts/login/', response.url)
    
    def test_profile_page_displays_user_info(self):
        """プロフィールページにユーザー情報が表示される"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'ログイン履歴')
        self.assertContains(response, '直近20件まで表示')

    def test_profile_update_post(self):
        """プロフィール更新のPOSTリクエストをテスト"""
        self.client.login(username='testuser', password='testpass123')

        # 更新するデータ
        updated_data = {
            'email': 'updated@example.com',
            'last_name': 'Updated',
            'first_name': 'User',
        }

        response = self.client.post(reverse('accounts:profile'), updated_data, follow=True)

        # 更新後は同じページにリダイレクトされ、メッセージが表示される
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'プロフィールを更新しました。')

        # データベースでユーザー情報が更新されたか確認
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.last_name, 'Updated')