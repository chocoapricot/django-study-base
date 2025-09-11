from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import Skill
from apps.master.forms import SkillForm, SkillCategoryForm

User = get_user_model()


class SkillModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_category_creation(self):
        """カテゴリ作成テスト"""
        category = Skill.objects.create(
            name='プログラミング言語',
            level=1,
            description='プログラミング言語カテゴリ',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(category.name, 'プログラミング言語')
        self.assertEqual(category.level, 1)
        self.assertTrue(category.is_category)
        self.assertEqual(str(category), '[カテゴリ] プログラミング言語')

    def test_skill_creation(self):
        """技能作成テスト"""
        # まずカテゴリを作成
        category = Skill.objects.create(
            name='プログラミング言語',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 技能を作成
        skill = Skill.objects.create(
            name='Java',
            level=2,
            parent=category,
            description='Javaプログラミングスキル',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(skill.name, 'Java')
        self.assertEqual(skill.level, 2)
        self.assertEqual(skill.parent, category)
        self.assertFalse(skill.is_category)
        self.assertEqual(str(skill), 'プログラミング言語 > Java')

    def test_hierarchy_validation(self):
        """階層バリデーションテスト"""
        from django.core.exceptions import ValidationError
        
        # カテゴリは親を持てない
        parent_category = Skill.objects.create(
            name='親カテゴリ',
            level=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            category = Skill(
                name='テストカテゴリ',
                level=1,
                parent=parent_category,  # カテゴリに親を設定
                created_by=self.user,
                updated_by=self.user
            )
            category.clean()
        
        # 技能は親が必要
        with self.assertRaises(ValidationError):
            skill = Skill(
                name='テスト技能',
                level=2,
                parent=None,  # 技能に親なし
                created_by=self.user,
                updated_by=self.user
            )
            skill.clean()

    def test_get_children(self):
        """子要素取得テスト"""
        # カテゴリ作成
        category = Skill.objects.create(
            name='プログラミング言語',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 子技能作成
        skill1 = Skill.objects.create(
            name='Java',
            level=2,
            parent=category,
            is_active=True,
            display_order=2,
            created_by=self.user,
            updated_by=self.user
        )
        skill2 = Skill.objects.create(
            name='Python',
            level=2,
            parent=category,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        children = list(category.get_children())
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0], skill2)  # display_order=1が先
        self.assertEqual(children[1], skill1)  # display_order=2が後




class SkillFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # テスト用カテゴリ作成
        self.category = Skill.objects.create(
            name='プログラミング言語',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )

    def test_category_direct_creation(self):
        """カテゴリ直接作成テスト"""
        # フォームを使わずに直接カテゴリを作成
        category = Skill.objects.create(
            name='データベース',
            level=1,
            description='データベース関連技能',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(category.name, 'データベース')
        self.assertEqual(category.level, 1)
        self.assertTrue(category.is_category)
        self.assertIsNone(category.parent)

    def test_skill_form_valid(self):
        """技能フォーム有効データテスト"""
        form_data = {
            'name': 'Python',
            'parent': self.category.pk,
            'description': 'Pythonプログラミングスキル',
            'is_active': True,
            'display_order': 1
        }
        form = SkillForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_skill_form_required_fields(self):
        """技能フォーム必須フィールドテスト"""
        form = SkillForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        # parentフィールドは必須だが、フォームレベルではなくモデルレベルでバリデーション




class SkillViewTest(TestCase):
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
                'add_skill', 'view_skill', 
                'change_skill', 'delete_skill'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        # テスト用カテゴリ作成
        self.category = Skill.objects.create(
            name='テストカテゴリ',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用技能作成
        self.skill = Skill.objects.create(
            name='テスト技能',
            level=2,
            parent=self.category,
            description='テスト技能の説明',
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()

    def test_skill_list_view(self):
        """技能一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('master:skill_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

    def test_skill_detail_view(self):
        """技能詳細ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:skill_detail', kwargs={'pk': self.skill.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

    def test_skill_create_view(self):
        """技能作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('master:skill_create'))
        self.assertEqual(response.status_code, 200)

    def test_skill_category_create_post(self):
        """カテゴリ作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '新しいカテゴリ',
            'description': '新しいカテゴリの説明',
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:skill_category_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        new_category = Skill.objects.get(name='新しいカテゴリ')
        self.assertTrue(new_category.is_category)

    def test_skill_create_post(self):
        """技能作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '新しい技能',
            'parent': self.category.pk,
            'description': '新しい技能の説明',
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:skill_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        new_skill = Skill.objects.get(name='新しい技能')
        self.assertEqual(new_skill.parent, self.category)

    def test_skill_update_view(self):
        """技能更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:skill_update', kwargs={'pk': self.skill.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_skill_update_post(self):
        """技能更新POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '更新された技能',
            'parent': self.category.pk,
            'description': '更新された説明',
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:skill_update', kwargs={'pk': self.skill.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.skill.refresh_from_db()
        self.assertEqual(self.skill.name, '更新された技能')
        self.assertEqual(self.skill.parent, self.category)

    def test_skill_delete_view(self):
        """技能削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:skill_delete', kwargs={'pk': self.skill.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_skill_delete_post(self):
        """技能削除POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.post(
            reverse('master:skill_delete', kwargs={'pk': self.skill.pk})
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertFalse(
            Skill.objects.filter(pk=self.skill.pk).exists()
        )

    def test_skill_search(self):
        """技能検索機能のテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:skill_list'),
            {'q': 'テスト'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

    def test_skill_level_filter(self):
        """技能レベルフィルタのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        # カテゴリのみ表示
        response = self.test_client.get(
            reverse('master:skill_list'),
            {'level': '1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストカテゴリ')
        
        # 技能のみ表示
        response = self.test_client.get(
            reverse('master:skill_list'),
            {'level': '2'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

    def test_skill_category_filter(self):
        """技能カテゴリフィルタのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:skill_list'),
            {'category': str(self.category.pk)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

