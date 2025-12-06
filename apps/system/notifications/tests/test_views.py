from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.system.notifications.models import Notification

User = get_user_model()


class NotificationViewTest(TestCase):
    """通知ビューのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # テスト用通知を作成
        self.notification = Notification.objects.create(
            user=self.user,
            title='テスト通知',
            message='これはテストメッセージです。',
        )
        
        self.other_notification = Notification.objects.create(
            user=self.other_user,
            title='他ユーザーの通知',
            message='他のユーザーの通知です。',
        )
    
    def test_notification_list_requires_login(self):
        """通知一覧は認証が必要"""
        response = self.client.get(reverse('system_notifications:notification_list'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
    
    def test_notification_list_view(self):
        """通知一覧ビューのテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('system_notifications:notification_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト通知')
        self.assertNotContains(response, '他ユーザーの通知')
    
    def test_notification_detail_requires_login(self):
        """通知詳細は認証が必要"""
        response = self.client.get(
            reverse('system_notifications:notification_detail', args=[self.notification.pk])
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト
    
    def test_notification_detail_view(self):
        """通知詳細ビューのテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('system_notifications:notification_detail', args=[self.notification.pk])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト通知')
        self.assertContains(response, 'これはテストメッセージです。')
    
    def test_notification_detail_marks_as_read(self):
        """通知詳細表示で自動的に既読になる"""
        self.assertFalse(self.notification.is_read)
        
        self.client.login(username='testuser', password='testpass123')
        self.client.get(
            reverse('system_notifications:notification_detail', args=[self.notification.pk])
        )
        
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
    
    def test_cannot_view_other_user_notification(self):
        """他ユーザーの通知は閲覧できない"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('system_notifications:notification_detail', args=[self.other_notification.pk])
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_notification_count_api(self):
        """未読通知数APIのテスト"""
        # 未読通知を追加
        Notification.objects.create(
            user=self.user,
            title='未読通知1',
            message='未読メッセージ1',
        )
        Notification.objects.create(
            user=self.user,
            title='未読通知2',
            message='未読メッセージ2',
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('system_notifications:notification_count'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['unread_count'], 3)  # 最初の1件 + 追加の2件
    
    def test_mark_all_as_read(self):
        """一括既読機能のテスト"""
        # 未読通知を追加
        Notification.objects.create(
            user=self.user,
            title='未読通知1',
            message='未読メッセージ1',
        )
        Notification.objects.create(
            user=self.user,
            title='未読通知2',
            message='未読メッセージ2',
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # 一括既読を実行
        response = self.client.post(reverse('system_notifications:mark_all_as_read'))
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # すべて既読になっているか確認
        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread_count, 0)
