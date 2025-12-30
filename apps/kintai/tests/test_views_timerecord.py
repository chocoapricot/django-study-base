from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from apps.kintai.models import StaffTimerecord, StaffTimerecordBreak
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern
from apps.common.constants import Constants

User = get_user_model()

class TimerecordPunchViewTest(TestCase):
    """勤怠打刻ビューとアクションのテスト"""

    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='staffuser', password='testpass123')

        # スタッフ作成（ユーザーのメールアドレスと一致させる）
        self.staff = Staff.objects.create(
            name_last='打刻',
            name_first='テスト',
            email='staff@example.com',
            employee_no='STF001',
            hire_date=date(2024, 1, 1)
        )

        # 雇用形態と契約パターン
        self.employment_type = EmploymentType.objects.create(name='正社員')
        self.contract_pattern = ContractPattern.objects.create(name='標準', domain=Constants.DOMAIN.STAFF)

        # 有効なスタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )

        self.punch_url = reverse('kintai:timerecord_punch')
        self.action_url = reverse('kintai:timerecord_action')

    def test_punch_page_not_started(self):
        """未出勤状態の打刻画面表示テスト"""
        response = self.client.get(self.punch_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '未出勤')
        self.assertContains(response, '出勤')
        # 出勤ボタンが有効、他が無効であることを確認
        self.assertNotContains(response, 'name="action" value="start" class="btn punch-btn btn-start" \n                        disabled')

    def test_action_start(self):
        """出勤アクションのテスト"""
        response = self.client.post(self.action_url, {'action': 'start', 'latitude': '35.0', 'longitude': '135.0'})
        self.assertRedirects(response, self.punch_url)
        
        # データの作成確認
        record = StaffTimerecord.objects.filter(staff=self.staff, work_date=timezone.localtime().date()).first()
        self.assertIsNotNone(record)
        self.assertIsNotNone(record.start_time)
        self.assertEqual(record.start_latitude, 35.0)
        
        # 画面状態の確認
        response = self.client.get(self.punch_url)
        self.assertContains(response, '勤務中')

    def test_action_break_cycle(self):
        """休憩開始・終了アクションのテスト"""
        # まず出勤
        self.client.post(self.action_url, {'action': 'start'})
        
        # 休憩開始
        response = self.client.post(self.action_url, {'action': 'break_start'})
        self.assertRedirects(response, self.punch_url)
        record = StaffTimerecord.objects.get(staff=self.staff)
        self.assertEqual(record.breaks.count(), 1)
        self.assertIsNone(record.breaks.first().break_end)
        
        # 画面状態で休憩中を確認
        response = self.client.get(self.punch_url)
        self.assertContains(response, '休憩中')
        
        # 休憩終了
        response = self.client.post(self.action_url, {'action': 'break_end'})
        self.assertRedirects(response, self.punch_url)
        self.assertIsNotNone(record.breaks.first().break_end)

    def test_action_end(self):
        """退勤アクションのテスト"""
        # 出勤済み状態
        self.client.post(self.action_url, {'action': 'start'})
        
        # 退勤
        response = self.client.post(self.action_url, {'action': 'end'})
        self.assertRedirects(response, self.punch_url)
        
        record = StaffTimerecord.objects.get(staff=self.staff)
        self.assertIsNotNone(record.end_time)
        
        # 画面状態で退勤済みを確認
        response = self.client.get(self.punch_url)
        self.assertContains(response, '退勤済み')

    def test_invalid_actions(self):
        """不正な状態での打刻制限テスト"""
        # 出勤前に退勤
        response = self.client.post(self.action_url, {'action': 'end'})
        self.assertEqual(StaffTimerecord.objects.count(), 0)
        
        # 出勤
        self.client.post(self.action_url, {'action': 'start'})
        
        # 休憩開始後に再度休憩開始
        self.client.post(self.action_url, {'action': 'break_start'})
        self.client.post(self.action_url, {'action': 'break_start'})
        record = StaffTimerecord.objects.get(staff=self.staff)
        self.assertEqual(record.breaks.count(), 1)
        
        # 休憩中に退勤（エラーになるべき）
        response = self.client.post(self.action_url, {'action': 'end'})
        record.refresh_from_db()
        self.assertIsNone(record.end_time)

    def test_overnight_shift(self):
        """日またぎ勤務のテスト（23時開始、翌日1時終了など）"""
        # 前日の日付でレコードを手動作成（23:00開始）
        from datetime import timedelta
        yesterday = timezone.localtime(timezone.now()).date() - timedelta(days=1)
        start_time = timezone.make_aware(datetime.combine(yesterday, time(23, 0)))
        
        # 有効な契約を取得
        contract = StaffContract.objects.filter(staff=self.staff).first()
        
        record = StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=contract,
            work_date=yesterday,
            start_time=start_time
        )

        # 翌日（今日）の01:00に退勤ボタンを押す想定
        response = self.client.post(self.action_url, {'action': 'end'})
        self.assertRedirects(response, self.punch_url)

        # レコードが更新されているか確認
        record.refresh_from_db()
        self.assertIsNotNone(record.end_time)
        self.assertEqual(record.work_date, yesterday)  # 勤務日は開始時のまま

        # 画面状態で再度出勤可能か確認（今日はまだ完了していないので）
        response = self.client.get(self.punch_url)
        self.assertContains(response, '未出勤')

    def test_double_start_prevention(self):
        """重複出勤の防止テスト（日をまたいでいても進行中なら出勤不可）"""
        # 進行中の打刻を作成
        from datetime import timedelta
        yesterday = timezone.localtime(timezone.now()).date() - timedelta(days=1)
        StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.staff_contract,
            work_date=yesterday,
            start_time=timezone.now() - timedelta(hours=5)
        )

        # 今日出勤ボタンを押しても、進行中があるためエラーになるべき
        response = self.client.post(self.action_url, {'action': 'start'})
        # メッセージを確認
        self.assertContains(self.client.get(self.punch_url), '既に勤務中（出勤打刻済み）です。')

    def test_no_staff_profile(self):
        """スタッフ情報がないユーザーのアクセス制限テスト"""
        User.objects.create_user(username='otheruser', email='other@example.com', password='pass')
        self.client.login(username='otheruser', password='pass')
        
        response = self.client.get(self.punch_url)
        self.assertRedirects(response, '/')

# 必要なインポートを追加
from datetime import datetime, time
