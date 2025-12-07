from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

class NotificationTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123', email='user1@example.com')
        self.user2 = User.objects.create_user(username='user2', password='password123', email='user2@example.com')
        self.notification1 = Notification.objects.create(user=self.user1, title='Test Notification 1', message='This is a test.')
        self.notification2 = Notification.objects.create(user=self.user1, title='Test Notification 2', message='This is another test.', is_read=True)
        self.notification3 = Notification.objects.create(user=self.user2, title='Test Notification 3', message='This is for user 2.')

    def test_notification_list_view_authenticated(self):
        self.client.login(email='user1@example.com', password='password123')
        response = self.client.get(reverse('notification:notification_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.notification1.title)
        self.assertContains(response, self.notification2.title)
        self.assertNotContains(response, self.notification3.title)
        self.assertTemplateUsed(response, 'notification/notification_list.html')

    def test_notification_list_view_unauthenticated(self):
        response = self.client.get(reverse('notification:notification_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/system/notifications/')

    def test_notification_detail_view(self):
        self.client.login(email='user1@example.com', password='password123')

        # 最初は未読のはず
        self.assertFalse(self.notification1.is_read)

        response = self.client.get(reverse('notification:notification_detail', args=[self.notification1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.notification1.title)
        self.assertContains(response, self.notification1.message)
        self.assertTemplateUsed(response, 'notification/notification_detail.html')

        # 詳細ビューにアクセスした後、既読になっていることを確認
        self.notification1.refresh_from_db()
        self.assertTrue(self.notification1.is_read)

    def test_other_user_cannot_see_notification_detail(self):
        self.client.login(email='user2@example.com', password='password123')
        response = self.client.get(reverse('notification:notification_detail', args=[self.notification1.pk]))
        self.assertEqual(response.status_code, 404)

    def test_unread_notification_context_processor(self):
        self.client.login(email='user1@example.com', password='password123')
        response = self.client.get(reverse('home:home'))
        self.assertEqual(response.context['unread_notification_count'], 1)

        # 既読にする
        self.notification1.is_read = True
        self.notification1.save()

        response = self.client.get(reverse('home:home'))
        self.assertEqual(response.context['unread_notification_count'], 0)
