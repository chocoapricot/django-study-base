from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffMynumber, StaffContact, StaffBank, StaffDisability, StaffInternational
from datetime import date
from apps.connect.models import ConnectStaff, MynumberRequest, BankRequest, ConnectInternationalRequest, DisabilityRequest, ContactRequest
from apps.profile.models import StaffProfile, StaffProfileMynumber, StaffProfileBank, StaffProfileInternational

User = get_user_model()

class StaffViewsOtherTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='スタッフ',
            name_kana_last='テスト',
            name_kana_first='スタッフ',
            employee_no='EMP001'
        )

        # Mynumber Permissions
        mynumber_ct = ContentType.objects.get_for_model(StaffMynumber)
        self.view_mynumber_perm = Permission.objects.get(codename='view_staffmynumber', content_type=mynumber_ct)
        self.add_mynumber_perm = Permission.objects.get(codename='add_staffmynumber', content_type=mynumber_ct)
        self.change_mynumber_perm = Permission.objects.get(codename='change_staffmynumber', content_type=mynumber_ct)
        self.delete_mynumber_perm = Permission.objects.get(codename='delete_staffmynumber', content_type=mynumber_ct)

        # Contact Permissions
        contact_ct = ContentType.objects.get_for_model(StaffContact)
        self.view_contact_perm = Permission.objects.get(codename='view_staffcontact', content_type=contact_ct)
        self.add_contact_perm = Permission.objects.get(codename='add_staffcontact', content_type=contact_ct)
        self.change_contact_perm = Permission.objects.get(codename='change_staffcontact', content_type=contact_ct)
        self.delete_contact_perm = Permission.objects.get(codename='delete_staffcontact', content_type=contact_ct)

        # Bank Permissions
        bank_ct = ContentType.objects.get_for_model(StaffBank)
        self.view_bank_perm = Permission.objects.get(codename='view_staffbank', content_type=bank_ct)
        self.add_bank_perm = Permission.objects.get(codename='add_staffbank', content_type=bank_ct)
        self.change_bank_perm = Permission.objects.get(codename='change_staffbank', content_type=bank_ct)
        self.delete_bank_perm = Permission.objects.get(codename='delete_staffbank', content_type=bank_ct)

        # Disability Permissions
        disability_ct = ContentType.objects.get_for_model(StaffDisability)
        self.view_disability_perm = Permission.objects.get(codename='view_staffdisability', content_type=disability_ct)
        self.add_disability_perm = Permission.objects.get(codename='add_staffdisability', content_type=disability_ct)
        self.change_disability_perm = Permission.objects.get(codename='change_staffdisability', content_type=disability_ct)
        self.delete_disability_perm = Permission.objects.get(codename='delete_staffdisability', content_type=disability_ct)

        # International Permissions
        international_ct = ContentType.objects.get_for_model(StaffInternational)
        self.view_international_perm = Permission.objects.get(codename='view_staffinternational', content_type=international_ct)
        self.add_international_perm = Permission.objects.get(codename='add_staffinternational', content_type=international_ct)
        self.change_international_perm = Permission.objects.get(codename='change_staffinternational', content_type=international_ct)
        self.delete_international_perm = Permission.objects.get(codename='delete_staffinternational', content_type=international_ct)

        # ConnectStaff and Request models setup
        self.staff.email = 'staff@example.com'
        self.staff.save()
        self.connect_staff = ConnectStaff.objects.create(email=self.staff.email, corporate_number='1234567890123', status='approved')

        self.staff_profile = StaffProfile.objects.create(user=self.user, name_last='プロファイル', name_first='姓')

        self.mynumber_profile = StaffProfileMynumber.objects.create(user=self.user, mynumber='123456789012')
        self.mynumber_request = MynumberRequest.objects.create(connect_staff=self.connect_staff, profile_mynumber=self.mynumber_profile, status='pending')

        self.bank_profile = StaffProfileBank.objects.create(user=self.user, bank_code='1234', branch_code='123', account_type='普通', account_number='1234567', account_holder='テスト タロウ')
        self.bank_request = BankRequest.objects.create(connect_staff=self.connect_staff, staff_bank_profile=self.bank_profile, status='pending')

        self.international_profile = StaffProfileInternational.objects.create(user=self.user, residence_card_number='AB12345678CD', residence_status='Engineer', residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1))
        self.international_request = ConnectInternationalRequest.objects.create(connect_staff=self.connect_staff, profile_international=self.international_profile, status='pending')

    # --- Mynumber View Tests ---
    def test_mynumber_detail_view_with_permission(self):
        StaffMynumber.objects.create(staff=self.staff, mynumber="123456789012")
        self.user.user_permissions.add(self.view_mynumber_perm)
        response = self.client.get(reverse('staff:staff_mynumber_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_mynumber_detail_view_without_permission(self):
        StaffMynumber.objects.create(staff=self.staff, mynumber="123456789012")
        response = self.client.get(reverse('staff:staff_mynumber_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_mynumber_create_view_with_permission(self):
        self.user.user_permissions.add(self.add_mynumber_perm)
        response = self.client.get(reverse('staff:staff_mynumber_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_mynumber_create_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_mynumber_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_mynumber_edit_view_with_permission(self):
        StaffMynumber.objects.create(staff=self.staff, mynumber="123456789012")
        self.user.user_permissions.add(self.change_mynumber_perm)
        response = self.client.get(reverse('staff:staff_mynumber_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_mynumber_edit_view_without_permission(self):
        StaffMynumber.objects.create(staff=self.staff, mynumber="123456789012")
        response = self.client.get(reverse('staff:staff_mynumber_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_mynumber_delete_view_with_permission(self):
        StaffMynumber.objects.create(staff=self.staff, mynumber="123456789012")
        self.user.user_permissions.add(self.delete_mynumber_perm)
        response = self.client.get(reverse('staff:staff_mynumber_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_mynumber_delete_view_without_permission(self):
        StaffMynumber.objects.create(staff=self.staff, mynumber="123456789012")
        response = self.client.get(reverse('staff:staff_mynumber_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    # --- Bank View Tests ---
    def test_bank_detail_view_with_permission(self):
        StaffBank.objects.create(staff=self.staff, bank_code='1234', branch_code='123', account_type='普通', account_number='1234567', account_holder='テスト スタッフ')
        self.user.user_permissions.add(self.view_bank_perm)
        response = self.client.get(reverse('staff:staff_bank_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_bank_detail_view_without_permission(self):
        StaffBank.objects.create(staff=self.staff, bank_code='1234', branch_code='123', account_type='普通', account_number='1234567', account_holder='テスト スタッフ')
        response = self.client.get(reverse('staff:staff_bank_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_bank_create_view_with_permission(self):
        self.user.user_permissions.add(self.add_bank_perm)
        response = self.client.get(reverse('staff:staff_bank_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_bank_create_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_bank_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_bank_edit_view_with_permission(self):
        StaffBank.objects.create(staff=self.staff, bank_code='1234', branch_code='123', account_type='普通', account_number='1234567', account_holder='テスト スタッフ')
        self.user.user_permissions.add(self.change_bank_perm)
        response = self.client.get(reverse('staff:staff_bank_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_bank_edit_view_without_permission(self):
        StaffBank.objects.create(staff=self.staff, bank_code='1234', branch_code='123', account_type='普通', account_number='1234567', account_holder='テスト スタッフ')
        response = self.client.get(reverse('staff:staff_bank_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_bank_delete_view_with_permission(self):
        StaffBank.objects.create(staff=self.staff, bank_code='1234', branch_code='123', account_type='普通', account_number='1234567', account_holder='テスト スタッフ')
        self.user.user_permissions.add(self.delete_bank_perm)
        response = self.client.get(reverse('staff:staff_bank_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_bank_delete_view_without_permission(self):
        StaffBank.objects.create(staff=self.staff, bank_code='1234', branch_code='123', account_type='普通', account_number='1234567', account_holder='テスト スタッフ')
        response = self.client.get(reverse('staff:staff_bank_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    # --- International View Tests ---
    def test_international_detail_view_with_permission(self):
        StaffInternational.objects.create(staff=self.staff, residence_card_number='AB12345678CD', residence_status='Engineer', residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1))
        self.user.user_permissions.add(self.view_international_perm)
        response = self.client.get(reverse('staff:staff_international_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_international_detail_view_without_permission(self):
        StaffInternational.objects.create(staff=self.staff, residence_card_number='AB12345678CD', residence_status='Engineer', residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1))
        response = self.client.get(reverse('staff:staff_international_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_international_create_view_with_permission(self):
        self.user.user_permissions.add(self.add_international_perm)
        response = self.client.get(reverse('staff:staff_international_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_international_create_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_international_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_international_edit_view_with_permission(self):
        StaffInternational.objects.create(staff=self.staff, residence_card_number='AB12345678CD', residence_status='Engineer', residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1))
        self.user.user_permissions.add(self.change_international_perm)
        response = self.client.get(reverse('staff:staff_international_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_international_edit_view_without_permission(self):
        StaffInternational.objects.create(staff=self.staff, residence_card_number='AB12345678CD', residence_status='Engineer', residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1))
        response = self.client.get(reverse('staff:staff_international_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_international_delete_view_with_permission(self):
        StaffInternational.objects.create(staff=self.staff, residence_card_number='AB12345678CD', residence_status='Engineer', residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1))
        self.user.user_permissions.add(self.delete_international_perm)
        response = self.client.get(reverse('staff:staff_international_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_international_delete_view_without_permission(self):
        StaffInternational.objects.create(staff=self.staff, residence_card_number='AB12345678CD', residence_status='Engineer', residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1))
        response = self.client.get(reverse('staff:staff_international_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    # --- Request Detail View Tests ---
    def test_mynumber_request_detail_view_with_permission(self):
        self.user.user_permissions.add(self.change_mynumber_perm)
        response = self.client.get(reverse('staff:staff_mynumber_request_detail', args=[self.staff.pk, self.mynumber_request.pk]))
        self.assertEqual(response.status_code, 200)

    def test_mynumber_request_detail_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_mynumber_request_detail', args=[self.staff.pk, self.mynumber_request.pk]))
        self.assertEqual(response.status_code, 403)

    def test_bank_request_detail_view_with_permission(self):
        self.user.user_permissions.add(self.change_bank_perm)
        response = self.client.get(reverse('staff:staff_bank_request_detail', args=[self.staff.pk, self.bank_request.pk]))
        self.assertEqual(response.status_code, 200)

    def test_bank_request_detail_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_bank_request_detail', args=[self.staff.pk, self.bank_request.pk]))
        self.assertEqual(response.status_code, 403)

    def test_international_request_detail_view_with_permission(self):
        self.user.user_permissions.add(self.change_international_perm)
        response = self.client.get(reverse('staff:staff_international_request_detail', args=[self.staff.pk, self.international_request.pk]))
        self.assertEqual(response.status_code, 200)

    def test_international_request_detail_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_international_request_detail', args=[self.staff.pk, self.international_request.pk]))
        self.assertEqual(response.status_code, 403)

    # --- Disability View Tests ---
    def test_disability_detail_view_with_permission(self):
        StaffDisability.objects.create(staff=self.staff, disability_type='身体障害')
        self.user.user_permissions.add(self.view_disability_perm)
        response = self.client.get(reverse('staff:staff_disability_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_disability_detail_view_without_permission(self):
        StaffDisability.objects.create(staff=self.staff, disability_type='身体障害')
        response = self.client.get(reverse('staff:staff_disability_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_disability_create_view_with_permission(self):
        self.user.user_permissions.add(self.add_disability_perm)
        response = self.client.get(reverse('staff:staff_disability_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_disability_create_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_disability_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_disability_edit_view_with_permission(self):
        StaffDisability.objects.create(staff=self.staff, disability_type='身体障害')
        self.user.user_permissions.add(self.change_disability_perm)
        response = self.client.get(reverse('staff:staff_disability_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_disability_edit_view_without_permission(self):
        StaffDisability.objects.create(staff=self.staff, disability_type='身体障害')
        response = self.client.get(reverse('staff:staff_disability_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_disability_delete_view_with_permission(self):
        StaffDisability.objects.create(staff=self.staff, disability_type='身体障害')
        self.user.user_permissions.add(self.delete_disability_perm)
        response = self.client.get(reverse('staff:staff_disability_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_disability_delete_view_without_permission(self):
        StaffDisability.objects.create(staff=self.staff, disability_type='身体障害')
        response = self.client.get(reverse('staff:staff_disability_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    # --- Contact View Tests ---
    def test_contact_detail_view_with_permission(self):
        StaffContact.objects.create(staff=self.staff, emergency_contact='09012345678')
        self.user.user_permissions.add(self.view_contact_perm)
        response = self.client.get(reverse('staff:staff_contact_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_contact_detail_view_without_permission(self):
        StaffContact.objects.create(staff=self.staff, emergency_contact='09012345678')
        response = self.client.get(reverse('staff:staff_contact_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_contact_create_view_with_permission(self):
        self.user.user_permissions.add(self.add_contact_perm)
        response = self.client.get(reverse('staff:staff_contact_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_contact_create_view_without_permission(self):
        response = self.client.get(reverse('staff:staff_contact_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_contact_edit_view_with_permission(self):
        StaffContact.objects.create(staff=self.staff, emergency_contact='09012345678')
        self.user.user_permissions.add(self.change_contact_perm)
        response = self.client.get(reverse('staff:staff_contact_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_contact_edit_view_without_permission(self):
        StaffContact.objects.create(staff=self.staff, emergency_contact='09012345678')
        response = self.client.get(reverse('staff:staff_contact_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)

    def test_contact_delete_view_with_permission(self):
        StaffContact.objects.create(staff=self.staff, emergency_contact='09012345678')
        self.user.user_permissions.add(self.delete_contact_perm)
        response = self.client.get(reverse('staff:staff_contact_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

    def test_contact_delete_view_without_permission(self):
        StaffContact.objects.create(staff=self.staff, emergency_contact='09012345678')
        response = self.client.get(reverse('staff:staff_contact_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 403)
