from django.test import TestCase, Client
from django.urls import reverse
from datetime import date

from django.contrib.auth import get_user_model

from apps.staff.models_staff import Staff
from apps.contract.models import StaffContract
from apps.kintai.models import StaffTimesheet, StaffTimecard
from apps.master.models_contract import ContractPattern


class KintaiViewIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client = Client()
        self.client.login(username='tester', password='pass')

        # Staff
        self.staff = Staff.objects.create(
            name_last='Yamada',
            name_first='Taro',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
        )

    def test_timesheet_create_post_rejects_outside_contract(self):
        cp = ContractPattern.objects.create(name='CP-timesheet', domain='1')
        sc = StaffContract.objects.create(
            staff=self.staff,
            contract_name='CT-timesheet',
            contract_pattern=cp,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 30),
        )

        url = reverse('kintai:timesheet_create')
        data = {
            'staff_contract': sc.pk,
            'target_month': '2025-03',  # outside contract
        }

        resp = self.client.post(url, data)
        # form invalid -> re-render page with form errors
        self.assertEqual(resp.status_code, 200)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        non_field = form.non_field_errors()
        self.assertTrue(any('契約期間外' in str(e) for e in non_field))

    def test_timesheet_create_post_accepts_inside_contract(self):
        cp = ContractPattern.objects.create(name='CP-timesheet2', domain='1')
        sc = StaffContract.objects.create(
            staff=self.staff,
            contract_name='CT-timesheet2',
            contract_pattern=cp,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 30),
        )

        url = reverse('kintai:timesheet_create')
        data = {
            'staff_contract': sc.pk,
            'target_month': '2025-04',  # inside
        }

        resp = self.client.post(url, data)
        # should redirect to detail
        self.assertEqual(resp.status_code, 302)
        # created timesheet exists
        ts = StaffTimesheet.objects.filter(staff_contract=sc, target_month=date(2025, 4, 1)).first()
        self.assertIsNotNone(ts)

    def test_timecard_create_post_rejects_outside_date(self):
        cp = ContractPattern.objects.create(name='CP-timecard', domain='1')
        sc = StaffContract.objects.create(
            staff=self.staff,
            contract_name='CT-timecard',
            contract_pattern=cp,
            start_date=date(2025, 4, 5),
            end_date=date(2025, 4, 25),
        )

        ts = StaffTimesheet.objects.create(staff_contract=sc, staff=self.staff, target_month=date(2025, 4, 1))

        url = reverse('kintai:timecard_create', args=[ts.pk])
        data = {
            'work_date': '2025-04-01',  # outside contract
            'work_type': '30',
            'break_minutes': 0,
            'late_night_break_minutes': 0,
            'paid_leave_days': 0,
        }

        resp = self.client.post(url, data)
        # form invalid -> re-render page
        self.assertEqual(resp.status_code, 200)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        # form should include our contract-period error
        self.assertTrue(any('契約期間外' in str(v) for v in form.errors.values()))

    def test_timecard_create_post_accepts_inside_date(self):
        cp = ContractPattern.objects.create(name='CP-timecard2', domain='1')
        sc = StaffContract.objects.create(
            staff=self.staff,
            contract_name='CT-timecard2',
            contract_pattern=cp,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 30),
        )

        ts = StaffTimesheet.objects.create(staff_contract=sc, staff=self.staff, target_month=date(2025, 4, 1))

        url = reverse('kintai:timecard_create', args=[ts.pk])
        data = {
            'work_date': '2025-04-10',
            'work_type': '30',
            'break_minutes': 0,
            'late_night_break_minutes': 0,
            'paid_leave_days': 0,
        }

        resp = self.client.post(url, data)
        # successful create redirects
        self.assertEqual(resp.status_code, 302)
        tc = StaffTimecard.objects.filter(timesheet=ts, work_date=date(2025, 4, 10)).first()
        self.assertIsNotNone(tc)
