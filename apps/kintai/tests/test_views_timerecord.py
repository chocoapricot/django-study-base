from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, datetime, time
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

    def test_cancel_action_order(self):
        """取り消し機能で正しい順序で取り消されるかテスト"""
        from datetime import timedelta
        
        # 出勤
        self.client.post(self.action_url, {'action': 'start'})
        record = StaffTimerecord.objects.get(staff=self.staff)
        
        # 複数の休憩を時系列順で追加
        now = timezone.now()
        
        # 1回目の休憩（古い・完了済み）
        StaffTimerecordBreak.objects.create(
            timerecord=record,
            break_start=now - timedelta(hours=2),
            break_end=now - timedelta(hours=1, minutes=30)
        )
        
        # 2回目の休憩（新しい）- 現在進行中（2分前に開始、取り消し可能）
        latest_break = StaffTimerecordBreak.objects.create(
            timerecord=record,
            break_start=now - timedelta(minutes=2)
        )
        
        # 取り消し実行
        response = self.client.post(self.action_url, {'action': 'cancel'})
        self.assertRedirects(response, self.punch_url)
        
        # 最新の休憩（2回目）が削除されているか確認
        self.assertFalse(StaffTimerecordBreak.objects.filter(id=latest_break.id).exists())
        
        # 古い休憩（1回目）は残っているか確認
        self.assertEqual(record.breaks.count(), 1)
        remaining_break = record.breaks.first()
        self.assertIsNotNone(remaining_break.break_end)  # 完了した休憩が残っている

    def test_cancel_break_end_order(self):
        """休憩終了の取り消しで正しい順序で取り消されるかテスト"""
        from datetime import timedelta
        
        # 出勤
        self.client.post(self.action_url, {'action': 'start'})
        record = StaffTimerecord.objects.get(staff=self.staff)
        
        now = timezone.now()
        
        # 1回目の休憩（古い・完了済み）
        StaffTimerecordBreak.objects.create(
            timerecord=record,
            break_start=now - timedelta(hours=3),
            break_end=now - timedelta(hours=2, minutes=30)
        )
        
        # 2回目の休憩（新しい・完了済み）
        latest_break = StaffTimerecordBreak.objects.create(
            timerecord=record,
            break_start=now - timedelta(minutes=30),
            break_end=now - timedelta(minutes=1)  # 1分前に終了（取り消し可能）
        )
        
        # 取り消し実行
        response = self.client.post(self.action_url, {'action': 'cancel'})
        self.assertRedirects(response, self.punch_url)
        
        # 最新の休憩の終了時刻が取り消されているか確認
        latest_break.refresh_from_db()
        self.assertIsNone(latest_break.break_end)
        
        # 古い休憩は影響を受けていないか確認
        old_break = record.breaks.exclude(id=latest_break.id).first()
        self.assertIsNotNone(old_break.break_end)

    def test_multiple_contracts_selection(self):
        """複数契約がある場合の契約選択テスト"""
        # 追加のスタッフ契約を作成（確認済み）
        contract2 = StaffContract.objects.create(
            staff=self.staff,
            contract_name="テスト契約2",
            start_date=timezone.localtime().date(),
            contract_pattern=self.contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2件の有効で確認済みの契約があります')
        
        # 契約を指定して出勤
        response = self.client.post(self.action_url, {
            'action': 'start',
            'contract_id': contract2.id
        })
        self.assertRedirects(response, self.punch_url)
        
        # 指定した契約で打刻が作成されているか確認
        record = StaffTimerecord.objects.get(staff=self.staff)
        self.assertEqual(record.staff_contract, contract2)

    def test_no_contract_punch_disabled(self):
        """契約がない場合の打刻無効化テスト"""
        # 契約を削除
        StaffContract.objects.filter(staff=self.staff).delete()
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '有効で確認済みのスタッフ契約がありません')
        # 打刻ボタンが非表示になることを確認
        self.assertNotContains(response, 'name="action" value="start"')
        self.assertNotContains(response, 'name="action" value="end"')
        # 代替メッセージが表示されることを確認
        self.assertContains(response, '打刻ボタンは表示されません')
        
        # 出勤を試行
        response = self.client.post(self.action_url, {'action': 'start'})
        self.assertRedirects(response, self.punch_url)
        
        # 打刻が作成されていないことを確認
        self.assertEqual(StaffTimerecord.objects.count(), 0)

    def test_unconfirmed_contract_punch_disabled(self):
        """未確認契約の場合の打刻無効化テスト"""
        # 既存の契約を未確認状態に変更
        self.staff_contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        self.staff_contract.save()
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '有効で確認済みのスタッフ契約がありません')
        # 打刻ボタンが非表示になることを確認
        self.assertNotContains(response, 'name="action" value="start"')
        self.assertNotContains(response, 'name="action" value="end"')
        # 代替メッセージが表示されることを確認
        self.assertContains(response, '打刻ボタンは表示されません')
        
        # 出勤を試行
        response = self.client.post(self.action_url, {'action': 'start'})
        self.assertRedirects(response, self.punch_url)
        
        # 打刻が作成されていないことを確認
        self.assertEqual(StaffTimerecord.objects.count(), 0)

    def test_mixed_contract_status_selection(self):
        """確認済みと未確認の契約が混在する場合のテスト"""
        # 未確認の契約を追加
        unconfirmed_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name="未確認契約",
            start_date=timezone.localtime().date(),
            contract_pattern=self.contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.ISSUED  # 未確認
        )
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        self.assertEqual(response.status_code, 200)
        
        # 確認済み契約のみが表示されることを確認（1件のみ）
        self.assertContains(response, '契約情報:')
        self.assertNotContains(response, '2件の有効で確認済みの契約があります')
        
        # 未確認契約での出勤を試行（直接POSTで送信）
        response = self.client.post(self.action_url, {
            'action': 'start',
            'contract_id': unconfirmed_contract.id
        })
        self.assertRedirects(response, self.punch_url)
        
        # 打刻が作成されていないことを確認
        self.assertEqual(StaffTimerecord.objects.count(), 0)