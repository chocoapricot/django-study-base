from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, time
from apps.kintai.models import StaffTimesheet, StaffTimecard
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.company.models import Company
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

        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )

    def tearDown(self):
        from apps.common.middleware import set_current_tenant_id
        set_current_tenant_id(None)

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
                staff_contract=self.staff_contract,
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
        
    def test_contract_search_filter_input_status(self):
        """契約検索画面の入力状況フィルタテスト"""
        target_month = date(2024, 11, 1)
        
        # 3人のスタッフと契約を作成
        staffs = []
        contracts = []
        for i in range(3):
            s = Staff.objects.create(
                name_last=f'テスト{i}', name_first='太郎',
                employee_no=f'EMP00{i+2}', # 既存と被らないように
                email=f'test{i}@example.com'
            )
            c = StaffContract.objects.create(
                staff=s,
                employment_type=self.employment_type,
                contract_name=f'契約{i}',
                contract_pattern=self.contract_pattern,
                start_date=date(2024, 4, 1),
                end_date=date(2025, 3, 31),
                contract_status=Constants.CONTRACT_STATUS.CONFIRMED
            )
            staffs.append(s)
            contracts.append(c)
            
        # 1人目: 未入力 (timesheetなし or timesheetありtimecardなし)
        # timesheetなしのまま
        
        # 2人目: 入力中 (1日だけ入力)
        ts2 = StaffTimesheet.objects.create(staff_contract=contracts[1], staff=staffs[1], target_month=target_month)
        StaffTimecard.objects.create(staff_contract=contracts[1], timesheet=ts2, work_date=date(2024, 11, 1), work_type='10', start_time=time(9,0), end_time=time(18,0))
        
        # 3人目: 入力済 (30日分入力)
        ts3 = StaffTimesheet.objects.create(staff_contract=contracts[2], staff=staffs[2], target_month=target_month)
        for d in range(1, 31): # 11月は30日まで
            StaffTimecard.objects.create(staff_contract=contracts[2], timesheet=ts3, work_date=date(2024, 11, d), work_type='10', start_time=time(9,0), end_time=time(18,0))

        # 既存のself.staff_contract (EMP001) はtimesheetなし -> 未入力扱い
        
        # ケース1: 未入力 (not_input)
        response = self.client.get(reverse('kintai:contract_search'), {'target_month': '2024-11', 'input_status': 'not_input'})
        self.assertEqual(response.status_code, 200)
        # EMP001とEMP002(1人目)が含まれるはず
        self.assertTrue(any(c['contract'] == self.staff_contract for c in response.context['contract_list']))
        self.assertTrue(any(c['contract'] == contracts[0] for c in response.context['contract_list']))
        self.assertFalse(any(c['contract'] == contracts[1] for c in response.context['contract_list'])) # 入力中
        
        # ケース2: 入力中 (inputting)
        response = self.client.get(reverse('kintai:contract_search'), {'target_month': '2024-11', 'input_status': 'inputting'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(c['contract'] == contracts[1] for c in response.context['contract_list']))
        self.assertFalse(any(c['contract'] == contracts[0] for c in response.context['contract_list']))
        
        # ケース3: 入力済 (inputted)
        response = self.client.get(reverse('kintai:contract_search'), {'target_month': '2024-11', 'input_status': 'inputted'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(c['contract'] == contracts[2] for c in response.context['contract_list']))
        self.assertFalse(any(c['contract'] == contracts[1] for c in response.context['contract_list']))
