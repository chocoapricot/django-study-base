from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.system.settings.models import Menu
from apps.system.settings.forms import MenuForm

User = get_user_model()

class MenuModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_menu_creation(self):
        """Menuモデルの作成テスト"""
        menu = Menu.objects.create(
            name='テストメニュー',
            url='/test/',
            icon='bi-test',
            icon_style='color:#ff0000;',
            level=0,
            disp_seq=1,
            active=True
        )
        
        self.assertEqual(menu.name, 'テストメニュー')
        self.assertEqual(menu.url, '/test/')
        self.assertEqual(menu.icon, 'bi-test')
        self.assertEqual(menu.disp_seq, 1)
        self.assertTrue(menu.active)
        self.assertIsNone(menu.parent)
        self.assertEqual(str(menu), 'テストメニュー')

    def test_menu_hierarchy(self):
        """メニューの階層構造テスト"""
        parent_menu = Menu.objects.create(
            name='親メニュー',
            url='/parent/',
            level=0,
            disp_seq=1
        )
        
        child_menu = Menu.objects.create(
            name='子メニュー',
            url='/child/',
            level=1,
            parent=parent_menu,
            disp_seq=1
        )
        
        self.assertEqual(child_menu.parent, parent_menu)
        self.assertEqual(child_menu.level, 1)
        self.assertIn(child_menu, parent_menu.get_children())
        self.assertTrue(parent_menu.has_children)
        self.assertEqual(str(child_menu), '親メニュー > 子メニュー')

    def test_menu_ordering(self):
        """メニューの表示順テスト"""
        menu1 = Menu.objects.create(name='メニュー1', url='/1/', level=0, disp_seq=2)
        menu2 = Menu.objects.create(name='メニュー2', url='/2/', level=0, disp_seq=1)
        menu3 = Menu.objects.create(name='メニュー3', url='/3/', level=1, disp_seq=1)
        
        menus = list(Menu.objects.all())
        self.assertEqual(menus[0], menu2)  # level 0, disp_seq 1
        self.assertEqual(menus[1], menu1)  # level 0, disp_seq 2
        self.assertEqual(menus[2], menu3)  # level 1, disp_seq 1

    def test_menu_active_filter(self):
        """有効メニューのフィルタリングテスト"""
        Menu.objects.create(name='有効', url='/active/', active=True)
        Menu.objects.create(name='無効', url='/inactive/', active=False)
        
        active_menus = Menu.objects.filter(active=True)
        self.assertEqual(active_menus.count(), 1)
        self.assertEqual(active_menus[0].name, '有効')

    def test_is_active_for_path(self):
        """URLパスによるアクティブ判定のテスト"""
        home_menu = Menu.objects.create(name='ホーム', url='/', level=0, exact_match=False, active=True)
        staff_menu = Menu.objects.create(name='スタッフ', url='/staff/', level=0, exact_match=True, active=True)
        staff_detail = Menu.objects.create(name='スタッフ詳細', url='/staff/detail/', level=1, parent=staff_menu, exact_match=False, active=True)
        
        # ホームの判定
        self.assertTrue(home_menu.is_active_for_path('/'))
        self.assertFalse(home_menu.is_active_for_path('/staff/'))
        
        # スタッフ（完全一致=True）の判定
        self.assertTrue(staff_menu.is_active_for_path('/staff/'))
        # 子メニューがアクティブな場合、親は非アクティブ（より具体的なメニューが優先されるロジック）
        self.assertFalse(staff_menu.is_active_for_path('/staff/detail/'))
        self.assertTrue(staff_detail.is_active_for_path('/staff/detail/'))

    def test_has_permission(self):
        """アクセス権限チェックのテスト"""
        public_menu = Menu.objects.create(name='公開', url='/public/', level=0, required_permission='')
        private_menu = Menu.objects.create(name='制限', url='/private/', level=0, required_permission='accounts.view_myuser')
        
        from django.contrib.auth.models import AnonymousUser
        anon_user = AnonymousUser()
        self.assertFalse(public_menu.has_permission(anon_user))
        
        self.assertTrue(public_menu.has_permission(self.user))
        self.assertFalse(private_menu.has_permission(self.user))
        
        perm = Permission.objects.get(codename='view_myuser', content_type__app_label='accounts')
        self.user.user_permissions.add(perm)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(private_menu.has_permission(self.user))

class MenuFormTest(TestCase):
    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'name': 'テストメニュー',
            'url': '/test/',
            'icon': 'bi-test',
            'icon_style': 'color:#ff0000;',
            'level': 0,
            'disp_seq': 1,
            'active': True
        }
        form = MenuForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = MenuForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('url', form.errors)

    def test_display_order_validation(self):
        """表示順のバリデーションテスト"""
        form_data = {
            'name': 'テストメニュー',
            'url': '/test/',
            'disp_seq': -1,  # 不正な値
            'level': 0,
        }
        form = MenuForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('disp_seq', form.errors)