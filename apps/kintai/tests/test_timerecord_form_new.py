from django.test import TestCase
from django.utils import timezone
from datetime import date, time, datetime, timedelta
from apps.kintai.forms import StaffTimerecordForm
from apps.kintai.models import StaffTimerecord
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern
from apps.common.constants import Constants
from zoneinfo import ZoneInfo

class StaffTimerecordFormTest(TestCase):
    def setUp(self):
        self.staff = Staff.objects.create(
            name_last='山田', name_first='太郎', email='yamada@example.com'
        )
        self.employment_type = EmploymentType.objects.create(name='正社員')
        self.contract_pattern = ContractPattern.objects.create(name='標準', domain=Constants.DOMAIN.STAFF)
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 1, 1),
            confirmed_at=timezone.now()
        )
        self.work_date = date(2024, 11, 1)

    def test_form_with_time_and_next_day(self):
        """時間と翌日フラグが正しくDateTimeFieldに変換されるか"""
        form_data = {
            'staff_contract': self.staff_contract.pk,
            'work_date': self.work_date,
            'rounded_start_time': '09:00',
            'rounded_start_time_next_day': False,
            'rounded_end_time': '02:00',
            'rounded_end_time_next_day': True,
        }
        form = StaffTimerecordForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

        instance = form.save(commit=False)

        # Asia/Tokyoで期待値を計算
        tz = ZoneInfo('Asia/Tokyo')
        expected_start = datetime.combine(self.work_date, time(9, 0)).replace(tzinfo=tz)
        expected_end = datetime.combine(self.work_date + timedelta(days=1), time(2, 0)).replace(tzinfo=tz)

        self.assertEqual(instance.rounded_start_time, expected_start)
        self.assertEqual(instance.rounded_end_time, expected_end)

    def test_form_initial_values(self):
        """既存のDateTimeFieldから初期値が正しく設定されるか"""
        tz = ZoneInfo('Asia/Tokyo')
        start_dt = datetime.combine(self.work_date, time(22, 0)).replace(tzinfo=tz)
        end_dt = datetime.combine(self.work_date + timedelta(days=1), time(5, 0)).replace(tzinfo=tz)

        timerecord = StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.staff_contract,
            work_date=self.work_date,
            rounded_start_time=start_dt,
            rounded_end_time=end_dt
        )

        form = StaffTimerecordForm(instance=timerecord)
        self.assertEqual(form.initial['rounded_start_time'], time(22, 0))
        self.assertEqual(form.initial.get('rounded_start_time_next_day'), False)
        self.assertEqual(form.initial['rounded_end_time'], time(5, 0))
        self.assertEqual(form.initial.get('rounded_end_time_next_day'), True)
