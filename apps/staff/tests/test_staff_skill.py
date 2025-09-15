from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date
from apps.staff.models import Staff, StaffSkill
from apps.master.models import Skill
from apps.staff.forms_qualification import StaffSkillForm

User = get_user_model()


class StaffSkillModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date=date(1990, 1, 1),
            sex=1,
            regist_status_code=20,
            created_by=self.user,
            updated_by=self.user
        )
        self.category = Skill.objects.create(
            name='プログラミング言語',
            level=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.skill = Skill.objects.create(
            name='Java',
            level=2,
            parent=self.category,
            created_by=self.user,
            updated_by=self.user
        )

    def test_staff_skill_creation(self):
        """StaffSkillモデルの作成テスト"""
        staff_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            acquired_date=date(2024, 1, 15),
            years_of_experience=3,
            memo='実務経験3年',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(staff_skill.staff, self.staff)
        self.assertEqual(staff_skill.skill, self.skill)
        self.assertEqual(staff_skill.acquired_date, date(2024, 1, 15))
        self.assertEqual(staff_skill.years_of_experience, 3)
        self.assertEqual(str(staff_skill), '田中 太郎 - プログラミング言語 > Java')

    def test_staff_skill_unique_constraint(self):
        """スタッフ技能の一意制約テスト"""
        StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 同じスタッフと技能の組み合わせは作成できない
        with self.assertRaises(Exception):
            StaffSkill.objects.create(
                staff=self.staff,
                skill=self.skill,
                created_by=self.user,
                updated_by=self.user
            )

    def test_staff_skill_str_method(self):
        """文字列表現のテスト"""
        staff_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            created_by=self.user,
            updated_by=self.user
        )
        
        expected_str = f"{self.staff} - {self.skill}"
        self.assertEqual(str(staff_skill), expected_str)

    


class StaffSkillFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date=date(1990, 1, 1),
            sex=1,
            regist_status_code=20,
            created_by=self.user,
            updated_by=self.user
        )
        self.category = Skill.objects.create(
            name='テストカテゴリ',
            level=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.skill = Skill.objects.create(
            name='テスト技能',
            level=2,
            parent=self.category,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )

    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'skill': self.skill.pk,
            'acquired_date': '2024-01-15',
            'years_of_experience': 2,
            'memo': 'テスト習得'
        }
        form = StaffSkillForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = StaffSkillForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('skill', form.errors)

    def test_active_skill_queryset(self):
        """アクティブな技能のみ表示されるテスト"""
        # 非アクティブな技能を作成
        inactive_skill = Skill.objects.create(
            name='非アクティブ技能',
            level=2,
            parent=self.category,
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        form = StaffSkillForm()
        skill_choices = form.fields['skill'].queryset
        
        self.assertIn(self.skill, skill_choices)
        self.assertNotIn(inactive_skill, skill_choices)

    def test_duplicate_skill_validation(self):
        """重複技能のバリデーションテスト"""
        # 既存の技能を作成
        existing_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            acquired_date=date(2024, 1, 15),
            created_by=self.user,
            updated_by=self.user
        )
        
        # 同じ技能を再度登録しようとする
        form_data = {
            'skill': self.skill.pk,
            'acquired_date': '2024-02-01',
        }
        form = StaffSkillForm(data=form_data, staff=self.staff)
        self.assertFalse(form.is_valid())
        self.assertIn('skill', form.errors)
        self.assertIn('既に登録されています', str(form.errors['skill']))

    def test_duplicate_skill_validation_edit_mode(self):
        """編集時の重複技能バリデーションテスト（自分自身は除外）"""
        # 既存の技能を作成
        existing_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            acquired_date=date(2024, 1, 15),
            created_by=self.user,
            updated_by=self.user
        )
        
        # 同じ技能を編集（自分自身なので有効）
        form_data = {
            'skill': self.skill.pk,
            'acquired_date': '2024-02-01',
        }
        form = StaffSkillForm(
            data=form_data, 
            staff=self.staff, 
            instance=existing_skill
        )
        self.assertTrue(form.is_valid())


class StaffSkillViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='staff',
            codename__in=[
                'add_staffskill', 'view_staffskill', 
                'change_staffskill', 'delete_staffskill',
                'view_staff'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date=date(1990, 1, 1),
            sex=1,
            regist_status_code=20,
            created_by=self.user,
            updated_by=self.user
        )
        self.category = Skill.objects.create(
            name='テストカテゴリ',
            level=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.skill = Skill.objects.create(
            name='テスト技能',
            level=2,
            parent=self.category,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        self.staff_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            acquired_date=date(2024, 1, 15),
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()

    def test_staff_skill_list_view(self):
        """スタッフ技能一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_skill_list', kwargs={'staff_pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

    def test_staff_skill_create_view(self):
        """スタッフ技能作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_skill_create', kwargs={'staff_pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_skill_create_post(self):
        """スタッフ技能作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        new_skill = Skill.objects.create(
            name='新しい技能',
            level=2,
            parent=self.category,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        form_data = {
            'skill': new_skill.pk,
            'level': 'intermediate',
            'acquired_date': '2024-02-01',
            'years_of_experience': 1
        }
        
        response = self.test_client.post(
            reverse('staff:staff_skill_create', kwargs={'staff_pk': self.staff.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            StaffSkill.objects.filter(
                staff=self.staff,
                skill=new_skill
            ).exists()
        )

    

    def test_staff_skill_update_view(self):
        """スタッフ技能更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_skill_update', kwargs={'pk': self.staff_skill.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_skill_delete_view(self):
        """スタッフ技能削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_skill_delete', kwargs={'pk': self.staff_skill.pk})
        )
        self.assertEqual(response.status_code, 200)