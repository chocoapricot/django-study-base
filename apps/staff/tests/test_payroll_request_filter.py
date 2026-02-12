from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from apps.connect.models import ConnectStaff, PayrollRequest
from apps.profile.models import StaffProfilePayroll, StaffProfile

User = get_user_model()

class PayrollRequestFilterTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        if not self.company.tenant_id:
            self.company.tenant_id = 1
            self.company.save()
        # スレッドローカルにテナントIDをセット
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(username='testuser', password='testpassword', tenant_id=self.company.tenant_id)
        self.client.login(username='testuser', password='testpassword')

        # StaffモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Staff)
        # 必要な権限をユーザーに付与
        self.view_staff_permission = Permission.objects.get(codename='view_staff', content_type=content_type)
        self.user.user_permissions.add(self.view_staff_permission)

    def test_staff_list_filter_by_payroll_request(self):
        """
        Test that the staff list can be filtered by `has_request=true` when a payroll request is pending.
        """
        # Create a staff with a pending payroll request
        staff_with_payroll_request = Staff.objects.create(
            email='payroll_request@example.com',
            name_last='Payroll',
            name_first='Request',
            tenant_id=self.company.tenant_id
        )

        staff_user_with_request = User.objects.create_user(
            username='staffwithpayrollrequest',
            email='payroll_request@example.com',
            password='testpassword',
            tenant_id=self.company.tenant_id
        )

        # Create staff profile (needed for some logic)
        staff_profile = StaffProfile.objects.create(
            user=staff_user_with_request,
            name_last='Payroll',
            name_first='Request'
        )

        staff_payroll_profile = StaffProfilePayroll.objects.create(
            user=staff_user_with_request,
            basic_pension_number='1234567890'
        )

        connect_staff = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=staff_with_payroll_request.email,
            status='approved'
        )

        PayrollRequest.objects.create(
            connect_staff=connect_staff,
            staff_payroll_profile=staff_payroll_profile,
            status='pending'
        )

        # Create a staff without a pending request
        staff_without_request = Staff.objects.create(
            email='without_request@example.com',
            name_last='Without',
            name_first='Request',
            tenant_id=self.company.tenant_id
        )

        # Test with filter
        response = self.client.get(reverse('staff:staff_list') + '?has_request=true')
        self.assertEqual(response.status_code, 200)

        staff_list_on_page = response.context['staffs'].object_list
        self.assertEqual(len(staff_list_on_page), 1)
        self.assertEqual(staff_list_on_page[0], staff_with_payroll_request)

        # Verify that has_pending_payroll_request is set
        self.assertTrue(staff_list_on_page[0].has_pending_payroll_request)

    def test_staff_list_registration_status_payroll_request_icon(self):
        """
        Test that the down arrow icon is displayed in the payroll column of the registration status view
        when a payroll request is pending.
        """
        # Create a staff with a pending payroll request
        staff_with_payroll_request = Staff.objects.create(
            email='payroll_request_icon@example.com',
            employee_no='ICON001',
            name_last='Payroll',
            name_first='Icon',
            tenant_id=self.company.tenant_id
        )

        staff_user = User.objects.create_user(
            username='payrolliconuser',
            email='payroll_request_icon@example.com',
            password='testpassword',
            tenant_id=self.company.tenant_id
        )

        staff_payroll_profile = StaffProfilePayroll.objects.create(
            user=staff_user,
            basic_pension_number='1234567890'
        )

        connect_staff = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=staff_with_payroll_request.email,
            status='approved'
        )

        PayrollRequest.objects.create(
            connect_staff=connect_staff,
            staff_payroll_profile=staff_payroll_profile,
            status='pending'
        )

        # Test registration status view
        response = self.client.get(reverse('staff:staff_list') + '?registration_status=true')
        self.assertEqual(response.status_code, 200)

        # Check for the down arrow icon in the response content
        # It should have title="変更あり" and style="color:#17a2b8;"
        self.assertContains(response, 'bi-arrow-down-circle')
        self.assertContains(response, 'title="変更あり"')
