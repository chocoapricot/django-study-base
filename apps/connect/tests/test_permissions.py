from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission
from apps.connect.models import ConnectStaff
from apps.profile.models import StaffProfile, ProfileMynumber

User = get_user_model()

class PermissionGrantingTest(TestCase):
    """権限付与のテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.client.login(username='testuser', password='TestPass123!')

        self.connection = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='test@example.com',
            created_by=self.user,
            updated_by=self.user
        )

    def test_profile_permission_grant_on_approval(self):
        """接続承認時にプロファイル権限が付与されるかテスト"""
        
        # Initially, user should not have profile permissions
        self.assertFalse(self.user.has_perm('profile.view_staffprofile'))
        self.assertFalse(self.user.has_perm('profile.view_profilemynumber'))

        # Approve the connection
        response = self.client.post(reverse('connect:staff_approve', args=[self.connection.pk]))
        self.assertEqual(response.status_code, 302)

        # Refresh user object to get updated permissions
        self.user.refresh_from_db()
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache
        if hasattr(self.user, '_user_perm_cache'):
            del self.user._user_perm_cache

        # Check for permissions
        profile_perms = [
            'view_staffprofile', 'add_staffprofile', 'change_staffprofile', 'delete_staffprofile'
        ]
        mynumber_perms = [
            'view_profilemynumber', 'add_profilemynumber', 'change_profilemynumber', 'delete_profilemynumber'
        ]

        for perm in profile_perms:
            self.assertTrue(self.user.has_perm(f'profile.{perm}'))

        for perm in mynumber_perms:
            self.assertTrue(self.user.has_perm(f'profile.{perm}'))
