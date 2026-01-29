from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.client.models import Client, ClientContactSchedule
from apps.system.settings.models import Dropdowns

User = get_user_model()

class ClientContactScheduleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client_obj = Client.objects.create(corporate_number='1234567890123', name='Test Client', name_furigana='テストクライアント')
        self.schedule = ClientContactSchedule.objects.create(
            client=self.client_obj,
            contact_date='2025-01-01',
            content='テスト連絡予定'
        )
        from apps.master.models import ClientContactType
        self.contact_type = ClientContactType.objects.create(name='テスト', display_order=10, is_active=True)
        self.client.login(username='testuser', password='password')

    def test_contact_schedule_list_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('client:client_contact_schedule_list', kwargs={'client_pk': self.client_obj.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='view_clientcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト連絡予定')

    def test_contact_schedule_create_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('client:client_contact_schedule_create', kwargs={'client_pk': self.client_obj.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='add_clientcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, {
            'contact_date': '2025-01-02',
            'content': '新しい連絡予定',
            'contact_type': self.contact_type.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientContactSchedule.objects.filter(content='新しい連絡予定').exists())

    def test_contact_schedule_update_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('client:client_contact_schedule_update', kwargs={'pk': self.schedule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='change_clientcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, {
            'contact_date': '2025-01-01',
            'content': '更新された連絡予定',
            'contact_type': self.contact_type.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.content, '更新された連絡予定')

    def test_contact_schedule_delete_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('client:client_contact_schedule_delete', kwargs={'pk': self.schedule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='delete_clientcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClientContactSchedule.objects.filter(pk=self.schedule.pk).exists())

    def test_contact_schedule_detail_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('client:client_contact_schedule_detail', kwargs={'pk': self.schedule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='view_clientcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト連絡予定')
