from django.test import TestCase
from apps.master.models import OvertimePattern


class OvertimePatternModelTest(TestCase):
    """時間外算出パターンモデルのテスト"""

    def test_create_premium_pattern(self):
        """割増方式のパターン作成テスト"""
        pattern = OvertimePattern.objects.create(
            name="割増パターン1",
            calculation_type="premium",
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
            weekly_overtime_enabled=True,
            weekly_overtime_hours=40,
            monthly_overtime_enabled=True,
            monthly_overtime_hours=60,
            is_active=True
        )
        self.assertEqual(pattern.name, "割増パターン1")
        self.assertEqual(pattern.calculation_type, "premium")
        self.assertTrue(pattern.daily_overtime_enabled)
        self.assertEqual(pattern.daily_overtime_hours, 8)

    def test_create_monthly_range_pattern(self):
        """月単位時間範囲パターン作成テスト"""
        pattern = OvertimePattern.objects.create(
            name="時間範囲パターン1",
            calculation_type="monthly_range",
            monthly_range_min=140,
            monthly_range_max=160,
            is_active=True
        )
        self.assertEqual(pattern.name, "時間範囲パターン1")
        self.assertEqual(pattern.calculation_type, "monthly_range")
        self.assertEqual(pattern.monthly_range_min, 140)
        self.assertEqual(pattern.monthly_range_max, 160)

    def test_create_variable_pattern(self):
        """1ヶ月単位変形労働パターン作成テスト"""
        pattern = OvertimePattern.objects.create(
            name="変形労働パターン1",
            calculation_type="variable",
            variable_daily_overtime_enabled=True,
            variable_daily_overtime_hours=8,
            variable_weekly_overtime_enabled=True,
            variable_weekly_overtime_hours=40,
            days_28_hours=160,
            days_28_minutes=0,
            days_29_hours=165,
            days_29_minutes=42,
            days_30_hours=171,
            days_30_minutes=25,
            days_31_hours=177,
            days_31_minutes=8,
            is_active=True
        )
        self.assertEqual(pattern.name, "変形労働パターン1")
        self.assertEqual(pattern.calculation_type, "variable")
        self.assertTrue(pattern.variable_daily_overtime_enabled)
        self.assertEqual(pattern.days_28_hours, 160)
        self.assertEqual(pattern.days_29_minutes, 42)

    def test_default_values(self):
        """デフォルト値のテスト"""
        pattern = OvertimePattern.objects.create(
            name="デフォルトパターン"
        )
        self.assertEqual(pattern.calculation_type, "premium")
        self.assertEqual(pattern.daily_overtime_hours, 8)
        self.assertEqual(pattern.weekly_overtime_hours, 40)
        self.assertEqual(pattern.days_28_hours, 160)
        self.assertEqual(pattern.days_29_hours, 165)
        self.assertEqual(pattern.days_30_hours, 171)
        self.assertEqual(pattern.days_31_hours, 177)


from django.urls import reverse
from apps.accounts.models import MyUser
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class OvertimePatternListViewTest(TestCase):
    """時間外算出パターン一覧表示のテスト"""

    @classmethod
    def setUpTestData(cls):
        """テストクラス用のデータを一度だけ作成"""
        cls.user = MyUser.objects.create_user(
            username='testuser',
            password='password123',
            email='testuser@example.com',
            is_active=True
        )
        content_type = ContentType.objects.get_for_model(OvertimePattern)
        permission, _ = Permission.objects.get_or_create(
            codename='view_overtimepattern',
            content_type=content_type,
        )
        cls.user.user_permissions.add(permission)

        # テストデータ作成
        OvertimePattern.objects.create(
            name="Premium On",
            calculate_midnight_premium=True,
        )
        OvertimePattern.objects.create(
            name="Premium Off",
            calculate_midnight_premium=False,
        )

    def setUp(self):
        """各テストの前に実行"""
        self.client.login(username='testuser', password='password123')

    def test_view_renders_midnight_premium_text(self):
        """深夜割増が有効な場合、「深夜」が表示される"""
        url = reverse('master:overtime_pattern_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # "Premium On" のパターンで「深夜」が表示され、
        # "Premium Off" のパターンでは表示されないため、合計1回表示されるはず
        self.assertContains(response, '深夜', count=1)
