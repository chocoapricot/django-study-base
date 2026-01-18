from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth import get_user_model
from datetime import date, timedelta, time
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.kintai.models import StaffTimecard, StaffTimesheet
from apps.master.models import EmploymentType, ContractPattern
from apps.common.constants import Constants

User = get_user_model()


class StaffSearchViewTest(TestCase):
    """スタッフ検索ビューのテストケース"""

    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザーを作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # 権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='kintai',
            content_type__model__in=['stafftimesheet', 'stafftimecard']
        )
        self.user.user_permissions.set(permissions)
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # スタッフを作成
        self.staff1 = Staff.objects.create(
            employee_no='S001',
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ'
        )
        self.staff2 = Staff.objects.create(
            employee_no='S002',
            name_last='佐藤',
            name_first='花子',
            name_kana_last='サトウ',
            name_kana_first='ハナコ'
        )

        # 雇用形態を作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # 契約書パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            domain=Constants.DOMAIN.STAFF
        )

        # 今月の日付を取得
        today = date.today()
        self.target_month = today.replace(day=1)
        month_end = (self.target_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # スタッフ1の契約を作成（今月有効）
        self.contract1 = StaffContract.objects.create(
            staff=self.staff1,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=self.target_month,
            end_date=month_end
        )

        # スタッフ2の契約を作成（今月有効）
        self.contract2 = StaffContract.objects.create(
            staff=self.staff2,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=self.target_month,
            end_date=month_end
        )

    def test_staff_search_view_loads(self):
        """スタッフ検索画面が正常に表示されること"""
        url = reverse('kintai:staff_search')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/staff_search.html')

    def test_staff_search_displays_staff_with_contracts(self):
        """契約があるスタッフが表示されること"""
        url = reverse('kintai:staff_search')
        response = self.client.get(url, {'target_month': self.target_month.strftime('%Y-%m')})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('staff_list', response.context)
        
        staff_list = response.context['staff_list']
        self.assertEqual(len(staff_list), 2)
        
        # スタッフ1が含まれていること
        staff_ids = [item['staff'].pk for item in staff_list]
        self.assertIn(self.staff1.pk, staff_ids)
        self.assertIn(self.staff2.pk, staff_ids)

    def test_staff_search_contract_count(self):
        """スタッフの契約数が正しくカウントされること"""
        # スタッフ1に追加の契約を作成
        StaffContract.objects.create(
            staff=self.staff1,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=self.target_month,
            end_date=self.target_month + timedelta(days=15)
        )

        url = reverse('kintai:staff_search')
        response = self.client.get(url, {'target_month': self.target_month.strftime('%Y-%m')})
        
        staff_list = response.context['staff_list']
        staff1_data = next(item for item in staff_list if item['staff'].pk == self.staff1.pk)
        
        self.assertEqual(staff1_data['contract_count'], 2)

    def test_staff_search_input_days_count(self):
        """勤怠入力日数が正しくカウントされること"""
        # スタッフ1の日次勤怠を作成
        work_date1 = self.target_month + timedelta(days=1)
        work_date2 = self.target_month + timedelta(days=2)
        
        StaffTimecard.objects.create(
            staff_contract=self.contract1,
            work_date=work_date1,
            work_type='10'
        )
        StaffTimecard.objects.create(
            staff_contract=self.contract1,
            work_date=work_date2,
            work_type='10'
        )

        url = reverse('kintai:staff_search')
        response = self.client.get(url, {'target_month': self.target_month.strftime('%Y-%m')})
        
        staff_list = response.context['staff_list']
        staff1_data = next(item for item in staff_list if item['staff'].pk == self.staff1.pk)
        
        self.assertEqual(staff1_data['input_days'], 2)

    def test_staff_search_no_contracts_in_month(self):
        """指定月に契約がないスタッフは表示されないこと"""
        # 来月の日付
        next_month = (self.target_month + timedelta(days=32)).replace(day=1)
        
        url = reverse('kintai:staff_search')
        response = self.client.get(url, {'target_month': next_month.strftime('%Y-%m')})
        
        staff_list = response.context['staff_list']
        self.assertEqual(len(staff_list), 0)


class StaffTimecardCalendarViewTest(TestCase):
    """スタッフ別カレンダー入力ビューのテストケース"""

    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザーを作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # 権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='kintai',
            content_type__model__in=['stafftimesheet', 'stafftimecard']
        )
        self.user.user_permissions.set(permissions)
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # スタッフを作成
        self.staff = Staff.objects.create(
            employee_no='S001',
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ'
        )

        # 雇用形態を作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # 契約書パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            domain=Constants.DOMAIN.STAFF
        )

        # 今月の日付を取得
        today = date.today()
        self.target_month = today.replace(day=1)
        month_end = (self.target_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # スタッフの契約を作成
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=self.target_month,
            end_date=month_end
        )

    def test_staff_timecard_calendar_view_loads(self):
        """スタッフ別カレンダー入力画面が正常に表示されること"""
        url = reverse('kintai:staff_timecard_calendar', 
                     kwargs={'staff_pk': self.staff.pk, 'target_month': self.target_month.strftime('%Y-%m')})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/staff_timecard_calendar.html')

    def test_staff_timecard_calendar_displays_calendar_data(self):
        """カレンダーデータが正しく表示されること"""
        url = reverse('kintai:staff_timecard_calendar',
                     kwargs={'staff_pk': self.staff.pk, 'target_month': self.target_month.strftime('%Y-%m')})
        response = self.client.get(url)
        
        self.assertIn('calendar_data', response.context)
        self.assertIn('staff', response.context)
        
        calendar_data = response.context['calendar_data']
        self.assertGreater(len(calendar_data), 0)  # カレンダーデータが存在すること

    def test_staff_timecard_calendar_valid_contracts_per_day(self):
        """各日に有効な契約のみが表示されること"""
        # 月の途中で終了する契約を追加
        mid_month = self.target_month + timedelta(days=15)
        contract2 = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=self.target_month,
            end_date=mid_month
        )

        url = reverse('kintai:staff_timecard_calendar',
                     kwargs={'staff_pk': self.staff.pk, 'target_month': self.target_month.strftime('%Y-%m')})
        response = self.client.get(url)
        
        calendar_data = response.context['calendar_data']
        
        # 月の最初の日は2つの契約が有効
        first_day_data = calendar_data[0]
        self.assertEqual(len(first_day_data['valid_contracts']), 2)
        
        # 月の最後の日は1つの契約のみ有効
        last_day_data = calendar_data[-1]
        self.assertEqual(len(last_day_data['valid_contracts']), 1)

    def test_staff_timecard_calendar_create_timecard(self):
        """日次勤怠を作成できること"""
        work_date = self.target_month + timedelta(days=1)
        
        url = reverse('kintai:staff_timecard_calendar',
                     kwargs={'staff_pk': self.staff.pk, 'target_month': self.target_month.strftime('%Y-%m')})
        
        post_data = {
            f'contract_{work_date.day}': self.contract.pk,
            f'work_type_{work_date.day}': '10',
            f'start_time_{work_date.day}': '09:00',
            f'end_time_{work_date.day}': '18:00',
            f'break_minutes_{work_date.day}': '60',
            f'paid_leave_days_{work_date.day}': '0',
        }
        
        response = self.client.post(url, post_data)
        
        # リダイレクトされること
        self.assertEqual(response.status_code, 302)
        
        # 日次勤怠が作成されていること
        timecard = StaffTimecard.objects.filter(
            staff_contract=self.contract,
            work_date=work_date
        ).first()
        
        self.assertIsNotNone(timecard)
        self.assertEqual(timecard.work_type, '10')

    def test_staff_timecard_calendar_creates_timesheet_automatically(self):
        """日次勤怠作成時に月次勤怠が自動作成されること"""
        work_date = self.target_month + timedelta(days=1)
        
        url = reverse('kintai:staff_timecard_calendar',
                     kwargs={'staff_pk': self.staff.pk, 'target_month': self.target_month.strftime('%Y-%m')})
        
        post_data = {
            f'contract_{work_date.day}': self.contract.pk,
            f'work_type_{work_date.day}': '10',
            f'start_time_{work_date.day}': '09:00',
            f'end_time_{work_date.day}': '18:00',
            f'break_minutes_{work_date.day}': '60',
            f'paid_leave_days_{work_date.day}': '0',
        }
        
        response = self.client.post(url, post_data)
        
        # 月次勤怠が自動作成されていること
        timesheet = StaffTimesheet.objects.filter(
            staff_contract=self.contract,
            target_month=self.target_month
        ).first()
        
        self.assertIsNotNone(timesheet)
        self.assertEqual(timesheet.staff, self.staff)

    def test_staff_timecard_calendar_displays_existing_timecard(self):
        """既存の日次勤怠が表示されること"""
        work_date = self.target_month + timedelta(days=1)
        
        # 事前に日次勤怠を作成
        StaffTimecard.objects.create(
            staff_contract=self.contract,
            work_date=work_date,
            work_type='10',
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60
        )

        url = reverse('kintai:staff_timecard_calendar',
                     kwargs={'staff_pk': self.staff.pk, 'target_month': self.target_month.strftime('%Y-%m')})
        response = self.client.get(url)
        
        calendar_data = response.context['calendar_data']
        day_data = next(d for d in calendar_data if d['day'] == work_date.day)
        
        self.assertIsNotNone(day_data['timecard'])
        self.assertEqual(day_data['timecard'].work_type, '10')

    def test_staff_timecard_calendar_validation_error(self):
        """バリデーションエラーが発生すること"""
        work_date = self.target_month + timedelta(days=1)
        
        url = reverse('kintai:staff_timecard_calendar',
                     kwargs={'staff_pk': self.staff.pk, 'target_month': self.target_month.strftime('%Y-%m')})
        
        # 出勤なのに時間が空の場合
        post_data = {
            f'contract_{work_date.day}': self.contract.pk,
            f'work_type_{work_date.day}': '10',
            f'start_time_{work_date.day}': '',
            f'end_time_{work_date.day}': '',
            f'break_minutes_{work_date.day}': '60',
            f'paid_leave_days_{work_date.day}': '0',
        }
        
        response = self.client.post(url, post_data, follow=True)
        
        # エラーメッセージが表示されていること
        messages = list(response.context['messages'])
        self.assertTrue(any('出勤の場合は出勤時刻と退勤時刻を入力してください' in str(m) for m in messages))
        
        # データが保存されていないこと
        timecard = StaffTimecard.objects.filter(
            staff_contract=self.contract,
            work_date=work_date
        ).first()
        self.assertIsNone(timecard)
