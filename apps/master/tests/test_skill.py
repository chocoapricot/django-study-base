from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import Skill
from apps.master.forms import SkillForm

User = get_user_model()


class SkillModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_skill_creation(self):
        """Skillモデルの作成テスト"""
        skill = Skill.objects.create(
            name='Java',
            category='プログラミング言語',
            description='Javaプログラミングスキル',
            required_level='intermediate',
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(skill.name, 'Java')
        self.assertEqual(skill.category, 'プログラミング言語')
        self.assertEqual(skill.description, 'Javaプログラミングスキル')
        self.assertEqual(skill.required_level, 'intermediate')
        self.assertTrue(skill.is_active)
        self.assertEqual(str(skill), 'Java')

    def test_skill_ordering(self):
        """Skillの表示順テスト"""
        skill1 = Skill.objects.create(
            name='技能1',
            category='テスト',
            display_order=2,
            created_by=self.user,
            updated_by=self.user
        )
        skill2 = Skill.objects.create(
            name='技能2',
            category='テスト',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        skills = list(Skill.objects.all())
        self.assertEqual(skills[0], skill2)  # display_order=1が先
        self.assertEqual(skills[1], skill1)  # display_order=2が後

    def test_skill_required_level_display(self):
        """必要レベル表示名のテスト"""
        skill = Skill.objects.create(
            name='テスト技能',
            category='テスト',
            required_level='advanced',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(skill.required_level_display_name, '上級')


class SkillFormTest(TestCase):
    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'name': 'Python',
            'category': 'プログラミング言語',
            'description': 'Pythonプログラミングスキル',
            'required_level': 'intermediate',
            'is_active': True,
            'display_order': 1
        }
        form = SkillForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = SkillForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_required_level_choices(self):
        """必要レベル選択肢のテスト"""
        form_data = {
            'name': 'テスト技能',
            'category': 'テスト',
            'required_level': 'invalid_level',  # 無効なレベル
            'is_active': True,
            'display_order': 1
        }
        form = SkillForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('required_level', form.errors)


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
        
        self.skill = Skill.objects.create(
            name='テスト技能',
            category='テストカテゴリ',
            description='テスト技能の説明',
            required_level='intermediate',
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

    def test_skill_create_post(self):
        """技能作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '新しい技能',
            'category': '新カテゴリ',
            'description': '新しい技能の説明',
            'required_level': 'advanced',
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:skill_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            Skill.objects.filter(name='新しい技能').exists()
        )

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
            'category': '更新カテゴリ',
            'description': '更新された説明',
            'required_level': 'expert',
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
        self.assertEqual(self.skill.required_level, 'expert')

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

    def test_skill_category_filter(self):
        """技能カテゴリフィルタのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:skill_list'),
            {'category': 'テストカテゴリ'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

    def test_skill_level_filter(self):
        """技能レベルフィルタのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:skill_list'),
            {'required_level': 'intermediate'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')