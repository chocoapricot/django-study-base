from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission
from apps.profile.models import StaffProfile, StaffProfileMynumber

User = get_user_model()

class ProfilePermissionTest(TestCase):
    """プロファイル機能の権限テスト"""

    def setUp(self):
        self.client = Client()
        self.user_with_perms = User.objects.create_user(
            username='perm_user',
            email='perm@example.com',
            password='TestPass123!'
        )
        self.user_without_perms = User.objects.create_user(
            username='no_perm_user',
            email='no_perm@example.com',
            password='TestPass123!'
        )

        # Add permissions to user_with_perms
        profile_perms = Permission.objects.filter(content_type__app_label='profile')
        for perm in profile_perms:
            self.user_with_perms.user_permissions.add(perm)

        self.profile = StaffProfile.objects.create(user=self.user_with_perms, name_last='test', name_first='user')
        self.mynumber = StaffProfileMynumber.objects.create(user=self.user_with_perms, mynumber='123456789012')
        self.profile_no_perm = StaffProfile.objects.create(user=self.user_without_perms, name_last='no', name_first='perm')
        self.mynumber_no_perm = StaffProfileMynumber.objects.create(user=self.user_without_perms, mynumber='210987654321')


    def test_views_with_permission(self):
        """権限を持つユーザーがビューにアクセスできることをテスト"""
        self.client.login(username='perm_user', password='TestPass123!')
        
        urls = [
            reverse('profile:detail'),
            reverse('profile:edit'),
            reverse('profile:delete'),
            reverse('profile:mynumber_detail'),
            reverse('profile:mynumber_edit'),
            reverse('profile:mynumber_delete'),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 403)

    def test_views_without_permission(self):
        """権限のないユーザーがビューにアクセスできないことをテスト"""
        self.client.login(username='no_perm_user', password='TestPass123!')

        urls = [
            reverse('profile:detail'),
            reverse('profile:edit'),
            reverse('profile:delete'),
            reverse('profile:mynumber_detail'),
            reverse('profile:mynumber_edit'),
            reverse('profile:mynumber_delete'),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
