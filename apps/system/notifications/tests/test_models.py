from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.system.notifications.models import Notification

User = get_user_model()


class NotificationModelTest(TestCase):
    """Notificationモデルのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_notification(self):
        """通知の作成テスト"""
        notification = Notification.objects.create(
            user=self.user,
            title='テスト通知',
            message='これはテストメッセージです。',
            notification_type='general'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, 'テスト通知')
        self.assertEqual(notification.message, 'これはテストメッセージです。')
        self.assertEqual(notification.notification_type, 'general')
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
    
    def test_notification_str(self):
        """__str__メソッドのテスト"""
        notification = Notification.objects.create(
            user=self.user,
            title='テスト通知',
            message='テストメッセージ',
        )
        
        expected = f"{self.user.username} - テスト通知 (未読)"
        self.assertEqual(str(notification), expected)
    
    def test_mark_as_read(self):
        """既読にするメソッドのテスト"""
        notification = Notification.objects.create(
            user=self.user,
            title='テスト通知',
            message='テストメッセージ',
        )
        
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        
        notification.mark_as_read()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
        self.assertIsInstance(notification.read_at, timezone.datetime)
    
    def test_mark_as_read_idempotent(self):
        """既読メソッドの冪等性テスト（複数回呼んでも問題ない）"""
        notification = Notification.objects.create(
            user=self.user,
            title='テスト通知',
            message='テストメッセージ',
        )
        
        notification.mark_as_read()
        first_read_at = notification.read_at
        
        # 再度既読にする
        notification.mark_as_read()
        
        # read_atは変わらないはず
        self.assertEqual(notification.read_at, first_read_at)
    
    def test_notification_type_display_name(self):
        """通知種別の表示名テスト"""
        notification = Notification.objects.create(
            user=self.user,
            title='テスト通知',
            message='テストメッセージ',
            notification_type='alert'
        )
        
        self.assertEqual(notification.notification_type_display_name, 'アラート')
    
    def test_notification_with_link(self):
        """リンク付き通知のテスト"""
        notification = Notification.objects.create(
            user=self.user,
            title='リンク付き通知',
            message='詳細はリンクを確認してください。',
            link_url='/some/page/'
        )
        
        self.assertEqual(notification.link_url, '/some/page/')
    
    def test_notification_ordering(self):
        """通知の並び順テスト（新しい順）"""
        notification1 = Notification.objects.create(
            user=self.user,
            title='古い通知',
            message='古いメッセージ',
        )
        
        notification2 = Notification.objects.create(
            user=self.user,
            title='新しい通知',
            message='新しいメッセージ',
        )
        
        notifications = Notification.objects.all()
        self.assertEqual(notifications[0], notification2)
        self.assertEqual(notifications[1], notification1)
