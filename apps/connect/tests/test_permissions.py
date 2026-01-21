from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission
from apps.connect.models import ConnectStaff
from apps.profile.models import StaffProfile, StaffProfileMynumber

User = get_user_model()

class PermissionGrantingTest(TestCase):
    """権限付与のテスト"""

    def setUp(self):
        from django.contrib.auth.models import Group
        from django.contrib.contenttypes.models import ContentType
        from apps.contract.models import StaffContract
        from apps.kintai.models import StaffTimesheet, StaffTimecard, StaffTimerecord, StaffTimerecordBreak

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

        # --- staff_connected グループのセットアップ ---
        group, _ = Group.objects.get_or_create(name='staff_connected')

        models_to_grant_all = [
            StaffProfile, StaffProfileMynumber,
            StaffTimesheet, StaffTimecard, StaffTimerecord, StaffTimerecordBreak
        ]
        permissions_to_add = []

        for model in models_to_grant_all:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            permissions_to_add.extend(permissions)

        contract_content_type = ContentType.objects.get_for_model(StaffContract)
        contract_permissions = Permission.objects.filter(
            content_type=contract_content_type,
            codename__in=['confirm_staffcontract', 'view_staffcontract']
        )
        permissions_to_add.extend(contract_permissions)
        group.permissions.add(*permissions_to_add)


    def test_profile_permission_grant_on_approval(self):
        """接続承認時にプロファイル権限が付与されるかテスト"""
        
        # Initially, user should not have profile permissions
        self.assertFalse(self.user.has_perm('profile.view_staffprofile'))
        self.assertFalse(self.user.has_perm('profile.view_staffprofilemynumber'))

        # Approve the connection
        response = self.client.post(reverse('connect:staff_approve', args=[self.connection.pk]))
        self.assertEqual(response.status_code, 302)

        # 権限の変更を確実に反映させるため、ユーザーオブジェクトを再取得
        self.user = User.objects.get(pk=self.user.pk)

        # Check for permissions
        profile_perms = [
            'view_staffprofile', 'add_staffprofile', 'change_staffprofile', 'delete_staffprofile'
        ]
        mynumber_perms = [
            'view_staffprofilemynumber', 'add_staffprofilemynumber', 'change_staffprofilemynumber', 'delete_staffprofilemynumber'
        ]

        for perm in profile_perms:
            self.assertTrue(self.user.has_perm(f'profile.{perm}'))

        for perm in mynumber_perms:
            self.assertTrue(self.user.has_perm(f'profile.{perm}'))
