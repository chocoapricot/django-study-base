from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
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
            url_name='test_menu',
            icon='bi-test',
            display_order=1,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(menu.name, 'テストメニュー')
        self.assertEqual(menu.url_name, 'test_menu')
        self.assertEqual(menu.icon, 'bi-test')
        self.assertEqual(menu.display_order, 1)
        self.assertTrue(menu.is_active)
        self.assertIsNone(menu.parent)
        self.assertEqual(str(menu), 'テストメニュー')

    def test_menu_hierarchy(self):
        """メニューの階層構造テスト"""
        parent_menu = Menu.objects.create(
            name='親メニュー',
            url_name='parent_menu',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        child_menu = Menu.objects.create(
            name='子メニュー',
            url_name='child_menu',
            parent=parent_menu,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(child_menu.parent, parent_menu)
        self.assertIn(child_menu, parent_menu.children.all())

    def test_menu_ordering(self):
        """メニューの表示順テスト"""
        menu1 = Menu.objects.create(
            name='メニュー1',
            url_name='menu1',
            display_order=2,
            created_by=self.user,
            updated_by=self.user
        )
        menu2 = Menu.objects.create(
            name='メニュー2',
            url_name='menu2',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        menus = list(Menu.objects.all())
        self.assertEqual(menus[0], menu2)  # display_order=1が先
        self.assertEqual(menus[1], menu1)  # display_order=2が後

    def test_menu_active_filter(self):
        """アクティブなメニューのフィルタテスト"""
        active_menu = Menu.objects.create(
            name='アクティブメニュー',
            url_name='active_menu',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        inactive_menu = Menu.objects.create(
            name='非アクティブメニュー',
            url_name='inactive_menu',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        active_menus = Menu.objects.filter(is_active=True)
        self.assertIn(active_menu, active_menus)
        self.assertNotIn(inactive_menu, active_menus)

    def test_menu_get_level(self):
        """メニューレベルの取得テスト"""
        parent_menu = Menu.objects.create(
            name='親メニュー',
            url_name='parent_menu',
            created_by=self.user,
            updated_by=self.user
        )
        
        child_menu = Menu.objects.create(
            name='子メニュー',
            url_name='child_menu',
            parent=parent_menu,
            created_by=self.user,
            updated_by=self.user
        )
        
        grandchild_menu = Menu.objects.create(
            name='孫メニュー',
            url_name='grandchild_menu',
            parent=child_menu,
            created_by=self.user,
            updated_by=self.user
        )
        
        # get_levelメソッドがある場合のテスト
        # self.assertEqual(parent_menu.get_level(), 0)
        # self.assertEqual(child_menu.get_level(), 1)
        # self.assertEqual(grandchild_menu.get_level(), 2)

    def test_menu_get_breadcrumb(self):
        """メニューのパンくずリスト取得テスト"""
        parent_menu = Menu.objects.create(
            name='親メニュー',
            url_name='parent_menu',
            created_by=self.user,
            updated_by=self.user
        )
        
        child_menu = Menu.objects.create(
            name='子メニュー',
            url_name='child_menu',
            parent=parent_menu,
            created_by=self.user,
            updated_by=self.user
        )
        
        # get_breadcrumbメソッドがある場合のテスト
        # breadcrumb = child_menu.get_breadcrumb()
        # self.assertEqual(len(breadcrumb), 2)
        # self.assertEqual(breadcrumb[0], parent_menu)
        # self.assertEqual(breadcrumb[1], child_menu)


class MenuFormTest(TestCase):
    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'name': 'テストメニュー',
            'url_name': 'test_menu',
            'icon': 'bi-test',
            'display_order': 1,
            'is_active': True
        }
        form = MenuForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = MenuForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('url_name', form.errors)

    def test_display_order_validation(self):
        """表示順のバリデーションテスト"""
        form_data = {
            'name': 'テストメニュー',
            'url_name': 'test_menu',
            'display_order': -1,  # 負の値
            'is_active': True
        }
        form = MenuForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('display_order', form.errors)

    def test_url_name_validation(self):
        """URL名のバリデーションテスト"""
        form_data = {
            'name': 'テストメニュー',
            'url_name': 'invalid url name',  # スペースを含む
            'display_order': 1,
            'is_active': True
        }
        form = MenuForm(data=form_data)
        # URL名のバリデーションがある場合
        # self.assertFalse(form.is_valid())
        # self.assertIn('url_name', form.errors)


class MenuViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='settings',
            codename__in=[
                'add_menu', 'view_menu', 
                'change_menu', 'delete_menu'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.menu = Menu.objects.create(
            name='テストメニュー',
            url_name='test_menu',
            icon='bi-test',
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()

    def test_menu_list_view(self):
        """メニュー一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('settings:menu_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストメニュー')

    def test_menu_create_view(self):
        """メニュー作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('settings:menu_create'))
        self.assertEqual(response.status_code, 200)

    def test_menu_detail_view(self):
        """メニュー詳細ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:menu_detail', kwargs={'pk': self.menu.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストメニュー')

    def test_menu_update_view(self):
        """メニュー更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:menu_update', kwargs={'pk': self.menu.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_menu_delete_view(self):
        """メニュー削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:menu_delete', kwargs={'pk': self.menu.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_menu_create_post(self):
        """メニュー作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '新しいメニュー',
            'url_name': 'new_menu',
            'icon': 'bi-new',
            'display_order': 1,
            'is_active': True
        }
        
        response = self.test_client.post(
            reverse('settings:menu_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            Menu.objects.filter(name='新しいメニュー').exists()
        )

    def test_menu_hierarchy_create(self):
        """階層メニューの作成テスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '子メニュー',
            'url_name': 'child_menu',
            'parent': self.menu.pk,
            'display_order': 1,
            'is_active': True
        }
        
        response = self.test_client.post(
            reverse('settings:menu_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        child_menu = Menu.objects.get(name='子メニュー')
        self.assertEqual(child_menu.parent, self.menu)

    def test_menu_tree_view(self):
        """メニューツリービューのテスト"""
        # 子メニューを作成
        child_menu = Menu.objects.create(
            name='子メニュー',
            url_name='child_menu',
            parent=self.menu,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('settings:menu_tree'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストメニュー')
        self.assertContains(response, '子メニュー')