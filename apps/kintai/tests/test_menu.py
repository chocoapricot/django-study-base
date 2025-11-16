from django.test import TestCase
from apps.system.settings.models import Menu


class KintaiMenuTest(TestCase):
    """勤怠管理メニューのテスト"""

    def test_menu_exists(self):
        """勤怠管理メニューが存在することを確認"""
        parent_menu = Menu.objects.filter(name='勤怠管理').first()
        self.assertIsNotNone(parent_menu, '勤怠管理メニューが存在しません')
        self.assertEqual(parent_menu.url, '/kintai/')
        self.assertEqual(parent_menu.level, 0)
        self.assertTrue(parent_menu.active)

    def test_child_menu_exists(self):
        """月次勤怠一覧メニューが存在することを確認"""
        child_menu = Menu.objects.filter(name='月次勤怠一覧').first()
        self.assertIsNotNone(child_menu, '月次勤怠一覧メニューが存在しません')
        self.assertEqual(child_menu.url, '/kintai/timesheet/')
        self.assertEqual(child_menu.level, 1)
        self.assertTrue(child_menu.active)

    def test_menu_hierarchy(self):
        """メニューの階層構造を確認"""
        parent_menu = Menu.objects.filter(name='勤怠管理').first()
        child_menu = Menu.objects.filter(name='月次勤怠一覧').first()
        
        self.assertIsNotNone(parent_menu)
        self.assertIsNotNone(child_menu)
        self.assertEqual(child_menu.parent, parent_menu)
