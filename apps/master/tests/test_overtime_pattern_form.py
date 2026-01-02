from django.test import TestCase
from apps.master.forms_kintai import OvertimePatternForm
from apps.master.models import OvertimePattern


class OvertimePatternFormTest(TestCase):
    """時間外算出パターンフォームのテスト"""

    def test_valid_premium_form(self):
        """割増方式の有効なフォームテスト"""
        form_data = {
            'name': '割増パターン',
            'calculation_type': 'premium',
            'daily_overtime_enabled': True,
            'daily_overtime_hours': 8,
            'weekly_overtime_enabled': True,
            'weekly_overtime_hours': 40,
            'monthly_overtime_enabled': False,
            'monthly_estimated_enabled': False,
            'monthly_range_min': 140,
            'monthly_range_max': 160,

            'days_28_hours': 160,
            'days_28_minutes': 0,
            'days_29_hours': 165,
            'days_29_minutes': 42,
            'days_30_hours': 171,
            'days_30_minutes': 25,
            'days_31_hours': 177,
            'days_31_minutes': 8,
            'display_order': 1,
            'is_active': True
        }
        form = OvertimePatternForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_monthly_range_form(self):
        """月単位時間範囲方式の有効なフォームテスト"""
        form_data = {
            'name': '時間範囲パターン',
            'calculation_type': 'monthly_range',
            'daily_overtime_enabled': False,
            'weekly_overtime_enabled': False,
            'monthly_overtime_enabled': False,
            'monthly_estimated_enabled': False,
            'monthly_range_min': 140,
            'monthly_range_max': 160,

            'days_28_hours': 160,
            'days_28_minutes': 0,
            'days_29_hours': 165,
            'days_29_minutes': 42,
            'days_30_hours': 171,
            'days_30_minutes': 25,
            'days_31_hours': 177,
            'days_31_minutes': 8,
            'display_order': 1,
            'is_active': True
        }
        form = OvertimePatternForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_variable_form(self):
        """変形労働方式の有効なフォームテスト"""
        form_data = {
            'name': '変形労働パターン',
            'calculation_type': 'variable',
            'monthly_overtime_enabled': True,
            'monthly_overtime_hours': 60,
            'monthly_estimated_enabled': True,
            'monthly_estimated_hours': 20,
            'monthly_range_min': 140,
            'monthly_range_max': 160,
            'daily_overtime_enabled': True,
            'daily_overtime_hours': 8,
            'weekly_overtime_enabled': True,
            'weekly_overtime_hours': 40,
            'days_28_hours': 160,
            'days_28_minutes': 0,
            'days_29_hours': 165,
            'days_29_minutes': 42,
            'days_30_hours': 171,
            'days_30_minutes': 25,
            'days_31_hours': 177,
            'days_31_minutes': 8,
            'display_order': 1,
            'is_active': True
        }
        form = OvertimePatternForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_name(self):
        """名称が欠けている無効なフォームテスト"""
        form_data = {
            'calculation_type': 'premium',
            'display_order': 1,
            'is_active': True
        }
        form = OvertimePatternForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_form_save(self):
        """フォーム保存テスト"""
        form_data = {
            'name': '保存テストパターン',
            'calculation_type': 'premium',
            'daily_overtime_enabled': True,
            'daily_overtime_hours': 8,
            'weekly_overtime_enabled': False,
            'monthly_overtime_enabled': False,
            'monthly_estimated_enabled': False,
            'monthly_range_min': 140,
            'monthly_range_max': 160,

            'days_28_hours': 160,
            'days_28_minutes': 0,
            'days_29_hours': 165,
            'days_29_minutes': 42,
            'days_30_hours': 171,
            'days_30_minutes': 25,
            'days_31_hours': 177,
            'days_31_minutes': 8,
            'display_order': 1,
            'is_active': True
        }
        form = OvertimePatternForm(data=form_data)
        self.assertTrue(form.is_valid())
        pattern = form.save()
        self.assertEqual(pattern.name, '保存テストパターン')
        self.assertEqual(pattern.calculation_type, 'premium')
        self.assertTrue(pattern.daily_overtime_enabled)
        self.assertEqual(OvertimePattern.objects.count(), 1)

    def test_form_save_with_midnight_premium(self):
        """深夜割増計算を含むフォーム保存テスト"""
        form_data = {
            'name': '深夜割増テスト',
            'calculation_type': 'premium',
            'calculate_midnight_premium': True,
            'daily_overtime_enabled': True,
            'daily_overtime_hours': 8,
            'weekly_overtime_enabled': False,
            'monthly_overtime_enabled': False,
            'monthly_estimated_enabled': False,
            'monthly_range_min': 140,
            'monthly_range_max': 160,

            'days_28_hours': 160,
            'days_28_minutes': 0,
            'days_29_hours': 165,
            'days_29_minutes': 42,
            'days_30_hours': 171,
            'days_30_minutes': 25,
            'days_31_hours': 177,
            'days_31_minutes': 8,
            'display_order': 1,
            'is_active': True,
        }
        form = OvertimePatternForm(data=form_data)
        self.assertTrue(form.is_valid())
        pattern = form.save()
        self.assertEqual(pattern.name, '深夜割増テスト')
        self.assertTrue(pattern.calculate_midnight_premium)
        self.assertEqual(OvertimePattern.objects.count(), 1)
