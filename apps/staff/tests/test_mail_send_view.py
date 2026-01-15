from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.staff.models import Staff
from apps.connect.models import ConnectStaff
from apps.company.models import Company, CompanyUser

User = get_user_model()

class StaffMailSendViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password', email='testuser@example.com')
        # Grant permission to view staff
        permission = Permission.objects.get(codename='view_staff', content_type__app_label='staff')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')

        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        CompanyUser.objects.create(
            email=self.user.email,
            corporate_number=self.company.corporate_number,
            name_last='Test',
            name_first='User'
        )

        # Staff with approved connection
        self.approved_staff = Staff.objects.create(
            name='Approved Staff',
            email='approved@example.com',
            name_last='Approved',
            name_first='Staff'
        )
        ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.approved_staff.email,
            status='approved'
        )

        # Staff with pending connection
        self.pending_staff = Staff.objects.create(
            name='Pending Staff',
            email='pending@example.com',
            name_last='Pending',
            name_first='Staff'
        )
        ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.pending_staff.email,
            status='pending'
        )

    def test_send_notification_visible_for_approved_staff(self):
        """
        Test that the 'Send Notification' checkbox is visible for staff with an approved connection.
        """
        url = reverse('staff:staff_mail_send', kwargs={'pk': self.approved_staff.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'send_notification')

    def test_send_notification_hidden_for_pending_staff(self):
        """
        Test that the 'Send Notification' checkbox is hidden for staff with a pending connection.
        """
        url = reverse('staff:staff_mail_send', kwargs={'pk': self.pending_staff.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'send_notification')
