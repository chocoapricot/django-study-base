from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, time
from apps.kintai.models import StaffTimesheet, StaffTimecard
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern
from apps.common.constants import Constants

User = get_user_model()

class ContractSearchViewTest(TestCase):
    """契約検索および仮想月次勤怠フローのテスト"""

    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を追加
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.kintai.models import StaffTimesheet, StaffTimecard
        
        timesheet_ct = ContentType.objects.get_for_model(StaffTimesheet)
        timecard_ct = ContentType.objects.get_for_model(StaffTimecard)
        
        add_timesheet_perm = Permission.objects.get(codename='add_stafftimesheet', content_type=timesheet_ct)
        add_timecard_perm = Permission.objects.get(codename='add_stafftimecard', content_type=timecard_ct)
        delete_timesheet_perm = Permission.objects.get(codename='delete_stafftimesheet', content_type=timesheet_ct)
        
        self.user.user_permissions.add(add_timesheet_perm, add_timecard_perm, delete_timesheet_perm)
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            email='yamada@example.com',
            employee_no='EMP001',
            hire_date=date(2024, 4, 1)
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False
        )

        # 契約書パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            domain=Constants.DOMAIN.STAFF
        )

        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31)
        )

    def test_contract_search_view(self):
        """契約検索画面の表示テスト"""
        # 契約期間内の月を指定
        response = self.client.get(reverse('kintai:contract_search'), {'target_month': '2024-11'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '契約検索')
        self.assertContains(response, '山田太郎')
        self.assertContains(response, 'EMP001')  # 社員番号
        self.assertContains(response, '正社員')    # 雇用形態

    def test_contract_search_with_target_month(self):
        """対象月指定での契約検索テスト"""
        target_month = '2024-11'
        response = self.client.get(reverse('kintai:contract_search'), {'target_month': target_month})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['target_date'], date(2024, 11, 1))

    def test_timesheet_preview_view(self):
        """仮想月次勤怠プレビュー画面のテスト"""
        target_month = '2024-11'
        url = reverse('kintai:timesheet_preview', kwargs={
            'contract_pk': self.staff_contract.pk,
            'target_month': target_month
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '未作成')
        # ボタンのテキストを確認（権限がある場合のみ表示）
        if self.user.has_perm('kintai.add_stafftimecard'):
            self.assertContains(response, '日次勤怠追加')
            self.assertContains(response, 'カレンダー入力')
        
        # コンテキストの確認
        self.assertTrue(response.context['is_preview'])
        self.assertEqual(response.context['contract'], self.staff_contract)
        self.assertEqual(response.context['target_date'], date(2024, 11, 1))

    def test_timecard_create_initial_view(self):
        """初回日次勤怠作成（仮想フロー）のテスト"""
        target_month = '2024-11'
        url = reverse('kintai:timecard_create_initial', kwargs={
            'contract_pk': self.staff_contract.pk,
            'target_month': target_month
        })
        
        # GETリクエスト
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '日次勤怠作成')

        # POSTリクエスト（保存と月次勤怠作成の確認）
        post_data = {
            'work_date': '2024-11-01',
            'work_type': '10',  # 出勤
            'start_time': '09:00',
            'end_time': '18:00',
            'break_minutes': '60',
            'late_night_break_minutes': '0',
            'paid_leave_days': '0',
        }
        response = self.client.post(url, post_data)
        
        # 作成された月次勤怠を確認
        timesheet = StaffTimesheet.objects.filter(
            staff_contract=self.staff_contract,
            target_month=date(2024, 11, 1)
        ).first()
        self.assertIsNotNone(timesheet)
        
        # リダイレクト先が月次勤怠詳細であることを確認
        self.assertRedirects(response, reverse('kintai:timesheet_detail', args=[timesheet.pk]))

    def test_timecard_calendar_initial_view(self):
        """初回カレンダー入力（仮想フロー）のテスト"""
        target_month = '2024-11'
        url = reverse('kintai:timecard_calendar_initial', kwargs={
            'contract_pk': self.staff_contract.pk,
            'target_month': target_month
        })

        # GETリクエスト
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'カレンダー入力')

        # POSTリクエスト
        post_data = {
            'work_type_1': '10',
            'start_time_1': '09:00',
            'end_time_1': '18:00',
            'break_minutes_1': '60',
            'paid_leave_days_1': '0',
        }
        response = self.client.post(url, post_data)

        # 作成された月次勤怠を確認
        timesheet = StaffTimesheet.objects.filter(
            staff_contract=self.staff_contract,
            target_month=date(2024, 11, 1)
        ).first()
        self.assertIsNotNone(timesheet)

        # リダイレクト先が月次勤怠詳細であることを確認
        self.assertRedirects(response, reverse('kintai:timesheet_detail', args=[timesheet.pk]))

    def test_timesheet_delete_redirect(self):
        """月次勤怠削除後のリダイレクト先テスト"""
        # 月次勤怠を作成
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )
        
        url = reverse('kintai:timesheet_delete', args=[timesheet.pk])
        response = self.client.post(url)
        
        # リダイレクト先が契約検索（対象月パラメータ付き）であることを確認
    def test_contract_search_input_days(self):
        """契約検索画面の入力日数表示テスト"""
        # 月次勤怠を作成
        target_month = date(2024, 11, 1)
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=target_month
        )
        
        # 日次勤怠を3日分作成
        for i in range(1, 4):
            StaffTimecard.objects.create(
                timesheet=timesheet,
                work_date=date(2024, 11, i),
                work_type='10',
                start_time=time(9, 0),
                end_time=time(18, 0)
            )
            
        # 検索画面にアクセス
        response = self.client.get(reverse('kintai:contract_search'), {'target_month': '2024-11'})
        self.assertEqual(response.status_code, 200)
        
        # コンテキストの確認
        contract_list = response.context['contract_list']
        self.assertEqual(len(contract_list), 1)
        self.assertEqual(contract_list[0]['input_days'], 3)
        
        # HTMLの確認
        self.assertContains(response, '3日')
