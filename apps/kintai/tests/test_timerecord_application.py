from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, datetime, timedelta
import calendar as py_calendar
from apps.kintai.models import StaffTimerecord, StaffTimerecordApproval, StaffTimecard
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.master.models import EmploymentType, ContractPattern, TimePunch
from apps.common.constants import Constants

User = get_user_model()

class TimerecordApplicationTest(TestCase):
    """勤怠申請機能のテスト"""

    def setUp(self):
        # ユーザー作成
        self.user = User.objects.create_user(
            username='teststaff',
            email='staff@example.com',
            password='password',
            is_staff=True,
            is_superuser=True
        )

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            email='staff@example.com',
            employee_no='EMP001'
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(name='正社員')

        # 契約書パターン作成
        self.contract_pattern = ContractPattern.objects.create(name='標準契約', domain=Constants.DOMAIN.STAFF)

        # 打刻設定
        self.time_punch = TimePunch.objects.create(
            name='標準打刻',
            punch_method=Constants.PUNCH_METHOD.PUNCH
        )

        # スタッフ契約作成 (2024年を通じた契約)
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_pattern=self.contract_pattern,
            contract_name='2024年度契約',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
            time_punch=self.time_punch,
            confirmed_at=timezone.now()
        )

        self.client = Client()
        self.client.login(username='teststaff', password='password')

    def test_timerecord_apply(self):
        """勤怠申請のテスト"""
        target_month = '2024-01'
        url = reverse('kintai:timerecord_apply')
        # target_month_str = '2024-01' -> last_day = 2024-01-31
        response = self.client.post(url, {'target_month': target_month})

        self.assertEqual(response.status_code, 302)

        # Approvalレコードが作成されているか確認
        # テナントフィルタを無効化して取得
        approval = StaffTimerecordApproval.objects.unfiltered().filter(
            staff=self.staff,
            closing_date=date(2024, 1, 31)
        ).first()
        self.assertIsNotNone(approval, "Approval record was not created")
        self.assertEqual(approval.status, '20')

    def test_timerecord_withdraw(self):
        """申請取り戻しのテスト"""
        # まず申請する
        StaffTimerecordApproval.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            closing_date=date(2024, 1, 31),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status='20'
        )

        target_month = '2024-01'
        url = reverse('kintai:timerecord_withdraw')
        response = self.client.post(url, {'target_month': target_month})

        self.assertEqual(response.status_code, 302)

        # ステータスが作成中(10)に戻っているか確認
        approval = StaffTimerecordApproval.objects.unfiltered().get(staff=self.staff, closing_date=date(2024, 1, 31))
        self.assertEqual(approval.status, '10')

    def test_locking_mechanism(self):
        """ロック機能のテスト"""
        # 今日をロック期間にする
        today = timezone.localtime().date()
        _, last_day_num = py_calendar.monthrange(today.year, today.month)
        last_day = today.replace(day=last_day_num)

        # スタッフ契約を今日を含むように調整（もしsetUpの期間外なら）
        if self.contract.start_date > today or (self.contract.end_date and self.contract.end_date < today):
            self.contract.start_date = today.replace(day=1)
            self.contract.end_date = None
            self.contract.save()

        StaffTimerecordApproval.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            closing_date=last_day,
            period_start=today.replace(day=1),
            period_end=last_day,
            status='20'
        )

        # 1. 打刻アクションがブロックされるか確認
        url = reverse('kintai:timerecord_action')
        # 必要なパラメータ（緯度経度など）を追加
        response = self.client.post(url, {'action': 'start', 'latitude': 35.0, 'longitude': 135.0})
        self.assertEqual(response.status_code, 302)

        # メッセージを確認
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('申請済みまたは承認済みの勤怠は打刻できません' in str(m) for m in messages))

    def test_timerecord_update_locked(self):
        """申請済みの打刻編集がブロックされるか確認"""
        work_date = date(2024, 1, 15)
        tr = StaffTimerecord.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            work_date=work_date,
            start_time=timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        )

        # 申請済みの状態にする
        StaffTimerecordApproval.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            closing_date=date(2024, 1, 31),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status='20'
        )

        # GETアクセスで編集画面に行こうとする
        url = reverse('kintai:timerecord_update', args=[tr.pk])
        response = self.client.get(url)
        # detail画面へリダイレクトされるはず
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('kintai:timerecord_detail', args=[tr.pk]), response.url)

        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('申請済みまたは承認済みの勤怠は編集できません' in str(m) for m in messages))
