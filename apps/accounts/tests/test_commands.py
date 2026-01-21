import csv
import os
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from allauth.account.models import EmailAddress
from apps.profile.models import StaffProfile
from apps.contract.models import StaffContract, ClientContract
from apps.connect.models import ConnectClient

User = get_user_model()

class ImportUsersCommandTest(TestCase):
    def setUp(self):
        self.csv_file_path = 'test_users.csv'
        # clientグループと関連権限のセットアップ
        self.client_group, _ = Group.objects.get_or_create(name='client')

        # 権限とモデルをマッピング
        permissions_map = {
            'view_connectclient': ConnectClient,
            'change_connectclient': ConnectClient,
            'confirm_clientcontract': ClientContract,
        }

        for codename, model_cls in permissions_map.items():
            content_type = ContentType.objects.get_for_model(model_cls)
            permission, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
            )
            self.client_group.permissions.add(permission)

    def tearDown(self):
        if os.path.exists(self.csv_file_path):
            os.remove(self.csv_file_path)

    def test_import_users_command(self):
        """
        Test that users are imported correctly from a CSV file.
        """
        csv_data = [
            ['testuser1', 'password123', 'test1@example.com', 'User', 'Test'],
            ['testuser2', 'password456', 'test2@example.com', 'UserTwo', 'Test'],
        ]

        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

        # StringIO is used to capture the output of the command
        out = StringIO()
        call_command('import_users', self.csv_file_path, stdout=out)

        self.assertIn('Successfully created user "testuser1"', out.getvalue())
        self.assertIn('Successfully created user "testuser2"', out.getvalue())

        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(EmailAddress.objects.count(), 2)

        user1 = User.objects.get(username='testuser1')
        self.assertEqual(user1.email, 'test1@example.com')
        self.assertEqual(user1.last_name, 'User')
        self.assertEqual(user1.first_name, 'Test')
        self.assertTrue(user1.check_password('password123'))

        email1 = EmailAddress.objects.get(user=user1)
        self.assertTrue(email1.primary)
        self.assertTrue(email1.verified)

    def test_import_staff_user_with_permissions(self):
        """
        Test that staff users are imported with correct groups.
        """
        csv_data = [
            ['staffuser', 'password123', 'staff@example.com', 'Staff', 'User', 'staff'],
        ]

        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

        out = StringIO()
        call_command('import_users', self.csv_file_path, stdout=out)

        self.assertIn('Successfully created staff user "staffuser" and added to staff/staff_connected groups.', out.getvalue())

        user = User.objects.get(username='staffuser')
        self.assertTrue(user.groups.filter(name='staff').exists())
        self.assertTrue(user.groups.filter(name='staff_connected').exists())

    def test_import_client_user_with_permissions(self):
        """
        Test that client users are imported with correct groups.
        """
        csv_data = [
            ['clientuser', 'password123', 'client@example.com', 'Client', 'User', 'client'],
        ]

        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

        out = StringIO()
        call_command('import_users', self.csv_file_path, stdout=out)

        self.assertIn('Successfully created client user "clientuser" and added to client/client_connected groups.', out.getvalue())

        user = User.objects.get(username='clientuser')
        self.assertTrue(user.groups.filter(name='client').exists())
        self.assertTrue(user.groups.filter(name='client_connected').exists())

    def test_import_users_backward_compatibility(self):
        """
        Test that the command still works with 5-column CSV (backward compatibility).
        """
        csv_data = [
            ['olduser', 'password123', 'old@example.com', 'Old', 'User'],
        ]

        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

        out = StringIO()
        call_command('import_users', self.csv_file_path, stdout=out)

        self.assertIn('Successfully created user "olduser"', out.getvalue())

        user = User.objects.get(username='olduser')
        self.assertEqual(user.email, 'old@example.com')
        
        # 特別な権限が付与されていないことを確認
        # （スタッフ契約確認権限がないことを確認）
        content_type = ContentType.objects.get_for_model(StaffContract)
        self.assertFalse(
            user.has_perm(f'{content_type.app_label}.confirm_staffcontract'),
            'User should not have staff contract confirmation permission'
        )

