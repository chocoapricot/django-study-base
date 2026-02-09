from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from datetime import date, datetime, timedelta
from apps.kintai.models import StaffTimerecord
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern, TimePunch, OvertimePattern
from apps.common.constants import Constants
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class TimerecordCalendarViewTest(TestCase):
    """勤怠打刻カレンダービューのテスト"""

    def setUp(self):
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)

        self.user = User.objects.create_user(
            username='staffuser_cal',
            email='staff_cal@example.com',
            password='testpass123',
            is_staff=True,
            tenant_id=self.company.tenant_id
        )

        # 権限追加
        permissions = Permission.objects.filter(
            codename__in=['view_stafftimerecord', 'add_stafftimerecord']
        )
        self.user.user_permissions.add(*permissions)

        self.client = Client()
        self.client.login(username='staffuser_cal', password='testpass123')

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='カレンダー',
            name_first='テスト',
            email='staff_cal@example.com',
            tenant_id=self.company.tenant_id
        )

        self.employment_type = EmploymentType.objects.create(name='正社員')
        self.contract_pattern = ContractPattern.objects.create(name='標準', domain=Constants.DOMAIN.STAFF)
        self.time_punch = TimePunch.objects.create(name='テスト打刻', punch_method=Constants.PUNCH_METHOD.PUNCH)
        self.overtime_pattern = OvertimePattern.objects.create(name='テスト時間外')

        self.today = date.today()
        # 1日から28日までの契約を作成（29日以降を「対象外」にするため）
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            time_punch=self.time_punch,
            overtime_pattern=self.overtime_pattern,
            start_date=self.today.replace(day=1),
            end_date=self.today.replace(day=28),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )

        self.calendar_url = reverse('kintai:timerecord_calender')

    def test_calendar_display(self):
        """カレンダー表示のテスト"""
        response = self.client.get(self.calendar_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/timerecord_calender.html')

        # 契約期間内の日付が含まれているか
        self.assertContains(response, self.today.replace(day=1).strftime('%m/%d'))
        self.assertContains(response, self.today.replace(day=28).strftime('%m/%d'))

        # 契約期間外の日付（例: 29日）が含まれていないか
        # ※月によっては29日がない場合もあるので、存在する場合のみチェック
        from calendar import monthrange
        _, last_day = monthrange(self.today.year, self.today.month)
        if last_day >= 29:
            self.assertNotContains(response, self.today.replace(day=29).strftime('%m/%d'))

    def test_calendar_with_record(self):
        """打刻データがある場合の表示テスト"""
        work_date = self.today.replace(day=10)
        # 9:00 - 18:00 の打刻
        start_time = timezone.make_aware(datetime.combine(work_date, datetime.min.time().replace(hour=9)))
        end_time = timezone.make_aware(datetime.combine(work_date, datetime.min.time().replace(hour=18)))

        StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.staff_contract,
            work_date=work_date,
            start_time=start_time,
            end_time=end_time
        )

        response = self.client.get(self.calendar_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '09:00')
        self.assertContains(response, '18:00')
        self.assertContains(response, '編集')

    def test_calendar_filter(self):
        """年月フィルタのテスト"""
        # 翌月の1日
        if self.today.month == 12:
            next_month = date(self.today.year + 1, 1, 1)
        else:
            next_month = date(self.today.year, self.today.month + 1, 1)

        url = f"{self.calendar_url}?target_month={next_month.strftime('%Y-%m')}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # 次の月の契約はないので、カレンダーは空（対象日なし）
        self.assertNotContains(response, next_month.strftime('%m/%d'))

    def test_timerecord_create_prefill(self):
        """新規作成画面の初期値設定テスト"""
        work_date = self.today.replace(day=15)
        url = reverse('kintai:timerecord_create') + f"?work_date={work_date.strftime('%Y-%m-%d')}&staff_contract={self.staff_contract.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # フォームに初期値が設定されているか確認
        form = response.context['form']
        self.assertEqual(str(form.initial['work_date']), work_date.strftime('%Y-%m-%d'))
        self.assertEqual(int(form.initial['staff_contract']), self.staff_contract.pk)
