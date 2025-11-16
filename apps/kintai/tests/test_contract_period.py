from django.test import TestCase, Client
from django.urls import reverse
from datetime import date

from apps.staff.models_staff import Staff
from apps.contract.models import StaffContract
from apps.kintai.models import StaffTimesheet
from apps.kintai.forms import StaffTimecardForm
from apps.master.models_contract import ContractPattern


class ContractPeriodTests(TestCase):
    def setUp(self):
        # Create a user for view access
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')

        # Create a staff
        self.staff = Staff.objects.create(
            name_last='Yamada',
            name_first='Taro',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
        )

    def test_timesheet_month_outside_contract_raises(self):
        # Contract covers Mar-Jun 2025
        cp = ContractPattern.objects.create(name='CP1', domain='1')
        sc = StaffContract.objects.create(
            staff=self.staff,
            contract_name='CT1',
            contract_pattern=cp,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 6, 30),
        )

        # Create timesheet for Feb 2025 which is outside the contract
        ts = StaffTimesheet(staff_contract=sc, staff=self.staff, year=2025, month=2)

        # call clean() directly to exercise our contract-period validation
        with self.assertRaises(Exception) as cm:
            ts.clean()

        self.assertIn('契約期間外', str(cm.exception))

    def test_timecard_form_rejects_work_date_outside_contract(self):
        # Contract covers Apr 2025
        cp = ContractPattern.objects.create(name='CP2', domain='1')
        sc = StaffContract.objects.create(
            staff=self.staff,
            contract_name='CT2',
            contract_pattern=cp,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 30),
        )

        # Create timesheet for April
        ts = StaffTimesheet.objects.create(staff_contract=sc, year=2025, month=4)

        # Prepare form data for a work_date in March (outside contract)
        data = {
            'work_date': '2025-03-15',
            'work_type': '30',  # 欠勤 - does not require times
            'break_minutes': 0,
            'paid_leave_days': 0,
        }

        form = StaffTimecardForm(data=data, timesheet=ts)
        self.assertFalse(form.is_valid())
        self.assertIn('契約期間外', str(form.errors))

    def test_timecard_calendar_excludes_outside_dates(self):
        # Contract from Apr 5 to Apr 25
        cp = ContractPattern.objects.create(name='CP3', domain='1')
        sc = StaffContract.objects.create(
            staff=self.staff,
            contract_name='CT3',
            contract_pattern=cp,
            start_date=date(2025, 4, 5),
            end_date=date(2025, 4, 25),
        )

        ts = StaffTimesheet.objects.create(staff_contract=sc, year=2025, month=4)

        client = Client()
        logged = client.login(username='tester', password='pass')
        self.assertTrue(logged)

        url = reverse('kintai:timecard_calendar', args=[ts.pk])
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)

        calendar_data = resp.context['calendar_data']
        # All returned days should be within start_date and end_date
        for item in calendar_data:
            d = item['date']
            self.assertGreaterEqual(d, sc.start_date)
            self.assertLessEqual(d, sc.end_date)
