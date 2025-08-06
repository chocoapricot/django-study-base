from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import Qualification
from apps.master.forms import QualificationForm

User = get_user_model()


class QualificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_qualification_creation(self):
        """Qualificationモデルの作成テスト"""
        qualification = Qualification.objects.create(
            name='基本情報技術者試験',
            category='national',
            issuing_organization='IPA',
            validity_period=None,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(qualification.name, '基本情報技術者試験')
        self.assertEqual(qualification.category, 'national')
        self.assertEqual(qualification.issuing_organization, 'IPA')
        self.assertIsNone(qualification.validity_period)
        self.assertTrue(qualification.is_active)
        self.assertEqual(str(qualification), '基本情報技術者試験')

    def test_qualification_ordering(self):
        """Qualificationの表示順テスト"""
        qual1 = Qualification.objects.create(
            name='資格1',
            category='national',
            display_order=2,
            created_by=self.user,
            updated_by=self.user
        )
        qual2 = Qualification.objects.create(
            name='資格2',
            category='national',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        qualifications = list(Qualification.objects.all())
        self.assertEqual(qualifications[0], qual2)  # display_order=1が先
        self.assertEqual(qualifications[1], qual1)  # display_order=2が後

    def test_qualification_category_display(self):
        """カテゴリ表示名のテスト"""
        qualification = Qualification.objects.create(
            name='テスト資格',
            category='national',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(qualification.category_display_name, '国家資格')

    def test_qualification_has_validity_period(self):
        """有効期間の有無判定テスト"""
        # 有効期間あり
        qual_with_period = Qualification.objects.create(
            name='有効期間あり資格',
            category='private',
            validity_period=3,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(qual_with_period.has_validity_period)
        
        # 有効期間なし
        qual_without_period = Qualification.objects.create(
            name='有効期間なし資格',
            category='national',
            validity_period=None,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertFalse(qual_without_period.has_validity_period)


class QualificationFormTest(TestCase):
    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'name': 'テスト資格',
            'category': 'national',
            'issuing_organization': 'テスト機関',
            'validity_period': 3,
            'is_active': True,
            'display_order': 1
        }
        form = QualificationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = QualificationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_validity_period_validation(self):
        """有効期間のバリデーションテスト"""
        form_data = {
            'name': 'テスト資格',
            'category': 'private',
            'validity_period': 0,  # 0年は有効
            'is_active': True,
            'display_order': 1
        }
        form = QualificationForm(data=form_data)
        self.assertTrue(form.is_valid())  # 0年は有効とする


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
        
        self.qualification = Qualification.objects.create(
            name='テスト資格',
            category='national',
            issuing_organization='テスト機関',
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

    def test_qualification_create_post(self):
        """資格作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '新しい資格',
            'category': 'private',
            'issuing_organization': '新機関',
            'validity_period': 2,
            'is_active': True,
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('master:qualification_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            Qualification.objects.filter(name='新しい資格').exists()
        )

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
            'category': 'private',
            'issuing_organization': '更新機関',
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

    def test_qualification_category_filter(self):
        """資格カテゴリフィルタのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('master:qualification_list'),
            {'category': 'national'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')