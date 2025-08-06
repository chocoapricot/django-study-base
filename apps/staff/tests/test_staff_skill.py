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
            regist_form_code=20,
            created_by=self.user,
            updated_by=self.user
        )
        self.skill = Skill.objects.create(
            name='Java',
            category='プログラミング言語',
            required_level='intermediate',
            created_by=self.user,
            updated_by=self.user
        )

    def test_staff_skill_creation(self):
        """StaffSkillモデルの作成テスト"""
        staff_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            level='advanced',
            acquired_date=date(2024, 1, 15),
            years_of_experience=3,
            memo='実務経験3年',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(staff_skill.staff, self.staff)
        self.assertEqual(staff_skill.skill, self.skill)
        self.assertEqual(staff_skill.level, 'advanced')
        self.assertEqual(staff_skill.acquired_date, date(2024, 1, 15))
        self.assertEqual(staff_skill.years_of_experience, 3)
        self.assertEqual(str(staff_skill), '田中 太郎 - Java (上級)')

    def test_staff_skill_unique_constraint(self):
        """スタッフ技能の一意制約テスト"""
        StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            level='intermediate',
            created_by=self.user,
            updated_by=self.user
        )
        
        # 同じスタッフと技能の組み合わせは作成できない
        with self.assertRaises(Exception):
            StaffSkill.objects.create(
                staff=self.staff,
                skill=self.skill,
                level='advanced',
                created_by=self.user,
                updated_by=self.user
            )

    def test_level_display_name_property(self):
        """レベル表示名のテスト"""
        staff_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            level='expert',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(staff_skill.level_display_name, 'エキスパート')

    def test_meets_required_level_property(self):
        """必要レベル達成判定のテスト"""
        # 必要レベルを満たしている場合
        advanced_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,  # required_level='intermediate'
            level='advanced',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(advanced_skill.meets_required_level)
        
        # 必要レベルを満たしていない場合
        beginner_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=Skill.objects.create(
                name='Python',
                category='プログラミング言語',
                required_level='advanced',
                created_by=self.user,
                updated_by=self.user
            ),
            level='beginner',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertFalse(beginner_skill.meets_required_level)


class StaffSkillFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.skill = Skill.objects.create(
            name='テスト技能',
            category='テスト',
            required_level='intermediate',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )

    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'skill': self.skill.pk,
            'level': 'advanced',
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
            category='テスト',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        form = StaffSkillForm()
        skill_choices = form.fields['skill'].queryset
        
        self.assertIn(self.skill, skill_choices)
        self.assertNotIn(inactive_skill, skill_choices)


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
            regist_form_code=20,
            created_by=self.user,
            updated_by=self.user
        )
        self.skill = Skill.objects.create(
            name='テスト技能',
            category='テスト',
            required_level='intermediate',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        self.staff_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            level='advanced',
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
            category='テスト',
            required_level='beginner',
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

    def test_staff_skill_detail_view(self):
        """スタッフ技能詳細ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_skill_detail', kwargs={'pk': self.staff_skill.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト技能')

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