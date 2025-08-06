from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.system.settings.models import Dropdowns
from apps.system.settings.forms import DropdownsForm

User = get_user_model()


class DropdownsModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_dropdowns_creation(self):
        """Dropdownsモデルの作成テスト"""
        dropdown = Dropdowns.objects.create(
            category='test_category',
            code='TEST001',
            name='テストドロップダウン',
            display_order=1,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(dropdown.category, 'test_category')
        self.assertEqual(dropdown.code, 'TEST001')
        self.assertEqual(dropdown.name, 'テストドロップダウン')
        self.assertEqual(dropdown.display_order, 1)
        self.assertTrue(dropdown.is_active)
        self.assertEqual(str(dropdown), 'test_category - TEST001 - テストドロップダウン')

    def test_dropdowns_unique_constraint(self):
        """カテゴリとコードの組み合わせの一意性テスト"""
        Dropdowns.objects.create(
            category='test_category',
            code='TEST001',
            name='テストドロップダウン1',
            created_by=self.user,
            updated_by=self.user
        )
        
        # 同じカテゴリとコードの組み合わせは作成できない
        with self.assertRaises(Exception):
            Dropdowns.objects.create(
                category='test_category',
                code='TEST001',
                name='テストドロップダウン2',
                created_by=self.user,
                updated_by=self.user
            )

    def test_dropdowns_ordering(self):
        """Dropdownsの表示順テスト"""
        dropdown1 = Dropdowns.objects.create(
            category='test_category',
            code='TEST001',
            name='テスト1',
            display_order=2,
            created_by=self.user,
            updated_by=self.user
        )
        dropdown2 = Dropdowns.objects.create(
            category='test_category',
            code='TEST002',
            name='テスト2',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        dropdowns = list(Dropdowns.objects.all())
        self.assertEqual(dropdowns[0], dropdown2)  # display_order=1が先
        self.assertEqual(dropdowns[1], dropdown1)  # display_order=2が後

    def test_dropdowns_active_filter(self):
        """アクティブなドロップダウンのフィルタテスト"""
        active_dropdown = Dropdowns.objects.create(
            category='test_category',
            code='ACTIVE',
            name='アクティブ',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        inactive_dropdown = Dropdowns.objects.create(
            category='test_category',
            code='INACTIVE',
            name='非アクティブ',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        active_dropdowns = Dropdowns.objects.filter(is_active=True)
        self.assertIn(active_dropdown, active_dropdowns)
        self.assertNotIn(inactive_dropdown, active_dropdowns)


class DropdownsFormTest(TestCase):
    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'category': 'test_category',
            'code': 'TEST001',
            'name': 'テストドロップダウン',
            'display_order': 1,
            'is_active': True
        }
        form = DropdownsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = DropdownsForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)
        self.assertIn('code', form.errors)
        self.assertIn('name', form.errors)

    def test_display_order_validation(self):
        """表示順のバリデーションテスト"""
        form_data = {
            'category': 'test_category',
            'code': 'TEST001',
            'name': 'テストドロップダウン',
            'display_order': -1,  # 負の値
            'is_active': True
        }
        form = DropdownsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('display_order', form.errors)


class DropdownsViewTest(TestCase):
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
                'add_dropdowns', 'view_dropdowns', 
                'change_dropdowns', 'delete_dropdowns'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.dropdown = Dropdowns.objects.create(
            category='test_category',
            code='TEST001',
            name='テストドロップダウン',
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()

    def test_dropdowns_list_view(self):
        """ドロップダウン一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('settings:dropdowns_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストドロップダウン')

    def test_dropdowns_create_view(self):
        """ドロップダウン作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('settings:dropdowns_create'))
        self.assertEqual(response.status_code, 200)

    def test_dropdowns_detail_view(self):
        """ドロップダウン詳細ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:dropdowns_detail', kwargs={'pk': self.dropdown.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストドロップダウン')

    def test_dropdowns_update_view(self):
        """ドロップダウン更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:dropdowns_update', kwargs={'pk': self.dropdown.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_dropdowns_delete_view(self):
        """ドロップダウン削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:dropdowns_delete', kwargs={'pk': self.dropdown.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_dropdowns_create_post(self):
        """ドロップダウン作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'category': 'new_category',
            'code': 'NEW001',
            'name': '新しいドロップダウン',
            'display_order': 1,
            'is_active': True
        }
        
        response = self.test_client.post(
            reverse('settings:dropdowns_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            Dropdowns.objects.filter(
                category='new_category',
                code='NEW001'
            ).exists()
        )