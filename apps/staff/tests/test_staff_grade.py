from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.staff.models import Staff, StaffGrade
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from datetime import date
from dateutil.relativedelta import relativedelta

class StaffGradeOverlapTest(TestCase):
    def setUp(self):
        # 会社データの作成（TenantManager用）
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        set_current_tenant_id(self.company.tenant_id)

        # ユーザーの作成（CurrentUserField用）
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password')
        from django_currentuser.middleware import _set_current_user as set_current_user
        set_current_user(self.user)

        # スタッフデータの作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            email='test@example.com',
            tenant_id=self.company.tenant_id
        )

    def test_grade_overlap_validation(self):
        """スタッフ等級の期間重複バリデーションのテスト"""
        
        # 1. 基準となるデータを登録 (2026/01/01 ～ 2026/01/15)
        StaffGrade.objects.create(
            staff=self.staff,
            grade_code='A-1',
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 1, 15),
            tenant_id=self.company.tenant_id
        )

        # 2. 開始日が既存の終了日と重なる (2026/01/15 ～ 2026/01/20) -> NG
        grade2 = StaffGrade(
            staff=self.staff,
            grade_code='A-2',
            valid_from=date(2026, 1, 15),
            valid_to=date(2026, 1, 20),
            tenant_id=self.company.tenant_id
        )
        with self.assertRaises(ValidationError):
            grade2.full_clean()
            grade2.save()

        # 3. 既存の翌日から開始する (2026/01/16 ～ 2026/01/31) -> OK
        grade3 = StaffGrade(
            staff=self.staff,
            grade_code='A-3',
            valid_from=date(2026, 1, 16),
            valid_to=date(2026, 1, 31),
            tenant_id=self.company.tenant_id
        )
        grade3.full_clean()
        grade3.save()

        # 4. 無期限データとの重複チェック
        # 現在: [1/1-1/15], [1/16-1/31]
        # 新規: [2/1 ～ 無期限] -> OK
        grade4 = StaffGrade(
            staff=self.staff,
            grade_code='B-1',
            valid_from=date(2026, 2, 1),
            valid_to=None,
            tenant_id=self.company.tenant_id
        )
        grade4.full_clean()
        grade4.save()

        # 現在: [1/1-1/15], [1/16-1/31], [2/1-無期限]
        # 新規: [2/10 ～ 2/20] -> NG (無期限枠内)
        grade5 = StaffGrade(
            staff=self.staff,
            grade_code='B-2',
            valid_from=date(2026, 2, 10),
            valid_to=date(2026, 2, 20),
            tenant_id=self.company.tenant_id
        )
        with self.assertRaises(ValidationError):
            grade5.full_clean()
            grade5.save()

    def test_unlimited_overlap(self):
        """無期限データ同士の重複テスト"""
        # 1. 全期間無期限を登録
        StaffGrade.objects.create(
            staff=self.staff,
            grade_code='FULL',
            valid_from=None,
            valid_to=None,
            tenant_id=self.company.tenant_id
        )

        # 2. 追加登録を試みる -> NG
        grade = StaffGrade(
            staff=self.staff,
            grade_code='ANY',
            valid_from=date(2026, 1, 1),
            tenant_id=self.company.tenant_id
        )
        with self.assertRaises(ValidationError):
            grade.full_clean()
            grade.save()

    def test_date_order_validation(self):
        """開始日と終了日の前後関係バリデーションのテスト"""
        grade = StaffGrade(
            staff=self.staff,
            grade_code='ERROR',
            valid_from=date(2026, 1, 31),
            valid_to=date(2026, 1, 1),
            tenant_id=self.company.tenant_id
        )
        with self.assertRaises(ValidationError):
            grade.full_clean()
            grade.save()

class StaffGradeDurationTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        set_current_tenant_id(self.company.tenant_id)

        # ユーザーの作成（CurrentUserField用）
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser_duration', password='password')
        from django_currentuser.middleware import _set_current_user as set_current_user
        set_current_user(self.user)

        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            tenant_id=self.company.tenant_id
        )

    def test_duration_calculation(self):
        """有効期間の計算 (durationプロパティ) のテスト"""
        # 1. ちょうど1ヶ月 (4/1 ～ 4/30) -> 終了日の翌日との差分なので 4/1~5/1 = 1ヶ月
        # ※relativedeltaの挙動に依存。4/1~4/30を「1ヶ月」と表示したい
        g1 = StaffGrade(
            staff=self.staff,
            valid_from=date(2025, 4, 1),
            valid_to=date(2025, 4, 30),
            tenant_id=self.company.tenant_id
        )
        self.assertEqual(g1.duration, "1ヶ月")

        # 2. ちょうど1年 (2025/1/1 ～ 2025/12/31) -> 1年0ヶ月
        g2 = StaffGrade(
            staff=self.staff,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            tenant_id=self.company.tenant_id
        )
        self.assertEqual(g2.duration, "1年0ヶ月")

        # 3. 1年3ヶ月 (2024/1/1 ～ 2025/3/31)
        g3 = StaffGrade(
            staff=self.staff,
            valid_from=date(2024, 1, 1),
            valid_to=date(2025, 3, 31),
            tenant_id=self.company.tenant_id
        )
        self.assertEqual(g3.duration, "1年3ヶ月")

        # 4. 1ヶ月未満 (4/1 ～ 4/15)
        g4 = StaffGrade(
            staff=self.staff,
            valid_from=date(2025, 4, 1),
            valid_to=date(2025, 4, 15),
            tenant_id=self.company.tenant_id
        )
        self.assertEqual(g4.duration, "1ヶ月未満")

        # 5. 終了日なし (無期限) の場合
        # 本日が2026/02/07と想定（システム日時により変動するため、開始日を調整）
        from django.utils import timezone
        today = timezone.localdate()
        # ちょうど2年前の同日から開始
        start_date = today - relativedelta(years=2)
        g5 = StaffGrade(
            staff=self.staff,
            valid_from=start_date,
            valid_to=None,
            tenant_id=self.company.tenant_id
        )
        # 終了日なしなので今日までで計算 -> 2年0ヶ月
        self.assertEqual(g5.duration, "2年0ヶ月")

        # 6. 未来から始まる開始日なし -> 空文字
        g6 = StaffGrade(
            staff=self.staff,
            valid_from=today + relativedelta(days=1),
            valid_to=None,
            tenant_id=self.company.tenant_id
        )
        self.assertEqual(g6.duration, "")
