
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date
from apps.kintai.models import ClientTimesheet, ClientTimecard
from apps.contract.models import ClientContract, StaffContract, ContractAssignment
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from apps.master.models import ContractPattern, OvertimePattern
from apps.common.constants import Constants
from django.contrib.auth import get_user_model

User = get_user_model()

class ClientKintaiViewTest(TestCase):
    def setUp(self):
        self.tenant_id = 1
        self.user = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')
        # Some models might need tenant_id
        self.client_model = ClientModel.objects.create(name="Test Client", tenant_id=self.tenant_id)
        self.staff = Staff.objects.create(name_last="Staff", name_first="Test", employee_no="E001", tenant_id=self.tenant_id)

        self.pattern_client = ContractPattern.objects.create(name="Pattern Client", domain=Constants.DOMAIN.CLIENT, tenant_id=self.tenant_id)
        self.pattern_staff = ContractPattern.objects.create(name="Pattern Staff", domain=Constants.DOMAIN.STAFF, tenant_id=self.tenant_id)
        self.overtime = OvertimePattern.objects.create(name="Overtime", calculation_type='premium', tenant_id=self.tenant_id)

        # Use a date that includes the current month
        today = timezone.localdate()
        start_date = today.replace(day=1)

        self.client_contract = ClientContract.objects.create(
            client=self.client_model,
            contract_name="Client Contract",
            contract_pattern=self.pattern_client,
            overtime_pattern=self.overtime,
            start_date=date(2020, 1, 1),
            tenant_id=self.tenant_id
        )

        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name="Staff Contract",
            contract_pattern=self.pattern_staff,
            overtime_pattern=self.overtime,
            start_date=date(2020, 1, 1),
            tenant_id=self.tenant_id
        )

        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            tenant_id=self.tenant_id
        )

        self.client.login(username='admin', password='password')

    def test_client_contract_search_view(self):
        response = self.client.get(reverse('kintai:client_contract_search'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Client")
        self.assertContains(response, "StaffTest")

    def test_client_contract_search_with_icons(self):
        from apps.staff.models_staff import StaffContactSchedule
        from datetime import date

        # Add a contact schedule
        StaffContactSchedule.objects.create(
            staff=self.staff,
            contact_date=date.today(),
            content="Test Contact",
            tenant_id=self.tenant_id
        )

        response = self.client.get(reverse('kintai:client_contract_search'))
        self.assertEqual(response.status_code, 200)

        # Check if the icon for contact schedule is present
        self.assertContains(response, 'bi-alarm')
        self.assertContains(response, '連絡予定あり')

    def test_client_timesheet_create_and_calendar(self):
        # Create timesheet
        today = timezone.localdate()
        target_month = today.strftime('%Y-%m')
        response = self.client.post(reverse('kintai:client_timesheet_create'), {
            'client_contract': self.client_contract.pk,
            'staff': self.staff.pk,
            'target_month': target_month
        })
        self.assertEqual(response.status_code, 302)

        timesheet = ClientTimesheet.objects.get(target_month=today.replace(day=1))

        # Access calendar
        response = self.client.get(reverse('kintai:client_timecard_calendar', args=[timesheet.pk]))
        self.assertEqual(response.status_code, 200)

        # Save a timecard via calendar
        response = self.client.post(reverse('kintai:client_timecard_calendar', args=[timesheet.pk]), {
            'work_type_1': '10',
            'start_time_1': '09:00',
            'end_time_1': '18:00',
            'break_minutes_1': '60'
        })
        self.assertEqual(response.status_code, 302)

        self.assertEqual(timesheet.timecards.count(), 1)
        tc = timesheet.timecards.first()
        self.assertEqual(tc.work_date.day, 1)
        self.assertEqual(tc.work_minutes, 480)
