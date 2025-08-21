from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.profile.models import StaffProfile
from apps.connect.models import ConnectStaff, ProfileRequest

User = get_user_model()

class ProfileRequestSignalTest(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='testuser1@example.com',
            password='password',
            first_name='Taro',
            last_name='Yamada'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='testuser2@example.com',
            password='password'
        )

        # Create approved connections
        self.connect_staff1 = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email=self.user1.email,
            status='approved'
        )
        self.connect_staff2 = ConnectStaff.objects.create(
            corporate_number='1234567890124',
            email=self.user2.email,
            status='approved'
        )
        # Create a pending connection
        self.connect_staff_pending = ConnectStaff.objects.create(
            corporate_number='1234567890125',
            email=self.user1.email,
            status='pending'
        )

    def test_request_creation_on_profile_create(self):
        """
        A ProfileRequest should be created when a StaffProfile is created.
        """
        # Create a StaffProfile
        staff_profile = StaffProfile.objects.create(user=self.user1)

        # Check if one ProfileRequest was created
        self.assertEqual(ProfileRequest.objects.count(), 1)
        request = ProfileRequest.objects.first()
        self.assertEqual(request.connect_staff, self.connect_staff1)
        self.assertEqual(request.staff_profile, staff_profile)
        self.assertEqual(request.status, 'pending')

    def test_request_recreation_on_profile_update(self):
        """
        The ProfileRequest should be recreated when a StaffProfile is updated.
        """
        # Create the StaffProfile first
        staff_profile = StaffProfile.objects.create(user=self.user1)
        self.assertEqual(ProfileRequest.objects.count(), 1)
        original_request = ProfileRequest.objects.first()
        original_request_id = original_request.id

        # Update the StaffProfile
        staff_profile.name_first = 'Jiro'
        staff_profile.save()

        # Check if the old request was deleted and a new one was created
        self.assertFalse(ProfileRequest.objects.filter(id=original_request_id).exists())
        self.assertEqual(ProfileRequest.objects.count(), 1)
        updated_request = ProfileRequest.objects.first()
        self.assertEqual(updated_request.connect_staff, self.connect_staff1)
        self.assertEqual(updated_request.staff_profile, staff_profile)
        self.assertNotEqual(updated_request.id, original_request_id)

    def test_no_request_if_no_approved_connection(self):
        """
        A ProfileRequest should not be created if there is no approved connection.
        """
        # Create a user with no connection
        user_no_connection = User.objects.create_user(
            username='nouser', email='nouser@example.com', password='password'
        )
        StaffProfile.objects.create(user=user_no_connection)

        # Check that no ProfileRequest was created
        self.assertEqual(ProfileRequest.objects.count(), 0)

    def test_multiple_connections(self):
        """
        Test case for a user with multiple approved connections.
        """
        # Add another approved connection for the same user
        ConnectStaff.objects.create(
            corporate_number='9998887776665',
            email=self.user1.email,
            status='approved'
        )

        # Create a StaffProfile
        StaffProfile.objects.create(user=self.user1)

        # Check if two ProfileRequests were created
        self.assertEqual(ProfileRequest.objects.count(), 2)
        self.assertEqual(ProfileRequest.objects.filter(staff_profile__user=self.user1).count(), 2)
