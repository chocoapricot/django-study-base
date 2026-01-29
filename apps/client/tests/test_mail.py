from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.client.models import Client, ClientUser
from apps.master.models import ClientContactType
from apps.system.notifications.models import Notification

User = get_user_model()

class ClientMailTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')
        self.client.login(username='admin', password='password')

        # 連絡種別のマスタを作成（ClientUserMailForm内部で使用）
        ClientContactType.objects.create(display_order=50, name='メール配信', is_active=True)

        # テスト用クライアント
        self.client_obj = Client.objects.create(name='テストクライアント')
        
        # テスト用クライアント担当者
        self.client_user_email = 'client_user@example.com'
        self.client_user = ClientUser.objects.create(
            client=self.client_obj,
            name_last='佐藤',
            name_first='一朗',
            email=self.client_user_email
        )

        # クライアント担当者に対応するユーザーを作成
        self.target_user = User.objects.create_user(
            username='client_user_login',
            email=self.client_user_email,
            password='password'
        )

    def test_mail_send_page_renders_notification_checkbox(self):
        """メール送信ページに通知チェックボックスが表示されることを確認"""
        url = reverse('client:client_user_mail_send', args=[self.client_user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="send_notification"')
        self.assertContains(response, '通知を送る')

    def test_mail_send_creates_notification_when_checked(self):
        """チェックを入れた場合に通知が作成されることを確認"""
        url = reverse('client:client_user_mail_send', args=[self.client_user.pk])
        data = {
            'to_email': self.client_user_email,
            'subject': 'クライアントテスト件名',
            'body': 'クライアントテスト本文',
            'send_notification': True
        }
        
        # 通知が0件であることを確認
        self.assertEqual(Notification.objects.filter(user=self.target_user).count(), 0)
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # リダイレクト
        
        # 通知が1件作成されていることを確認
        self.assertEqual(Notification.objects.filter(user=self.target_user).count(), 1)
        notification = Notification.objects.filter(user=self.target_user).first()
        self.assertEqual(notification.title, 'クライアントテスト件名')
        self.assertEqual(notification.message, 'クライアントテスト本文')

    def test_mail_send_does_not_create_notification_when_unchecked(self):
        """チェックを外した場合に通知が作成されないことを確認"""
        url = reverse('client:client_user_mail_send', args=[self.client_user.pk])
        data = {
            'to_email': self.client_user_email,
            'subject': '通知なし件名',
            'body': '通知なし本文',
            # send_notification は送信しない（=False）
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # 通知が作成されていないことを確認
        self.assertEqual(Notification.objects.filter(user=self.target_user).count(), 0)

    def test_mail_send_does_not_fail_if_user_not_exists(self):
        """ユーザーが存在しない場合でもエラーにならず、通知だけ作成されないことを確認"""
        # ユーザーが存在しない別の担当者を作成
        other_user = ClientUser.objects.create(
            client=self.client_obj,
            name_last='山崎',
            name_first='太郎',
            email='no_user_client@example.com'
        )
        
        url = reverse('client:client_user_mail_send', args=[other_user.pk])
        data = {
            'to_email': 'no_user_client@example.com',
            'subject': 'ユーザーなしクライアント',
            'body': '本文',
            'send_notification': True
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # 通知が作成されていないことを確認
        self.assertEqual(Notification.objects.filter(title='ユーザーなしクライアント').count(), 0)
