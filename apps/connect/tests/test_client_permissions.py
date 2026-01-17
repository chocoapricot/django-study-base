from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

from apps.connect.models import ConnectClient
from apps.connect.utils import grant_client_connect_permissions
from apps.connect.views import connect_client_approve

User = get_user_model()

class ClientDirectPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testclient',
            email='testclient@example.com',
            password='password'
        )
        self.staff_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password',
            is_staff=True
        )

    def test_grant_client_connect_permissions_direct_assignment(self):
        """Test that the function grants connect permissions directly to the user."""
        # Execute the function
        grant_client_connect_permissions(self.user)

        # Verify the permissions
        self.assertTrue(self.user.has_perm('connect.view_connectclient'))
        self.assertTrue(self.user.has_perm('connect.change_connectclient'))

    def test_connect_client_approve_grants_contract_permission(self):
        """Test that the approval view grants the contract confirmation permission."""
        # Setup: Create a connection request
        connect_request = ConnectClient.objects.create(
            corporate_number='1234567890123',
            email=self.user.email,
            created_by=self.staff_user,
            updated_by=self.staff_user,
            status='pending'
        )

        # Initially, the user should not have the permission
        self.assertFalse(self.user.has_perm('contract.confirm_clientcontract'))

        # Setup: Create a dummy request
        factory = RequestFactory()
        request = factory.post(f'/connect/client/{connect_request.pk}/approve/')
        request.user = self.staff_user

        # Add middleware for session and messages
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        middleware = MessageMiddleware(lambda r: None)
        middleware.process_request(request)

        # Execute the approval view
        response = connect_client_approve(request, connect_request.pk)

        # Verification
        self.assertEqual(response.status_code, 302) # Should redirect

        # Re-fetch the user from the database to clear any permission caches
        self.user = User.objects.get(pk=self.user.pk)

        # Now the user should have the contract confirmation permission
        self.assertTrue(self.user.has_perm('contract.confirm_clientcontract'))
