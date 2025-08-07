from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import Qualification
from apps.master.forms import QualificationForm, QualificationCategoryForm

User = get_user_model()


class QualificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_category_creation(self):
        """カテゴリ作成テスト"""
        category = Qualification.objects.create(
            name='国家資格',
            level=1,
            description='国家資格カテゴリ',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(category.name, '国家資格')
        self.assertEqual(category.level, 1)
        self.assertTrue(category.is_category)
        self.assertFalse(category.is_qualification)
        self.assertEqual(str(category), '[カテゴリ] 国家資格')

    def test_qualification_creation(self):
        """資格作成テスト"""
        # まずカテゴリを作成
        category = Qualification.objects.create(
            name='国家資格',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 資格を作成
        qualification = Qualification.objects.create(
            name='基本情報技術者試験',
            level=2,
            parent=category,
            description='基本情報技術者試験の説明',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(qualification.name, '基本情報技術者試験')
        self.assertEqual(qualification.level, 2)
        self.assertEqual(qualification.parent, category)
        self.assertFalse(qualification.is_category)
        self.assertTrue(qualification.is_qualification)
        self.assertEqual(str(qualification), '国家資格 > 基本情報技術者試験')

    def test_hierarchy_validation(self):
        """階層バリデーションテスト"""
        from django.core.exceptions import ValidationError
        
        # カテゴリは親を持てない
        parent_category = Qualification.objects.create(
            name='親カテゴリ',
            level=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            category = Qualification(
                name='テストカテゴリ',
                level=1,
                parent=parent_category,  # カテゴリに親を設定
                created_by=self.user,
                updated_by=self.user
            )
            category.clean()
        
        # 資格は親が必要
        with self.assertRaises(ValidationError):
            qualification = Qualification(
                name='テスト資格',
                level=2,
                parent=None,  # 資格に親なし
                created_by=self.user,
                updated_by=self.user
            )
            qualification.clean()

    def test_get_children(self):
        """子要素取得テスト"""
        # カテゴリ作成
        category = Qualification.objects.create(
            name='国家資格',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 子資格作成
        qual1 = Qualification.objects.create(
            name='基本情報技術者試験',
            level=2,
            parent=category,
            is_active=True,
            display_order=2,
            created_by=self.user,
            updated_by=self.user
        )
        qual2 = Qualification.objects.create(
            name='応用情報技術者試験',
            level=2,
            parent=category,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        children = list(category.get_children())
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0], qual2)  # display_order=1が先
        self.assertEqual(children[1], qual1)  # display_order=2が後






class QualificationFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # テスト用カテゴリ作成
        self.category = Qualification.objects.create(
            name='国家資格',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )

    def test_category_direct_creation(self):
        """カテゴリ直接作成テスト"""
        # フォームを使わずに直接カテゴリを作成
        category = Qualification.objects.create(
            name='民間資格',
            level=1,
            description='民間資格カテゴリ',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(category.name, '民間資格')
        self.assertEqual(category.level, 1)
        self.assertTrue(category.is_category)
        self.assertIsNone(category.parent)

    def test_qualification_form_valid(self):
        """資格フォーム有効データテスト"""
        form_data = {
            'name': 'テスト資格',
            'parent': self.category.pk,
            'description': 'テスト資格の説明',
            'is_active': True,
            'display_order': 1
        }
        form = QualificationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_qualification_form_required_fields(self):
        """資格フォーム必須フィールドテスト"""
        form = QualificationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        # parentフィールドは必須だが、フォームレベルではなくモデルレベルでバリデーション




class QualificationViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='master',
            codename__in=[
                'add_qualification', 'view_qualification', 
                'change_qualification', 'delete_qualification'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        # テスト用カテゴリ作成
        self.category = Qualification.objects.create(
            name='テストカテゴリ',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用資格作成
        self.qualification = Qualification.objects.create(
            name='テスト資格',
            level=2,
            parent=self.category,
            description='テスト資格の説明',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()

    def test_qualification_list_view(self):
        """資格一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('master:qualification_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')

    def test_qualification_detail_view(self):
        """資格詳細ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:qualification_detail', kwargs={'pk': self.qualification.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')

    def test_qualification_create_view(self):
        """資格作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('master:qualification_create'))
        self.assertEqual(response.status_code, 200)

    def test_qualification_category_create_post(self):
        """カテゴリ作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '新しいカテゴリ',
            'description': '新しいカテゴリの説明',
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:qualification_category_create'),
            data=form_data
        )
        

        self.assertEqual(response.status_code, 302)  # リダイレクト
        new_category = Qualification.objects.get(name='新しいカテゴリ')
        self.assertTrue(new_category.is_category)

    def test_qualification_create_post(self):
        """資格作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '新しい資格',
            'parent': self.category.pk,
            'description': '新しい資格の説明',
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:qualification_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        new_qualification = Qualification.objects.get(name='新しい資格')
        self.assertTrue(new_qualification.is_qualification)
        self.assertEqual(new_qualification.parent, self.category)

    def test_qualification_update_view(self):
        """資格更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:qualification_update', kwargs={'pk': self.qualification.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_qualification_update_post(self):
        """資格更新POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '更新された資格',
            'parent': self.category.pk,
            'description': '更新された資格の説明',
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:qualification_update', kwargs={'pk': self.qualification.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.qualification.refresh_from_db()
        self.assertEqual(self.qualification.name, '更新された資格')
        self.assertEqual(self.qualification.parent, self.category)

    def test_qualification_delete_view(self):
        """資格削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:qualification_delete', kwargs={'pk': self.qualification.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_qualification_delete_post(self):
        """資格削除POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.post(
            reverse('master:qualification_delete', kwargs={'pk': self.qualification.pk})
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertFalse(
            Qualification.objects.filter(pk=self.qualification.pk).exists()
        )

    def test_qualification_search(self):
        """資格検索機能のテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:qualification_list'),
            {'q': 'テスト'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')

    def test_qualification_level_filter(self):
        """資格レベルフィルタのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        # カテゴリのみ表示
        response = self.test_client.get(
            reverse('master:qualification_list'),
            {'level': '1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストカテゴリ')
        
        # 資格のみ表示
        response = self.test_client.get(
            reverse('master:qualification_list'),
            {'level': '2'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')

    def test_qualification_category_filter(self):
        """資格カテゴリフィルタのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:qualification_list'),
            {'category': str(self.category.pk)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')