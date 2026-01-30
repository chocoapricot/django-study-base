from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date
from apps.kintai.models import StaffTimesheet, StaffTimecard
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.company.models import Company
from apps.master.models import EmploymentType, ContractPattern, OvertimePattern
from apps.common.constants import Constants

User = get_user_model()


from django.contrib.auth.models import Permission


class TimesheetViewTest(TestCase):
    """月次勤怠ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # 権限を付与
        permissions = Permission.objects.filter(
            content_type__app_label='kintai',
            content_type__model__in=['stafftimesheet', 'stafftimecard']
        )
        self.user.user_permissions.set(permissions)

        # テナント設定
        self.company = Company.objects.create(name='テスト会社')
        self.user.tenant_id = self.company.tenant_id
        self.user.save()

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # セッションにテナントIDを設定
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # スレッドローカルにテナントIDをセット（オブジェクト作成用）
        from apps.common.middleware import set_current_tenant_id
        set_current_tenant_id(self.company.tenant_id)

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

        # 時間外算出パターン作成
        self.overtime_pattern = OvertimePattern.objects.create(
            name='テスト用時間外パターン',
            calculate_midnight_premium=True,
        )

        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約',
            contract_pattern=self.contract_pattern,
            overtime_pattern=self.overtime_pattern,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )

        # 月次勤怠作成
        self.timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )

    def tearDown(self):
        from apps.common.middleware import set_current_tenant_id
        set_current_tenant_id(None)

    def test_timesheet_list_view(self):
        """月次勤怠一覧ビューのテスト"""
        response = self.client.get(reverse('kintai:timesheet_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '月次勤怠一覧')
        self.assertContains(response, '山田')

    def test_timesheet_detail_view(self):
        """月次勤怠詳細ビューのテスト"""
        response = self.client.get(reverse('kintai:timesheet_detail', args=[self.timesheet.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '月次勤怠詳細')
        self.assertContains(response, '2024年11月')

    def test_timesheet_create_view(self):
        """月次勤怠作成ビューのテスト"""
        response = self.client.get(reverse('kintai:timesheet_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '月次勤怠作成')
        # テンプレートの修正が正しく反映されているか確認
        self.assertContains(response, 'name="target_month"')
        self.assertContains(response, 'type="month"')

    def test_timesheet_delete_view_get(self):
        """月次勤怠削除確認画面のテスト"""
        response = self.client.get(reverse('kintai:timesheet_delete', args=[self.timesheet.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '削除確認')

    def test_timesheet_delete_view_post(self):
        """月次勤怠削除実行のテスト"""
        response = self.client.post(reverse('kintai:timesheet_delete', args=[self.timesheet.pk]))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertFalse(StaffTimesheet.objects.filter(pk=self.timesheet.pk).exists())

    def test_login_required(self):
        """ログイン必須のテスト"""
        self.client.logout()
        response = self.client.get(reverse('kintai:timesheet_list'))
        self.assertEqual(response.status_code, 302)  # ログインページにリダイレクト


class TimecardViewTest(TestCase):
    """日次勤怠ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # 権限を付与
        permissions = Permission.objects.filter(
            content_type__app_label='kintai',
            content_type__model__in=['stafftimesheet', 'stafftimecard']
        )
        self.user.user_permissions.set(permissions)

        # テナント設定
        self.company = Company.objects.create(name='テスト会社')
        self.user.tenant_id = self.company.tenant_id
        self.user.save()

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # セッションにテナントIDを設定
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # スレッドローカルにテナントIDをセット（オブジェクト作成用）
        from apps.common.middleware import set_current_tenant_id
        set_current_tenant_id(self.company.tenant_id)

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

        # 時間外算出パターン作成
        self.overtime_pattern = OvertimePattern.objects.create(
            name='テスト用時間外パターン',
            calculate_midnight_premium=True,
        )

        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約',
            contract_pattern=self.contract_pattern,
            overtime_pattern=self.overtime_pattern,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )

        # 月次勤怠作成
        self.timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 11, 1)
        )

        # 日次勤怠作成
        from datetime import time
        self.timecard = StaffTimecard.objects.create(
            timesheet=self.timesheet,
            staff_contract=self.staff_contract,
            work_date=date(2024, 11, 1),
            work_type='10',
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60
        )

    def tearDown(self):
        from apps.common.middleware import set_current_tenant_id
        set_current_tenant_id(None)

    def test_timecard_delete_view_get(self):
        """日次勤怠削除確認画面のテスト"""
        response = self.client.get(reverse('kintai:timecard_delete', args=[self.timecard.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '削除確認')

    def test_timecard_delete_view_post(self):
        """日次勤怠削除実行のテスト"""
        response = self.client.post(reverse('kintai:timecard_delete', args=[self.timecard.pk]))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertFalse(StaffTimecard.objects.filter(pk=self.timecard.pk).exists())

    def test_timecard_calendar_view_get(self):
        """日次勤怠カレンダー入力画面のテスト"""
        response = self.client.get(reverse('kintai:timecard_calendar', args=[self.timesheet.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'カレンダー入力')

    def test_timecard_calendar_view_post(self):
        """日次勤怠カレンダー一括保存のテスト"""
        post_data = {
            'work_type_1': '10',
            'start_time_1': '09:00',
            'end_time_1': '18:00',
            'break_minutes_1': '60',
            'paid_leave_days_1': '0',
        }
        response = self.client.post(reverse('kintai:timecard_calendar', args=[self.timesheet.pk]), post_data)
        self.assertEqual(response.status_code, 302)  # リダイレクト
        # 日次勤怠が作成されたことを確認
        self.assertTrue(StaffTimecard.objects.filter(timesheet=self.timesheet, work_date=date(2024, 11, 1)).exists())
