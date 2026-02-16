from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.kintai.models import StaffTimerecordApproval, StaffTimerecord, StaffTimecard, ClientTimecard, ClientTimesheet
from apps.staff.models import Staff
from apps.contract.models import StaffContract, ClientContract, ContractAssignment
from apps.client.models import Client
from apps.master.models import TimePunch, ContractPattern
from apps.common.constants import Constants
from apps.common.middleware import set_current_tenant_id
from apps.kintai.utils import sync_timerecords_to_timecards
from datetime import date, datetime, time
from django.utils import timezone

User = get_user_model()

class TimerecordSyncClientTest(TestCase):
    def setUp(self):
        self.tenant_id = 1
        set_current_tenant_id(self.tenant_id)

        self.user = User.objects.create_superuser(
            username='admin',
            password='password',
            email='admin@example.com',
            tenant_id=self.tenant_id
        )

        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            employee_no='S001',
            email='taro@example.com',
            tenant_id=self.tenant_id
        )

        self.client_obj = Client.objects.create(
            name='テストクライアント',
            tenant_id=self.tenant_id
        )

        self.time_punch = TimePunch.objects.create(
            name='テスト打刻',
            punch_method=Constants.PUNCH_METHOD.PUNCH,
            tenant_id=self.tenant_id
        )

        self.staff_contract_pattern = ContractPattern.objects.create(
            name='スタッフテストパターン',
            domain=Constants.DOMAIN.STAFF,
            tenant_id=self.tenant_id
        )

        self.client_contract_pattern = ContractPattern.objects.create(
            name='クライアントテストパターン',
            domain=Constants.DOMAIN.CLIENT,
            tenant_id=self.tenant_id
        )

        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='スタッフテスト契約',
            start_date=date(2025, 1, 1),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
            time_punch=self.time_punch,
            contract_pattern=self.staff_contract_pattern,
            tenant_id=self.tenant_id
        )

        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='クライアントテスト契約',
            start_date=date(2025, 1, 1),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
            contract_pattern=self.client_contract_pattern,
            tenant_id=self.tenant_id
        )

        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=self.staff_contract,
            assignment_start_date=date(2025, 1, 1),
            assignment_end_date=date(2025, 1, 31),
            tenant_id=self.tenant_id
        )

        self.approval = StaffTimerecordApproval.objects.create(
            staff=self.staff,
            staff_contract=self.staff_contract,
            closing_date=date(2025, 1, 31),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            status=Constants.KINTAI_STATUS.SUBMITTED,
            tenant_id=self.tenant_id
        )

        # Create a timerecord within the assignment period
        self.tr1 = StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.staff_contract,
            work_date=date(2025, 1, 1),
            start_time=timezone.make_aware(datetime(2025, 1, 1, 9, 0, 0)),
            end_time=timezone.make_aware(datetime(2025, 1, 1, 18, 0, 0)),
            memo='テストメモ1'
        )

        # Create another timerecord outside the assignment period (different date)
        # But for this test, let's just use one that IS within the period first.
        self.tr2 = StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.staff_contract,
            work_date=date(2025, 1, 2),
            start_time=timezone.make_aware(datetime(2025, 1, 2, 9, 0, 0)),
            end_time=timezone.make_aware(datetime(2025, 1, 2, 18, 0, 0)),
            memo='テストメモ2'
        )

    def test_sync_to_client_timecard(self):
        # Initial check
        self.assertEqual(ClientTimecard.objects.count(), 0)

        # Sync
        sync_timerecords_to_timecards(self.approval)

        # Check StaffTimecard (existing behavior)
        self.assertEqual(StaffTimecard.objects.count(), 2)

        # Check ClientTimecard (new behavior)
        self.assertEqual(ClientTimecard.objects.count(), 2)

        ctc1 = ClientTimecard.objects.get(work_date=date(2025, 1, 1))
        self.assertEqual(ctc1.client_contract, self.client_contract)
        self.assertEqual(ctc1.staff, self.staff)
        self.assertEqual(ctc1.start_time, time(9, 0))
        self.assertEqual(ctc1.end_time, time(18, 0))
        self.assertEqual(ctc1.memo, 'テストメモ1')

        # Check ClientTimesheet
        ts = ClientTimesheet.objects.get(client_contract=self.client_contract, staff=self.staff, target_month=date(2025, 1, 1))
        self.assertGreater(ts.total_work_minutes, 0)
        # 9:00 - 18:00 = 9 hours = 540 minutes per day. 2 days = 1080 minutes.
        self.assertEqual(ts.total_work_minutes, 1080)

    def test_sync_only_within_assignment_period(self):
        # Update assignment to only cover the first day
        self.assignment.assignment_end_date = date(2025, 1, 1)
        self.assignment.save()

        # Sync
        sync_timerecords_to_timecards(self.approval)

        # StaffTimecard should have 2 records
        self.assertEqual(StaffTimecard.objects.count(), 2)

        # ClientTimecard should only have 1 record (tr1 is in period, tr2 is not)
        self.assertEqual(ClientTimecard.objects.count(), 1)
        self.assertTrue(ClientTimecard.objects.filter(work_date=date(2025, 1, 1)).exists())
        self.assertFalse(ClientTimecard.objects.filter(work_date=date(2025, 1, 2)).exists())
