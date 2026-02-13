from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q
from apps.kintai.models import StaffTimerecordApproval, StaffTimerecord, StaffTimecard, StaffTimesheet
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.master.models import TimePunch, ContractPattern
from apps.common.constants import Constants
from apps.common.middleware import set_current_tenant_id
from datetime import date, datetime, time
from django.utils import timezone

User = get_user_model()

class TimerecordSyncTest(TestCase):
    def setUp(self):
        self.tenant_id = 1
        set_current_tenant_id(self.tenant_id)

        self.user = User.objects.create_superuser(
            username='admin',
            password='password',
            email='admin@example.com',
            tenant_id=self.tenant_id
        )
        self.client.login(username='admin', password='password')

        # Add permissions
        permissions = Permission.objects.filter(
            Q(codename='view_stafftimerecordapproval') |
            Q(codename='change_stafftimerecordapproval') |
            Q(codename='view_stafftimecard') |
            Q(codename='change_stafftimecard') |
            Q(codename='view_stafftimesheet')
        )
        self.user.user_permissions.add(*permissions)

        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            employee_no='S001',
            email='taro@example.com',
            tenant_id=self.tenant_id
        )

        self.time_punch = TimePunch.objects.create(
            name='テスト打刻',
            punch_method=Constants.PUNCH_METHOD.PUNCH,
            tenant_id=self.tenant_id
        )

        self.contract_pattern = ContractPattern.objects.create(
            name='テストパターン',
            domain=Constants.DOMAIN.STAFF,
            tenant_id=self.tenant_id
        )

        self.contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            start_date=date(2025, 1, 1),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
            time_punch=self.time_punch,
            contract_pattern=self.contract_pattern,
            tenant_id=self.tenant_id
        )

        self.approval = StaffTimerecordApproval.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            closing_date=date(2025, 1, 31),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            status='20', # 提出済み
            tenant_id=self.tenant_id
        )

        # Create some timerecords
        self.tr1 = StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            work_date=date(2025, 1, 1),
            start_time=timezone.make_aware(datetime(2025, 1, 1, 9, 0, 0)),
            end_time=timezone.make_aware(datetime(2025, 1, 1, 18, 0, 0))
        )

        # Timerecord with next day end time
        self.tr2 = StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            work_date=date(2025, 1, 2),
            start_time=timezone.make_aware(datetime(2025, 1, 2, 22, 0, 0)),
            end_time=timezone.make_aware(datetime(2025, 1, 3, 5, 0, 0))
        )

        # Set tenant_id in session
        session = self.client.session
        session['tenant_id'] = self.tenant_id
        session.save()

    def test_sync_on_approval(self):
        # Approve the timerecord approval
        response = self.client.post(reverse('kintai:timerecord_approval_approve', args=[self.approval.pk]))
        self.assertEqual(response.status_code, 302)

        # Check if timecards are created
        self.assertEqual(StaffTimecard.objects.count(), 2)

        tc1 = StaffTimecard.objects.get(work_date=date(2025, 1, 1))
        self.assertEqual(tc1.work_type, '10')
        self.assertEqual(tc1.start_time, time(9, 0))
        self.assertEqual(tc1.end_time, time(18, 0))
        self.assertFalse(tc1.end_time_next_day)

        tc2 = StaffTimecard.objects.get(work_date=date(2025, 1, 2))
        self.assertEqual(tc2.start_time, time(22, 0))
        self.assertEqual(tc2.end_time, time(5, 0))
        self.assertTrue(tc2.end_time_next_day)

        # Check if timesheet totals are calculated
        timesheet = StaffTimesheet.objects.get(staff_contract=self.contract, target_month=date(2025, 1, 1))
        self.assertGreater(timesheet.total_work_minutes, 0)

    def test_timecard_editable_after_timerecord_approval(self):
        # Approve first
        self.client.post(reverse('kintai:timerecord_approval_approve', args=[self.approval.pk]))

        # Try to edit the created timecard
        tc1 = StaffTimecard.objects.get(work_date=date(2025, 1, 1))
        timesheet = tc1.timesheet

        # We need to make sure the timesheet is editable (status '10' or '40')
        self.assertIn(timesheet.status, ['10', '40'])

        response = self.client.post(reverse('kintai:timecard_edit', args=[tc1.pk]), {
            'work_date': '2025-01-01',
            'work_type': '10',
            'start_time': '10:00',
            'end_time': '19:00',
            'break_minutes': '60',
            'late_night_break_minutes': '0',
            'paid_leave_days': '0',
        })

        # Should NOT be blocked now
        if response.status_code != 302:
            print(f"Form errors: {response.context.get('form').errors if response.context else 'No context'}")
        self.assertEqual(response.status_code, 302)
        tc1.refresh_from_db()
        self.assertEqual(tc1.start_time, time(10, 0))
