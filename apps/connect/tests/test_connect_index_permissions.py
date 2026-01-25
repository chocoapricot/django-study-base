from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

User = get_user_model()

class ConnectIndexPermissionTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password'
        )
        self.client.login(email='testuser@example.com', password='password')
        self.url = reverse('connect:index')

    def test_no_permissions(self):
        """
        User with no permissions should be forbidden.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_only_view_connectclient_permission(self):
        """
        User with only 'view_connectclient' permission should be forbidden.
        """
        permission = Permission.objects.get(codename='view_connectclient', content_type__app_label='connect')
        self.user.user_permissions.add(permission)
        # Re-login to refresh permissions in session
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_only_view_connectstaff_permission(self):
        """
        User with only 'view_connectstaff' permission should be forbidden.
        """
        permission = Permission.objects.get(codename='view_connectstaff', content_type__app_label='connect')
        self.user.user_permissions.add(permission)
        # Re-login to refresh permissions in session
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_both_permissions(self):
        """
        User with both permissions should be allowed.
        """
        view_client_perm = Permission.objects.get(codename='view_connectclient', content_type__app_label='connect')
        view_staff_perm = Permission.objects.get(codename='view_connectstaff', content_type__app_label='connect')
        self.user.user_permissions.add(view_client_perm, view_staff_perm)
        # Re-login to refresh permissions in session
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
