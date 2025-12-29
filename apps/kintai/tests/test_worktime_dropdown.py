"""
就業時間プルダウン機能のテスト
"""
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, time
from apps.accounts.models import MyUser
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.master.models import (
    ContractPattern, EmploymentType, WorkTimePattern, 
    WorkTimePatternWork, WorkTimePatternBreak, PhraseTemplate, PhraseTemplateTitle
)
from apps.kintai.models import StaffTimesheet
from apps.common.constants import Constants


class WorkTimeDropdownTest(TestCase):
    """就業時間プルダウン機能のテストケース"""

    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.user)

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_first='太郎',
            name_last='テスト',
            name_kana_first='タロウ',
            name_kana_last='テスト',
            email='staff@example.com',
        )

        # 契約パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain='2'  # スタッフ
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # PhraseTemplateTitle作成（WORKTIME_NAME）
        self.phrase_template_title, _ = PhraseTemplateTitle.objects.get_or_create(
            key='WORKTIME_NAME',
            defaults={'name': '勤務時間名称'}
        )

        # PhraseTemplate作成（勤務時間名称）
        self.time_name_standard = PhraseTemplate.objects.create(
            title=self.phrase_template_title,
            content='通常勤務',
            is_active=True
        )
        self.time_name_early = PhraseTemplate.objects.create(
            title=self.phrase_template_title,
            content='早番',
            is_active=True
        )
        self.time_name_late = PhraseTemplate.objects.create(
            title=self.phrase_template_title,
            content='遅番',
            is_active=True
        )

        # 就業時間パターン作成
        self.worktime_pattern = WorkTimePattern.objects.create(
            name='標準勤務パターン',
            is_active=True,
            display_order=1
        )

        # 勤務時間1: 通常勤務 9:00-18:00 休憩60分
        self.work_time_standard = WorkTimePatternWork.objects.create(
            worktime_pattern=self.worktime_pattern,
            time_name=self.time_name_standard,
            start_time=time(9, 0),
            end_time=time(18, 0),
            start_time_next_day=False,
            end_time_next_day=False,
            display_order=1
        )
        WorkTimePatternBreak.objects.create(
            work_time=self.work_time_standard,
            start_time=time(12, 0),
            end_time=time(13, 0),
            display_order=1
        )

        # 勤務時間2: 早番 7:00-16:00 休憩60分
        self.work_time_early = WorkTimePatternWork.objects.create(
            worktime_pattern=self.worktime_pattern,
            time_name=self.time_name_early,
            start_time=time(7, 0),
            end_time=time(16, 0),
            start_time_next_day=False,
            end_time_next_day=False,
            display_order=2
        )
        WorkTimePatternBreak.objects.create(
            work_time=self.work_time_early,
            start_time=time(12, 0),
            end_time=time(13, 0),
            display_order=1
        )

        # 勤務時間3: 遅番 13:00-22:00 休憩60分
        self.work_time_late = WorkTimePatternWork.objects.create(
            worktime_pattern=self.worktime_pattern,
            time_name=self.time_name_late,
            start_time=time(13, 0),
            end_time=time(22, 0),
            start_time_next_day=False,
            end_time_next_day=False,
            display_order=3
        )
        WorkTimePatternBreak.objects.create(
            work_time=self.work_time_late,
            start_time=time(17, 0),
            end_time=time(18, 0),
            display_order=1
        )

        # スタッフ契約作成
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='テスト契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
            worktime_pattern=self.worktime_pattern,
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )

    def test_timecard_calendar_initial_has_work_times_data(self):
        """初回カレンダー入力画面に就業時間データが含まれていることを確認"""
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.contract.pk,
            'target_month': '2025-11'
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('work_times_data', response.context)
        
        work_times_data = response.context['work_times_data']
        self.assertEqual(len(work_times_data), 3)
        
        # 通常勤務のデータを確認
        standard_work = work_times_data[0]
        self.assertEqual(standard_work['name'], '通常勤務')
        self.assertEqual(standard_work['start_time'], '09:00')
        self.assertEqual(standard_work['end_time'], '18:00')
        self.assertEqual(standard_work['break_minutes'], 60)
        self.assertFalse(standard_work['start_time_next_day'])
        self.assertFalse(standard_work['end_time_next_day'])

    def test_timecard_calendar_initial_template_has_worktime_column(self):
        """初回カレンダー入力画面のテンプレートに就業時間列が含まれていることを確認"""
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.contract.pk,
            'target_month': '2025-11'
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '就業時間')
        self.assertContains(response, 'work-time-select')
        self.assertContains(response, '通常勤務')
        self.assertContains(response, '早番')
        self.assertContains(response, '遅番')

    def test_timecard_calendar_has_work_times_data(self):
        """月次勤怠作成後のカレンダー入力画面に就業時間データが含まれていることを確認"""
        # 月次勤怠を作成
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.contract,
            staff=self.staff,
            target_month=date(2025, 11, 1)
        )
        
        url = reverse('kintai:timecard_calendar', kwargs={
            'timesheet_pk': timesheet.pk
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('work_times_data', response.context)
        
        work_times_data = response.context['work_times_data']
        self.assertEqual(len(work_times_data), 3)

    def test_work_times_data_without_worktime_pattern(self):
        """就業時間パターンが設定されていない契約の場合、空のリストが返されることを確認"""
        # 就業時間パターンなしの契約を作成
        contract_no_pattern = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='パターンなし契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 31),
            worktime_pattern=None,
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )
        
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': contract_no_pattern.pk,
            'target_month': '2025-12'
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('work_times_data', response.context)
        
        work_times_data = response.context['work_times_data']
        self.assertEqual(len(work_times_data), 0)

    def test_work_times_data_order(self):
        """就業時間データが表示順でソートされていることを確認"""
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.contract.pk,
            'target_month': '2025-11'
        })
        response = self.client.get(url)
        
        work_times_data = response.context['work_times_data']
        
        # 表示順を確認
        self.assertEqual(work_times_data[0]['name'], '通常勤務')
        self.assertEqual(work_times_data[1]['name'], '早番')
        self.assertEqual(work_times_data[2]['name'], '遅番')

    def test_work_times_data_with_multiple_breaks(self):
        """複数の休憩時間がある場合、合計が正しく計算されることを確認"""
        # 追加の休憩時間を作成
        WorkTimePatternBreak.objects.create(
            work_time=self.work_time_standard,
            start_time=time(15, 0),
            end_time=time(15, 15),
            display_order=2
        )
        
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.contract.pk,
            'target_month': '2025-11'
        })
        response = self.client.get(url)
        
        work_times_data = response.context['work_times_data']
        standard_work = work_times_data[0]
        
        # 60分 + 15分 = 75分
        self.assertEqual(standard_work['break_minutes'], 75)

    def test_work_times_data_with_next_day_flags(self):
        """翌日フラグが正しく設定されることを確認"""
        # 夜勤パターンを作成
        time_name_night = PhraseTemplate.objects.create(
            title=self.phrase_template_title,
            content='夜勤',
            is_active=True
        )
        work_time_night = WorkTimePatternWork.objects.create(
            worktime_pattern=self.worktime_pattern,
            time_name=time_name_night,
            start_time=time(22, 0),
            end_time=time(7, 0),
            start_time_next_day=False,
            end_time_next_day=True,
            display_order=4
        )
        
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.contract.pk,
            'target_month': '2025-11'
        })
        response = self.client.get(url)
        
        work_times_data = response.context['work_times_data']
        night_work = work_times_data[3]
        
        self.assertEqual(night_work['name'], '夜勤')
        self.assertFalse(night_work['start_time_next_day'])
        self.assertTrue(night_work['end_time_next_day'])
