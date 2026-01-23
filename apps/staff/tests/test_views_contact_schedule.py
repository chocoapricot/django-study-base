from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.staff.models import Staff, StaffContactSchedule
from apps.system.settings.models import Dropdowns

User = get_user_model()

class StaffContactScheduleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.staff = Staff.objects.create(name_last='山田', name_first='太郎')
        self.schedule = StaffContactSchedule.objects.create(
            staff=self.staff,
            contact_date='2025-01-01',
            content='テスト連絡予定'
        )
        Dropdowns.objects.create(category='contact_type', value='1', name='テスト', disp_seq=1)
        self.client.login(username='testuser', password='password')

    def test_contact_schedule_create_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('staff:staff_contact_schedule_create', kwargs={'staff_pk': self.staff.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='add_staffcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, {
            'contact_date': '2025-01-02',
            'content': '新しい連絡予定',
            'contact_type': 1,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffContactSchedule.objects.filter(content='新しい連絡予定').exists())

    def test_contact_schedule_list_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('staff:staff_contact_schedule_list', kwargs={'staff_pk': self.staff.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='view_staffcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト連絡予定')

    def test_contact_schedule_detail_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('staff:staff_contact_schedule_detail', kwargs={'pk': self.schedule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='view_staffcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト連絡予定')

    def test_contact_schedule_update_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('staff:staff_contact_schedule_update', kwargs={'pk': self.schedule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='change_staffcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, {
            'contact_date': '2025-01-01',
            'content': '更新された連絡予定',
            'contact_type': 1,
        })
        self.assertEqual(response.status_code, 302)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.content, '更新された連絡予定')

    def test_contact_schedule_delete_view(self):
        self.client.login(username='testuser', password='password')
        url = reverse('staff:staff_contact_schedule_delete', kwargs={'pk': self.schedule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # permission denied

        permission = Permission.objects.get(codename='delete_staffcontactschedule')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffContactSchedule.objects.filter(pk=self.schedule.pk).exists())
