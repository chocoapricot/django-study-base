from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.kintai.models import StaffTimerecord, StaffTimerecordBreak
from apps.master.models import ContractPattern
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from datetime import date, datetime, timedelta

User = get_user_model()

class StaffTimerecordModelTests(TestCase):
    def setUp(self):
        # テナントを作成
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)

        # 契約パターンを作成
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain='1'  # スタッフ用
        )

        # ユーザーとスタッフ、契約を作成
        self.user = User.objects.create_user(username='staff_user', email='staff@example.com', password='password', tenant_id=self.company.tenant_id)
        self.staff = Staff.objects.create(
            employee_no='1001',
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com'  # メールアドレスで紐付け
        )
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            start_date=date(2025, 4, 1),
            contract_name='テスト契約',  # 必須フィールドを追加
            contract_pattern=self.contract_pattern,
            confirmed_at=timezone.now()
        )

    def test_timerecord_creation(self):
        """勤怠打刻が正しく作成され、契約からスタッフが自動設定されるか"""
        record = StaffTimerecord(
            staff_contract=self.contract,
            work_date=date(2025, 4, 1),
            start_time=timezone.make_aware(datetime(2025, 4, 1, 9, 0)),
            end_time=timezone.make_aware(datetime(2025, 4, 1, 18, 0))
        )
        record.save()
        
        self.assertEqual(record.staff, self.staff)
        self.assertEqual(record.total_work_minutes, 9 * 60)

    def test_timerecord_with_break(self):
        """休憩時間を含む勤怠打刻の計算が正しいか"""
        record = StaffTimerecord.objects.create(
            staff_contract=self.contract,
            work_date=date(2025, 4, 1),
            start_time=timezone.make_aware(datetime(2025, 4, 1, 9, 0)),
            end_time=timezone.make_aware(datetime(2025, 4, 1, 18, 0))
        )
        
        # 休憩時間を追加 (12:00-13:00, 60分)
        StaffTimerecordBreak.objects.create(
            timerecord=record,
            break_start=timezone.make_aware(datetime(2025, 4, 1, 12, 0)),
            break_end=timezone.make_aware(datetime(2025, 4, 1, 13, 0))
        )
        
        # 労働時間: 9時間(540分) - 休憩1時間(60分) = 8時間(480分)
        self.assertEqual(record.total_work_minutes, 480)

    def test_validation_error(self):
        """終了時刻が開始時刻より前の場合エラーになるか"""
        record = StaffTimerecord(
            staff_contract=self.contract,
            work_date=date(2025, 4, 1),
            start_time=timezone.make_aware(datetime(2025, 4, 1, 18, 0)),
            end_time=timezone.make_aware(datetime(2025, 4, 1, 9, 0))  # 逆転
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            record.full_clean()


from django.contrib.auth.models import Permission
from django.db.models import Q


class StaffTimerecordViewTests(TestCase):
    def setUp(self):
        # テナントを作成
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)

        # 契約パターンを作成
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain='1'  # スタッフ用
        )

        self.user = User.objects.create_user(username='staff_user', email='staff@example.com', password='password', tenant_id=self.company.tenant_id)

        # Add permissions
        permissions = Permission.objects.filter(
            Q(codename='view_stafftimerecord') |
            Q(codename='add_stafftimerecord')
        )
        self.user.user_permissions.set(permissions)

        self.client.login(username='staff_user', password='password')
        self.staff = Staff.objects.create(
            employee_no='1001',
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com'  # メールアドレスで紐付け
        )
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            start_date=date(2025, 4, 1),
            contract_name='テスト契約',  # 必須フィールドを追加
            contract_pattern=self.contract_pattern,
            confirmed_at=timezone.now()
        )

    def test_timerecord_list_view(self):
        """一覧画面が表示されるか"""
        response = self.client.get(reverse('kintai:timerecord_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/timerecord_list.html')

    def test_timerecord_create_view(self):
        """登録画面が表示され、正しく登録できるか"""
        response = self.client.get(reverse('kintai:timerecord_create'))
        self.assertEqual(response.status_code, 200)
        
        # フォーム送信
        data = {
            'staff_contract': self.contract.id,
            'work_date': '2025-04-02',
            'rounded_start_time': '2025-04-02T09:00',
            'rounded_end_time': '2025-04-02T18:00',
            'start_latitude': '35.6895',
            'start_longitude': '139.6917',
            'end_latitude': '35.6895',
            'end_longitude': '139.6917',
        }
        response = self.client.post(reverse('kintai:timerecord_create'), data)
        self.assertEqual(response.status_code, 302)  # 詳細画面へリダイレクト
        
        # データが作成されているか確認
        self.assertTrue(StaffTimerecord.objects.filter(work_date='2025-04-02').exists())
        record = StaffTimerecord.objects.get(work_date='2025-04-02')
        self.assertEqual(record.staff, self.staff)  # スタッフが自動設定されていること
        self.assertEqual(str(record.start_latitude), '35.68950')
