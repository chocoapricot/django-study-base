from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from apps.staff.models import Staff, StaffQualification
from apps.master.models import Qualification
from apps.staff.forms_qualification import StaffQualificationForm

User = get_user_model()


class StaffQualificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date='1990-01-01',
            sex=1,
            regist_form_code=20,
            created_by=self.user,
            updated_by=self.user
        )
        self.qualification = Qualification.objects.create(
            name='基本情報技術者試験',
            category='national',
            validity_period=None,
            created_by=self.user,
            updated_by=self.user
        )

    def test_staff_qualification_creation(self):
        """StaffQualificationモデルの作成テスト"""
        staff_qual = StaffQualification.objects.create(
            staff=self.staff,
            qualification=self.qualification,
            acquired_date=date(2024, 1, 15),
            certificate_number='TEST123',
            memo='テスト取得',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(staff_qual.staff, self.staff)
        self.assertEqual(staff_qual.qualification, self.qualification)
        self.assertEqual(staff_qual.acquired_date, date(2024, 1, 15))
        self.assertEqual(staff_qual.certificate_number, 'TEST123')
        self.assertEqual(str(staff_qual), '田中 太郎 - 基本情報技術者試験')

    def test_staff_qualification_unique_constraint(self):
        """スタッフ資格の一意制約テスト"""
        StaffQualification.objects.create(
            staff=self.staff,
            qualification=self.qualification,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 同じスタッフと資格の組み合わせは作成できない
        with self.assertRaises(Exception):
            StaffQualification.objects.create(
                staff=self.staff,
                qualification=self.qualification,
                created_by=self.user,
                updated_by=self.user
            )

    def test_is_expired_property(self):
        """資格期限切れ判定のテスト"""
        # 期限切れの資格
        expired_qual = StaffQualification.objects.create(
            staff=self.staff,
            qualification=self.qualification,
            acquired_date=date(2020, 1, 1),
            expiry_date=date(2023, 12, 31),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(expired_qual.is_expired)
        
        # 有効な資格
        valid_qual = StaffQualification.objects.create(
            staff=self.staff,
            qualification=Qualification.objects.create(
                name='有効資格',
                category='private',
                created_by=self.user,
                updated_by=self.user
            ),
            acquired_date=date(2024, 1, 1),
            expiry_date=date(2025, 12, 31),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertFalse(valid_qual.is_expired)

    def test_is_expiring_soon_property(self):
        """資格期限間近判定のテスト"""
        # 30日以内に期限切れ
        expiring_soon_qual = StaffQualification.objects.create(
            staff=self.staff,
            qualification=self.qualification,
            acquired_date=date(2024, 1, 1),
            expiry_date=date.today() + timedelta(days=15),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(expiring_soon_qual.is_expiring_soon)
        
        # まだ期限に余裕がある
        not_expiring_qual = StaffQualification.objects.create(
            staff=self.staff,
            qualification=Qualification.objects.create(
                name='余裕資格',
                category='private',
                created_by=self.user,
                updated_by=self.user
            ),
            acquired_date=date(2024, 1, 1),
            expiry_date=date.today() + timedelta(days=60),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertFalse(not_expiring_qual.is_expiring_soon)


class StaffQualificationFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.qualification = Qualification.objects.create(
            name='テスト資格',
            category='private',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )

    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'qualification': self.qualification.pk,
            'acquired_date': '2024-01-15',
            'expiry_date': '2027-01-15',
            'certificate_number': 'TEST123',
            'memo': 'テスト取得'
        }
        form = StaffQualificationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = StaffQualificationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('qualification', form.errors)

    def test_active_qualification_queryset(self):
        """アクティブな資格のみ表示されるテスト"""
        # 非アクティブな資格を作成
        inactive_qual = Qualification.objects.create(
            name='非アクティブ資格',
            category='private',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        form = StaffQualificationForm()
        qualification_choices = form.fields['qualification'].queryset
        
        self.assertIn(self.qualification, qualification_choices)
        self.assertNotIn(inactive_qual, qualification_choices)


class StaffQualificationViewTest(TestCase):
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
                'add_staffqualification', 'view_staffqualification', 
                'change_staffqualification', 'delete_staffqualification',
                'view_staff'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            birth_date='1990-01-01',
            sex=1,
            regist_form_code=20,
            created_by=self.user,
            updated_by=self.user
        )
        self.qualification = Qualification.objects.create(
            name='テスト資格',
            category='private',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        self.staff_qualification = StaffQualification.objects.create(
            staff=self.staff,
            qualification=self.qualification,
            acquired_date=date(2024, 1, 15),
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()

    def test_staff_qualification_list_view(self):
        """スタッフ資格一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_qualification_list', kwargs={'staff_pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')

    def test_staff_qualification_create_view(self):
        """スタッフ資格作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_qualification_create', kwargs={'staff_pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_qualification_create_post(self):
        """スタッフ資格作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        new_qualification = Qualification.objects.create(
            name='新しい資格',
            category='private',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        form_data = {
            'qualification': new_qualification.pk,
            'acquired_date': '2024-02-01',
            'certificate_number': 'NEW123'
        }
        
        response = self.test_client.post(
            reverse('staff:staff_qualification_create', kwargs={'staff_pk': self.staff.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            StaffQualification.objects.filter(
                staff=self.staff,
                qualification=new_qualification
            ).exists()
        )

    def test_staff_qualification_detail_view(self):
        """スタッフ資格詳細ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_qualification_detail', kwargs={'pk': self.staff_qualification.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト資格')

    def test_staff_qualification_update_view(self):
        """スタッフ資格更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_qualification_update', kwargs={'pk': self.staff_qualification.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_qualification_delete_view(self):
        """スタッフ資格削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('staff:staff_qualification_delete', kwargs={'pk': self.staff_qualification.pk})
        )
        self.assertEqual(response.status_code, 200)