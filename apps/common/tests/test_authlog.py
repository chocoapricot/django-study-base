from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.system.logs.models import AppLog

User = get_user_model()


class AuthLogTest(TestCase):
    """認証ログのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_login_log_with_ip(self):
        """ログイン時にIPアドレスが記録されることをテスト"""
        from django.contrib.auth.signals import user_logged_in
        from django.test import RequestFactory
        
        # ログイン前のログ件数を確認
        initial_count = AppLog.objects.filter(action='login').count()
        
        # リクエストを作成
        factory = RequestFactory()
        request = factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        # ログインシグナルを直接発火
        user_logged_in.send(sender=User, request=request, user=self.user)
        
        # ログイン後のログ件数を確認
        final_count = AppLog.objects.filter(action='login').count()
        self.assertEqual(final_count, initial_count + 1)
        
        # 最新のログインログを取得
        login_log = AppLog.objects.filter(action='login').order_by('-timestamp').first()
        
        # ログの内容を確認
        self.assertEqual(login_log.user, self.user)
        self.assertEqual(login_log.action, 'login')
        self.assertEqual(login_log.model_name, 'User')
        self.assertEqual(login_log.object_id, str(self.user.pk))
        
        # IPアドレスが含まれていることを確認
        self.assertIn('IP: 192.168.1.100', login_log.object_repr)
        self.assertIn('がログイン', login_log.object_repr)
    
    def test_logout_log_with_ip(self):
        """ログアウト時にIPアドレスが記録されることをテスト"""
        from django.contrib.auth.signals import user_logged_out
        from django.test import RequestFactory
        
        # ログアウト前のログ件数を確認
        initial_count = AppLog.objects.filter(action='logout').count()
        
        # リクエストを作成
        factory = RequestFactory()
        request = factory.post('/logout/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        
        # ログアウトシグナルを直接発火
        user_logged_out.send(sender=User, request=request, user=self.user)
        
        # ログアウト後のログ件数を確認
        final_count = AppLog.objects.filter(action='logout').count()
        self.assertEqual(final_count, initial_count + 1)
        
        # 最新のログアウトログを取得
        logout_log = AppLog.objects.filter(action='logout').order_by('-timestamp').first()
        
        # ログの内容を確認
        self.assertEqual(logout_log.user, self.user)
        self.assertEqual(logout_log.action, 'logout')
        self.assertEqual(logout_log.model_name, 'User')
        self.assertEqual(logout_log.object_id, str(self.user.pk))
        
        # IPアドレスが含まれていることを確認
        self.assertIn('IP: 10.0.0.1', logout_log.object_repr)
        self.assertIn('がログアウト', logout_log.object_repr)
    
    def test_ip_address_extraction_with_forwarded_header(self):
        """X-Forwarded-Forヘッダーがある場合のIPアドレス取得テスト"""
        from apps.common.authlog import get_client_ip
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # X-Forwarded-Forヘッダーがある場合
        request = factory.get('/', HTTP_X_FORWARDED_FOR='192.168.1.100, 10.0.0.1')
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')
        
        # X-Forwarded-Forヘッダーがない場合
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        ip = get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')
    
    def test_login_logout_sequence_with_ip(self):
        """ログイン→ログアウトの一連の流れでIPアドレスが記録されることをテスト"""
        from django.contrib.auth.signals import user_logged_in, user_logged_out
        from django.test import RequestFactory
        
        # 初期状態のログ件数
        initial_login_count = AppLog.objects.filter(action='login').count()
        initial_logout_count = AppLog.objects.filter(action='logout').count()
        
        # リクエストを作成
        factory = RequestFactory()
        
        # ログインリクエスト
        login_request = factory.post('/login/')
        login_request.META['REMOTE_ADDR'] = '172.16.0.1'
        user_logged_in.send(sender=User, request=login_request, user=self.user)
        
        # ログアウトリクエスト
        logout_request = factory.post('/logout/')
        logout_request.META['REMOTE_ADDR'] = '172.16.0.1'
        user_logged_out.send(sender=User, request=logout_request, user=self.user)
        
        # ログ件数の確認
        final_login_count = AppLog.objects.filter(action='login').count()
        final_logout_count = AppLog.objects.filter(action='logout').count()
        
        self.assertEqual(final_login_count, initial_login_count + 1)
        self.assertEqual(final_logout_count, initial_logout_count + 1)
        
        # 最新のログイン・ログアウトログを取得
        login_log = AppLog.objects.filter(action='login').order_by('-timestamp').first()
        logout_log = AppLog.objects.filter(action='logout').order_by('-timestamp').first()
        
        # 両方のログにIPアドレスが含まれていることを確認
        self.assertIn('IP: 172.16.0.1', login_log.object_repr)
        self.assertIn('IP: 172.16.0.1', logout_log.object_repr)
        
        # 同じユーザーのログであることを確認
        self.assertEqual(login_log.user, self.user)
        self.assertEqual(logout_log.user, self.user)