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
            daily_overtime_enabled=True,
            daily_overtime_hours=8,
            weekly_overtime_enabled=True,
            weekly_overtime_hours=40,
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
        self.assertTrue(pattern.daily_overtime_enabled)
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
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class OvertimePatternListViewTest(TestCase):
    """時間外算出パターン一覧表示のテスト"""

    @classmethod
    def setUpTestData(cls):
        """テストクラス用のデータを一度だけ作成"""
        User = get_user_model()
        cls.user = User.objects.create_user(
            username='testuser_list',
            password='password123',
            email='testuser_list@example.com',
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
        self.client.login(username='testuser_list', password='password123')

    def test_view_renders_midnight_premium_text(self):
        """深夜割増が有効な場合、「深夜」が表示される"""
        url = reverse('master:overtime_pattern_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # "Premium On" のパターンで「深夜」が表示され、
        # "Premium Off" のパターンでは表示されないため、合計1回表示されるはず
        self.assertContains(response, '深夜', count=1)

class OvertimePatternViewPermissionTest(TestCase):
    """
    OvertimePattern views permission tests.
    """
    def setUp(self):
        """
        Set up the test environment.
        """
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.overtime_pattern = OvertimePattern.objects.create(name='Test Overtime Pattern')
        self.content_type = ContentType.objects.get_for_model(OvertimePattern)

    def test_overtime_pattern_list_view_permission(self):
        """
        Test that the overtime_pattern_list view requires the correct permission.
        """
        url = reverse('master:overtime_pattern_list')
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='view_overtimepattern')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_overtime_pattern_create_view_permission(self):
        """
        Test that the overtime_pattern_create view requires the correct permission.
        """
        url = reverse('master:overtime_pattern_create')
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='add_overtimepattern')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_overtime_pattern_update_view_permission(self):
        """
        Test that the overtime_pattern_update view requires the correct permission.
        """
        url = reverse('master:overtime_pattern_update', args=[self.overtime_pattern.pk])
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='change_overtimepattern')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_overtime_pattern_delete_view_permission(self):
        """
        Test that the overtime_pattern_delete view requires the correct permission.
        """
        url = reverse('master:overtime_pattern_delete', args=[self.overtime_pattern.pk])
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='delete_overtimepattern')
        self.user.user_permissions.add(permission)
        # Re-create the object as it might have been deleted in other tests
        overtime_pattern_for_delete = OvertimePattern.objects.create(name='Test Overtime Pattern for Delete')
        url_for_delete = reverse('master:overtime_pattern_delete', args=[overtime_pattern_for_delete.pk])
        response = self.client.post(url_for_delete)
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)

    def test_overtime_pattern_change_history_list_view_permission(self):
        """
        Test that the overtime_pattern_change_history_list view requires the correct permission.
        """
        url = reverse('master:overtime_pattern_change_history_list')
        self.client.login(username='testuser', password='password')

        # Test without permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test with permission
        permission = Permission.objects.get(content_type=self.content_type, codename='view_overtimepattern')
        self.user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
