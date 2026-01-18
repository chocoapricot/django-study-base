from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from ..models import TimePunch

class TimePunchViewPermissionTest(TestCase):
    """
    TimePunch views permission tests.
    """
    def setUp(self):
        """
        Set up the test environment.
        """
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.time_punch = TimePunch.objects.create(name='Test Time Punch')
        self.content_type = ContentType.objects.get_for_model(TimePunch)

    def test_time_punch_list_view_permission(self):
        """
        Test that the time_punch_list view requires the correct permission.
        """
        url = reverse('master:time_punch_list')
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='view_timepunch')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_time_punch_create_view_permission(self):
        """
        Test that the time_punch_create view requires the correct permission.
        """
        url = reverse('master:time_punch_create')
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='add_timepunch')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_time_punch_edit_view_permission(self):
        """
        Test that the time_punch_edit view requires the correct permission.
        """
        url = reverse('master:time_punch_edit', args=[self.time_punch.pk])
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='change_timepunch')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_time_punch_delete_confirm_view_permission(self):
        """
        Test that the time_punch_delete_confirm view requires the correct permission.
        """
        url = reverse('master:time_punch_delete_confirm', args=[self.time_punch.pk])
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='delete_timepunch')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_time_punch_delete_view_permission(self):
        """
        Test that the time_punch_delete view requires the correct permission.
        """
        url = reverse('master:time_punch_delete', args=[self.time_punch.pk])
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='delete_timepunch')
        self.user.user_permissions.add(permission)
        # Re-create the object as it might have been deleted in other tests
        self.time_punch_for_delete = TimePunch.objects.create(name='Test Time Punch for Delete')
        url_for_delete = reverse('master:time_punch_delete', args=[self.time_punch_for_delete.pk])
        response = self.client.post(url_for_delete)
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)

    def test_time_punch_change_history_list_view_permission(self):
        """
        Test that the time_punch_change_history_list view requires the correct permission.
        """
        url = reverse('master:time_punch_change_history_list')
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='view_timepunch')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
