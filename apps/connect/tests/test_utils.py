from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch, MagicMock

from apps.connect.models import ConnectStaff, ConnectClient
from apps.connect.utils import (
    grant_profile_permissions,
    grant_connect_permissions,
    check_and_grant_permissions_for_email,
    grant_permissions_on_connection_request,
    grant_client_connect_permissions,
    check_and_grant_client_permissions_for_email,
    grant_client_permissions_on_connection_request,
    grant_staff_contract_confirmation_permission,
)
from apps.profile.models import (
    StaffProfile,
    StaffProfileMynumber,
    StaffProfileBank,
    StaffProfileContact,
    StaffProfileInternational,
    StaffProfileDisability,
)
from apps.contract.models import StaffContract, ClientContract

User = get_user_model()


class UtilsPermissionGrantingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password"
        )
        # clientグループと関連権限のセットアップ
        self.client_group, _ = Group.objects.get_or_create(name='client')
        client_permissions = [
            'view_connectclient',
            'change_connectclient',
        ]
        for perm_codename in client_permissions:
            permission = Permission.objects.get(codename=perm_codename)
            self.client_group.permissions.add(permission)

    def test_grant_profile_permissions_success(self):
        """Test that profile permissions are granted successfully."""
        result = grant_profile_permissions(self.user)
        self.assertTrue(result)

        models_to_check = [
            StaffProfile,
            StaffProfileMynumber,
            StaffProfileBank,
            StaffProfileContact,
            StaffProfileInternational,
            StaffProfileDisability,
        ]

        for model_class in models_to_check:
            content_type = ContentType.objects.get_for_model(model_class)
            permissions = Permission.objects.filter(content_type=content_type)
            for permission in permissions:
                self.assertTrue(self.user.has_perm(f"{permission.content_type.app_label}.{permission.codename}"))

    @patch('apps.connect.utils.ContentType.objects.get_for_model')
    def test_grant_profile_permissions_failure(self, mock_get_for_model):
        """Test that grant_profile_permissions returns False on exception."""
        mock_get_for_model.side_effect = Exception("Test exception")
        result = grant_profile_permissions(self.user)
        self.assertFalse(result)

    def test_grant_connect_permissions_success(self):
        """Test that connect permissions are granted successfully."""
        result = grant_connect_permissions(self.user)
        self.assertTrue(result)
        self.assertTrue(self.user.has_perm('connect.view_connectstaff'))
        self.assertTrue(self.user.has_perm('connect.change_connectstaff'))

    @patch('apps.connect.utils.ContentType.objects.get_for_model')
    def test_grant_connect_permissions_failure(self, mock_get_for_model):
        """Test that grant_connect_permissions returns False on exception."""
        mock_get_for_model.side_effect = Exception("Test exception")
        result = grant_connect_permissions(self.user)
        self.assertFalse(result)

    def test_check_and_grant_permissions_for_email_user_does_not_exist(self):
        """Test that the function returns False if the user does not exist."""
        result = check_and_grant_permissions_for_email('nonexistent@example.com')
        self.assertFalse(result)

    def test_check_and_grant_permissions_for_email_no_connections(self):
        """Test that the function returns False if there are no connections."""
        result = check_and_grant_permissions_for_email(self.user.email)
        self.assertFalse(result)

    def test_check_and_grant_permissions_for_email_success(self):
        """Test that permissions are granted if a connection exists."""
        ConnectStaff.objects.create(email=self.user.email, corporate_number='12345')
        result = check_and_grant_permissions_for_email(self.user.email)
        self.assertTrue(result)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_perm('connect.view_connectstaff'))
        self.assertTrue(self.user.has_perm('connect.change_connectstaff'))

    @patch('apps.connect.utils.User.objects.get')
    def test_check_and_grant_permissions_for_email_exception(self, mock_user_get):
        """Test that the function returns False on a generic exception."""
        mock_user_get.side_effect = Exception("Test exception")
        result = check_and_grant_permissions_for_email(self.user.email)
        self.assertFalse(result)

    def test_grant_permissions_on_connection_request_success(self):
        """Test that permissions are granted on connection request."""
        result = grant_permissions_on_connection_request(self.user.email)
        self.assertTrue(result)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_perm('connect.view_connectstaff'))
        self.assertTrue(self.user.has_perm('connect.change_connectstaff'))

    def test_grant_permissions_on_connection_request_user_does_not_exist(self):
        """Test that the function returns False if the user does not exist."""
        result = grant_permissions_on_connection_request('nonexistent@example.com')
        self.assertFalse(result)

    @patch('apps.connect.utils.User.objects.get')
    def test_grant_permissions_on_connection_request_exception(self, mock_user_get):
        """Test that the function returns False on a generic exception."""
        mock_user_get.side_effect = Exception("Test exception")
        result = grant_permissions_on_connection_request(self.user.email)
        self.assertFalse(result)

    def test_grant_client_connect_permissions_success(self):
        """Test that client connect permissions are granted successfully."""
        result = grant_client_connect_permissions(self.user)
        self.assertTrue(result)
        self.assertTrue(self.user.has_perm('connect.view_connectclient'))
        self.assertTrue(self.user.has_perm('connect.change_connectclient'))

    @patch('django.contrib.auth.models.Group.objects.get_or_create')
    def test_grant_client_connect_permissions_failure(self, mock_get_or_create):
        """Test that grant_client_connect_permissions returns False on exception."""
        mock_get_or_create.side_effect = Exception("Test exception")
        result = grant_client_connect_permissions(self.user)
        self.assertFalse(result)

    def test_check_and_grant_client_permissions_for_email_user_does_not_exist(self):
        """Test that the function returns False if the user does not exist."""
        result = check_and_grant_client_permissions_for_email('nonexistent@example.com')
        self.assertFalse(result)

    def test_check_and_grant_client_permissions_for_email_no_connections(self):
        """Test that the function returns False if there are no connections."""
        result = check_and_grant_client_permissions_for_email(self.user.email)
        self.assertFalse(result)

    def test_check_and_grant_client_permissions_for_email_success(self):
        """Test that permissions are granted if a client connection exists."""
        ConnectClient.objects.create(email=self.user.email, corporate_number='12345')
        result = check_and_grant_client_permissions_for_email(self.user.email)
        self.assertTrue(result)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_perm('connect.view_connectclient'))
        self.assertTrue(self.user.has_perm('connect.change_connectclient'))

    @patch('apps.connect.utils.User.objects.get')
    def test_check_and_grant_client_permissions_for_email_exception(self, mock_user_get):
        """Test that the function returns False on a generic exception."""
        mock_user_get.side_effect = Exception("Test exception")
        result = check_and_grant_client_permissions_for_email(self.user.email)
        self.assertFalse(result)

    def test_grant_client_permissions_on_connection_request_success(self):
        """Test that client permissions are granted on connection request."""
        result = grant_client_permissions_on_connection_request(self.user.email)
        self.assertTrue(result)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_perm('connect.view_connectclient'))
        self.assertTrue(self.user.has_perm('connect.change_connectclient'))

    def test_grant_client_permissions_on_connection_request_user_does_not_exist(self):
        """Test that the function returns False if the user does not exist."""
        result = grant_client_permissions_on_connection_request('nonexistent@example.com')
        self.assertFalse(result)

    @patch('apps.connect.utils.User.objects.get')
    def test_grant_client_permissions_on_connection_request_exception(self, mock_user_get):
        """Test that the function returns False on a generic exception."""
        mock_user_get.side_effect = Exception("Test exception")
        result = grant_client_permissions_on_connection_request(self.user.email)
        self.assertFalse(result)

    def test_grant_staff_contract_confirmation_permission_success(self):
        """Test that staff contract confirmation permission is granted successfully."""
        # The permission should be created by migrations, so we just need to grant it.
        result = grant_staff_contract_confirmation_permission(self.user)
        self.assertTrue(result)
        self.assertTrue(self.user.has_perm('contract.confirm_staffcontract'))

    @patch('apps.connect.utils.Permission.objects.get')
    def test_grant_staff_contract_confirmation_permission_failure(self, mock_perm_get):
        """Test that the function returns False on exception."""
        mock_perm_get.side_effect = Exception("Test exception")
        result = grant_staff_contract_confirmation_permission(self.user)
        self.assertFalse(result)

