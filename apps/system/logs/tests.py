from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from .models import MailLog
from .utils import log_mail, update_mail_log_status, get_user_mail_logs

User = get_user_model()

class MailLogTest(TestCase):
    """メールログ機能のテストクラス"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            first_name='テスト',
            last_name='ユーザー'
        )
        
        # 権限の設定
        content_type = ContentType.objects.get_for_model(MailLog)
        view_permission = Permission.objects.get(codename='view_maillog', content_type=content_type)
        self.user.user_permissions.add(view_permission)
        
        self.client.login(username='testuser', password='testpassword123')

    def test_log_mail_creation(self):
        """メールログ作成のテスト"""
        mail_log = log_mail(
            to_email='test@example.com',
            subject='テストメール',
            body='これはテストメールです。',
            mail_type='general',
            recipient_user=self.user,
            status='sent'
        )
        
        self.assertIsNotNone(mail_log)
        self.assertEqual(mail_log.to_email, 'test@example.com')
        self.assertEqual(mail_log.subject, 'テストメール')
        self.assertEqual(mail_log.mail_type, 'general')
        self.assertEqual(mail_log.status, 'sent')
        self.assertEqual(mail_log.recipient_user, self.user)

    def test_update_mail_log_status(self):
        """メールログ状況更新のテスト"""
        mail_log = log_mail(
            to_email='test@example.com',
            subject='テストメール',
            body='テスト本文',
            status='pending'
        )
        
        # 送信成功に更新
        updated_log = update_mail_log_status(mail_log.id, 'sent', message_id='test-message-id')
        
        self.assertEqual(updated_log.status, 'sent')
        self.assertIsNotNone(updated_log.sent_at)
        self.assertEqual(updated_log.message_id, 'test-message-id')
        
        # 送信失敗に更新
        updated_log = update_mail_log_status(mail_log.id, 'failed', error_message='送信エラー')
        
        self.assertEqual(updated_log.status, 'failed')
        self.assertEqual(updated_log.error_message, '送信エラー')

    def test_get_user_mail_logs(self):
        """ユーザーのメールログ取得のテスト"""
        # テストデータ作成
        log_mail(
            to_email=self.user.email,
            subject='サインアップメール',
            body='サインアップ確認',
            mail_type='signup',
            recipient_user=self.user
        )
        
        log_mail(
            to_email=self.user.email,
            subject='パスワードリセット',
            body='パスワードリセット確認',
            mail_type='password_reset',
            recipient_user=self.user
        )
        
        # 全てのログを取得
        logs = get_user_mail_logs(self.user)
        self.assertEqual(logs.count(), 2)
        
        # メール種別でフィルタ
        signup_logs = get_user_mail_logs(self.user, mail_type='signup')
        self.assertEqual(signup_logs.count(), 1)
        self.assertEqual(signup_logs.first().mail_type, 'signup')

    def test_mail_log_list_view(self):
        """メールログ一覧ビューのテスト"""
        # テストデータ作成
        log_mail(
            to_email='test1@example.com',
            subject='テストメール1',
            body='テスト本文1',
            mail_type='signup'
        )
        
        log_mail(
            to_email='test2@example.com',
            subject='テストメール2',
            body='テスト本文2',
            mail_type='password_reset'
        )
        
        response = self.client.get(reverse('logs:mail_log_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'メール送信ログ一覧')
        self.assertContains(response, 'test1@example.com')
        self.assertContains(response, 'test2@example.com')

    def test_mail_log_list_search(self):
        """メールログ一覧の検索機能テスト"""
        log_mail(
            to_email='search@example.com',
            subject='検索テストメール',
            body='検索用テスト本文'
        )
        
        log_mail(
            to_email='other@example.com',
            subject='その他のメール',
            body='その他の本文'
        )
        
        # メールアドレスで検索
        response = self.client.get(reverse('logs:mail_log_list'), {'q': 'search@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'search@example.com')
        self.assertNotContains(response, 'other@example.com')
        
        # 件名で検索
        response = self.client.get(reverse('logs:mail_log_list'), {'q': '検索テスト'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '検索テストメール')

    def test_mail_log_list_filter(self):
        """メールログ一覧のフィルタ機能テスト"""
        log_mail(
            to_email='signup@example.com',
            subject='サインアップメール',
            body='サインアップ本文',
            mail_type='signup',
            status='sent'
        )
        
        log_mail(
            to_email='reset@example.com',
            subject='パスワードリセット',
            body='リセット本文',
            mail_type='password_reset',
            status='failed'
        )
        
        # メール種別でフィルタ
        response = self.client.get(reverse('logs:mail_log_list'), {'mail_type': 'signup'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'signup@example.com')
        self.assertNotContains(response, 'reset@example.com')
        
        # 送信状況でフィルタ
        response = self.client.get(reverse('logs:mail_log_list'), {'status': 'failed'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reset@example.com')
        self.assertNotContains(response, 'signup@example.com')

    def test_mail_log_detail_view(self):
        """メールログ詳細ビューのテスト"""
        mail_log = log_mail(
            to_email='detail@example.com',
            subject='詳細テストメール',
            body='詳細テスト本文',
            mail_type='general',
            recipient_user=self.user
        )
        
        response = self.client.get(reverse('logs:mail_log_detail', args=[mail_log.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'メール送信ログ詳細')
        self.assertContains(response, 'detail@example.com')
        self.assertContains(response, '詳細テストメール')
        self.assertContains(response, '詳細テスト本文')

    def test_mail_log_model_properties(self):
        """メールログモデルのプロパティテスト"""
        mail_log = log_mail(
            to_email='property@example.com',
            subject='プロパティテスト',
            body='プロパティテスト本文',
            mail_type='signup',
            status='sent'
        )
        
        # is_successful プロパティ
        self.assertTrue(mail_log.is_successful)
        
        # mail_type_display_name プロパティ
        self.assertEqual(mail_log.mail_type_display_name, 'サインアップ確認')
        
        # status_display_name プロパティ
        self.assertEqual(mail_log.status_display_name, '送信成功')
        
        # __str__ メソッド
        expected_str = f"signup - property@example.com (sent)"
        self.assertEqual(str(mail_log), expected_str)

    def test_mail_log_permissions(self):
        """メールログの権限テスト"""
        # 権限のないユーザーでテスト
        user_no_perm = User.objects.create_user(
            username='noperm',
            email='noperm@example.com',
            password='testpass'
        )
        
        client_no_perm = TestClient()
        client_no_perm.login(username='noperm', password='testpass')
        
        # 一覧ページへのアクセス（権限なし）
        response = client_no_perm.get(reverse('logs:mail_log_list'))
        self.assertEqual(response.status_code, 403)
        
        # 詳細ページへのアクセス（権限なし）
        mail_log = log_mail(
            to_email='perm@example.com',
            subject='権限テスト',
            body='権限テスト本文'
        )
        
        response = client_no_perm.get(reverse('logs:mail_log_detail', args=[mail_log.pk]))
        self.assertEqual(response.status_code, 403)