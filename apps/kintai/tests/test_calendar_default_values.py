from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import MyUser
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.master.models import WorkTimePattern, WorkTimePatternWork, WorkTimePatternBreak, PhraseTemplate, PhraseTemplateTitle, EmploymentType, ContractPattern, OvertimePattern
from apps.kintai.models import StaffTimesheet
from datetime import date, time, datetime

class TestCalendarDefaultValues(TestCase):
    def setUp(self):
        print("DEBUG: Starting setUp")
        try:
            # ユーザー作成
            self.user = MyUser.objects.create_user(username='testuser', email='test@example.com', password='password')
            self.client = Client()
            self.client.force_login(self.user)

            # スタッフ作成
            self.staff = Staff.objects.create(
                name_first='太郎',
                name_last='テスト',
                email='staff@example.com',
                phone='090-0000-0000'
            )

            # 就業時間パターン作成
            self.work_pattern = WorkTimePattern.objects.create(name='通常勤務', display_order=1)
            
            # 時間名称作成 (PhraseTemplate)
            self.time_name_title = PhraseTemplateTitle.objects.create(
                key='WORKTIME_NAME',
                name='時間名称',
                is_active=True
            )
            self.time_name = PhraseTemplate.objects.create(
                title=self.time_name_title,
                content='通常',
                is_active=True
            )

            # 勤務時間作成 (10:00 - 19:00)
            self.work_time = WorkTimePatternWork.objects.create(
                worktime_pattern=self.work_pattern,
                time_name=self.time_name,
                start_time=time(10, 0),
                end_time=time(19, 0),
                display_order=1
            )

            # 休憩時間作成 (12:00 - 13:00)
            WorkTimePatternBreak.objects.create(
                work_time=self.work_time,
                start_time=time(12, 0),
                end_time=time(13, 0),
                display_order=1
            )
            
            # マスタデータ作成
            self.employment_type = EmploymentType.objects.create(name='正社員')
            self.contract_pattern = ContractPattern.objects.create(name='標準契約', domain='staff')
            self.overtime_pattern = OvertimePattern.objects.create(name='標準')

            # スタッフ契約作成
            self.contract = StaffContract.objects.create(
                staff=self.staff,
                contract_name='テスト契約',
                start_date=date(2023, 1, 1),
                worktime_pattern=self.work_pattern,
                employment_type=self.employment_type,
                contract_pattern=self.contract_pattern,
                overtime_pattern=self.overtime_pattern
            )
            print("DEBUG: setUp completed successfully")
        except Exception as e:
            print(f"DEBUG: Error in setUp: {e}")
            raise

    def test_timecard_calendar_initial_context(self):
        """初回作成時のコンテキストにデフォルト値が含まれているか確認"""
        print("DEBUG: Starting test_timecard_calendar_initial_context")
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.contract.pk,
            'target_month': '2023-04'
        })
        print(f"DEBUG: URL is {url}")
        response = self.client.get(url)
        print(f"DEBUG: Response status code: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['default_start_time'], '10:00')
        self.assertEqual(response.context['default_end_time'], '19:00')
        self.assertEqual(response.context['default_break_minutes'], '60')

    def test_timecard_calendar_context(self):
        """通常カレンダー入力時のコンテキストにデフォルト値が含まれているか確認"""
        # 月次勤怠作成
        timesheet = StaffTimesheet.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            target_month=date(2023, 4, 1)
        )
        
        url = reverse('kintai:timecard_calendar', kwargs={
            'timesheet_pk': timesheet.pk
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['default_start_time'], '10:00')
        self.assertEqual(response.context['default_end_time'], '19:00')
        self.assertEqual(response.context['default_break_minutes'], '60')

    def test_no_worktime_pattern(self):
        """就業時間パターンがない場合のデフォルト値確認"""
        self.contract.worktime_pattern = None
        self.contract.save()
        
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.contract.pk,
            'target_month': '2023-04'
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['default_start_time'], '09:00')
        self.assertEqual(response.context['default_end_time'], '18:00')
        self.assertEqual(response.context['default_break_minutes'], '60')
