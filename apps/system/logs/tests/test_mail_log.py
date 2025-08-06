from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.system.logs.models import MailLog

User = get_user_model()


class MailLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_mail_log_creation(self):
        """MailLogモデルの作成テスト"""
        from datetime import datetime
        from django.utils import timezone
        
        mail_log = MailLog.objects.create(
            from_email='from@example.com',
            to_email='test@example.com',
            subject='テストメール',
            body='テストメールの本文です',
            mail_type='password_reset',
            status='sent',
            backend='django.core.mail.backends.smtp.EmailBackend',
            message_id='test-message-id@example.com',
            sent_at=timezone.now()
        )
        
        self.assertEqual(mail_log.from_email, 'from@example.com')
        self.assertEqual(mail_log.to_email, 'test@example.com')
        self.assertEqual(mail_log.subject, 'テストメール')
        self.assertEqual(mail_log.body, 'テストメールの本文です')
        self.assertEqual(mail_log.mail_type, 'password_reset')
        self.assertEqual(mail_log.status, 'sent')
        self.assertEqual(mail_log.backend, 'django.core.mail.backends.smtp.EmailBackend')
        self.assertEqual(mail_log.message_id, 'test-message-id@example.com')
        self.assertIsNotNone(mail_log.sent_at)

    def test_mail_log_str_representation(self):
        """MailLogの文字列表現テスト"""
        mail_log = MailLog.objects.create(
            from_email='from@example.com',
            to_email='test@example.com',
            subject='テストメール',
            mail_type='general',
            status='sent'
        )
        
        # 実際のstr表現をチェック
        str_repr = str(mail_log)
        self.assertIn('general', str_repr)
        self.assertIn('test@example.com', str_repr)
        self.assertIn('sent', str_repr)