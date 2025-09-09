from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from apps.company.models import Company
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.master.models import StaffAgreement
from apps.contract.models import StaffContract

class StaffContractConfirmTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password',
            is_staff=True,
            is_active=True,
        )
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123',
        )
        self.staff = Staff.objects.create(
            email='testuser@example.com',
            name_last='Test',
            name_first='User',
        )
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.user.email,
            status='approved',
        )
        self.staff_agreement = StaffAgreement.objects.create(
            name='Test Agreement',
            agreement_text='This is a test agreement.',
            corporation_number=self.company.corporate_number,
        )
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='Test Contract',
            contract_status='40', # Issued
            start_date='2025-01-01',
        )

    def test_staff_contract_confirm_list_get(self):
        """
        Test GET request to staff_contract_confirm_list view.
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ契約確認')
        self.assertContains(response, 'Test Contract')
        self.assertContains(response, '発行済')

    def test_staff_contract_confirm_list_post(self):
        """
        Test POST request to staff_contract_confirm_list view to confirm a contract.
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.post(reverse('contract:staff_contract_confirm_list'), {'contract_id': self.contract.id, 'action': 'confirm'})
        self.assertEqual(response.status_code, 302) # Should redirect

        # Check if the agreement was created
        self.assertTrue(
            ConnectStaffAgree.objects.filter(
                email=self.user.email,
                corporate_number=self.company.corporate_number,
                staff_agreement=self.staff_agreement,
                is_agreed=True
            ).exists()
        )
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, '50') # Confirmed

    def test_staff_contract_unconfirm(self):
        """
        Test POST request to staff_contract_confirm_list view to un-confirm a contract.
        """
        # First, confirm the contract
        self.contract.contract_status = '50' # Confirmed
        self.contract.save()

        self.client.login(email='testuser@example.com', password='password')
        response = self.client.post(reverse('contract:staff_contract_confirm_list'), {'contract_id': self.contract.id, 'action': 'unconfirm'})
        self.assertEqual(response.status_code, 302) # Should redirect

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, '40') # Issued
