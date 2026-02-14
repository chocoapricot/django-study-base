from django.test import TestCase
from django.utils import timezone
from datetime import date, time
from apps.kintai.models import ClientTimesheet, ClientTimecard
from apps.contract.models import ClientContract
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import ContractPattern, OvertimePattern
from apps.common.constants import Constants

class ClientKintaiModelTest(TestCase):
    def setUp(self):
        self.client = Client.objects.create(name="Test Client")
        self.staff = Staff.objects.create(name_last="Staff", name_first="Test")

        # Need a contract pattern for ClientContract
        self.pattern = ContractPattern.objects.create(
            name="Test Pattern",
            domain=Constants.DOMAIN.CLIENT
        )

        # Need an overtime pattern
        self.overtime_pattern = OvertimePattern.objects.create(
            name="Normal",
            calculation_type='premium',
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
            daily_overtime_minutes=0
        )

        self.client_contract = ClientContract.objects.create(
            client=self.client,
            contract_name="Test Client Contract",
            contract_pattern=self.pattern,
            start_date=date(2025, 1, 1),
            overtime_pattern=self.overtime_pattern
        )

    def test_client_timesheet_and_timecard_creation(self):
        """ClientTimesheetとClientTimecardが正しく作成され、集計されるかテスト"""
        target_month = date(2025, 1, 1)

        # Create ClientTimecard (which should auto-create ClientTimesheet)
        timecard = ClientTimecard.objects.create(
            client_contract=self.client_contract,
            staff=self.staff,
            work_date=date(2025, 1, 5),
            work_type='10',
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60
        )

        # Check if timesheet was created
        self.assertIsNotNone(timecard.timesheet)
        self.assertEqual(timecard.timesheet.target_month, target_month)
        self.assertEqual(timecard.timesheet.client_contract, self.client_contract)
        self.assertEqual(timecard.timesheet.staff, self.staff)

        # Check calculation result in timecard
        # 9:00 to 18:00 is 9 hours. Minus 60 min break = 8 hours (480 min)
        self.assertEqual(timecard.work_minutes, 480)
        # 8 hours standard, so 0 overtime
        self.assertEqual(timecard.overtime_minutes, 0)

        # Check aggregation in timesheet
        timesheet = timecard.timesheet
        self.assertEqual(timesheet.total_work_days, 1)
        self.assertEqual(timesheet.total_work_minutes, 480)

    def test_client_timecard_overtime(self):
        """残業時間の計算テスト"""
        timecard = ClientTimecard.objects.create(
            client_contract=self.client_contract,
            staff=self.staff,
            work_date=date(2025, 1, 6),
            work_type='10',
            start_time=time(9, 0),
            end_time=time(20, 0), # 11 hours
            break_minutes=60      # 10 hours work
        )

        # 10 hours work - 8 hours standard = 2 hours (120 min) overtime
        self.assertEqual(timecard.work_minutes, 600)
        self.assertEqual(timecard.overtime_minutes, 120)

        # Check timesheet totals
        timesheet = timecard.timesheet
        self.assertEqual(timesheet.total_work_minutes, 600)
        self.assertEqual(timesheet.total_overtime_minutes, 120)
