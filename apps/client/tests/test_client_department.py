from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.client.models import Client, ClientDepartment
from apps.client.forms import ClientDepartmentForm

User = get_user_model()


class ClientDepartmentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client_obj = Client.objects.create(
            name='テスト会社',
            name_furigana='テストガイシャ',
            regist_form_client=10
        )

    def test_client_department_creation(self):
        """ClientDepartmentモデルの作成テスト"""
        department = ClientDepartment.objects.create(
            client=self.client_obj,
            name='営業部',
            department_code='SALES',
            postal_code='1000001',
            address='東京都千代田区千代田1-1',
            phone_number='03-1234-5678',
            email='sales@test.com',
            display_order=1
        )
        
        self.assertEqual(department.client, self.client_obj)
        self.assertEqual(department.name, '営業部')
        self.assertEqual(department.department_code, 'SALES')
        self.assertEqual(str(department), 'テスト会社 - 営業部')

    def test_client_department_ordering(self):
        """ClientDepartmentの表示順テスト"""
        dept1 = ClientDepartment.objects.create(
            client=self.client_obj,
            name='営業部',
            display_order=2
        )
        dept2 = ClientDepartment.objects.create(
            client=self.client_obj,
            name='総務部',
            display_order=1
        )
        
        departments = list(ClientDepartment.objects.all())
        self.assertEqual(departments[0], dept2)  # display_order=1が先
        self.assertEqual(departments[1], dept1)  # display_order=2が後


class ClientDepartmentFormTest(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name='テスト会社',
            name_furigana='テストガイシャ',
            regist_form_client=10
        )

    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'name': '営業部',
            'department_code': 'SALES',
            'postal_code': '1000001',
            'address': '東京都千代田区千代田1-1',
            'phone_number': '03-1234-5678',
            'email': 'sales@test.com',
            'display_order': 1,
            'valid_from': '2024-01-01',
            'valid_to': '2024-12-31'
        }
        form = ClientDepartmentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = ClientDepartmentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_email_validation(self):
        """メールアドレスのバリデーションテスト"""
        form_data = {
            'name': '営業部',
            'email': 'invalid-email'
        }
        form = ClientDepartmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_valid_period_validation(self):
        """有効期間のバリデーションテスト"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='testuser', password='testpass')
        
        # 正常な期間
        department = ClientDepartment(
            client=self.client_obj,
            name='営業部',
            valid_from='2024-01-01',
            valid_to='2024-12-31',
            created_by=user,
            updated_by=user
        )
        department.full_clean()  # バリデーション実行
        
        # 異常な期間（開始日 > 終了日）
        department_invalid = ClientDepartment(
            client=self.client_obj,
            name='営業部',
            valid_from='2024-12-31',
            valid_to='2024-01-01',
            created_by=user,
            updated_by=user
        )
        with self.assertRaises(ValidationError):
            department_invalid.full_clean()


class ClientDepartmentViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='client',
            codename__in=[
                'add_clientdepartment', 'view_clientdepartment', 
                'change_clientdepartment', 'delete_clientdepartment'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.client_obj = Client.objects.create(
            name='テスト会社',
            name_furigana='テストガイシャ',
            regist_form_client=10
        )
        self.department = ClientDepartment.objects.create(
            client=self.client_obj,
            name='営業部',
            department_code='SALES'
        )
        self.test_client = TestClient()

    def test_client_department_create_view(self):
        """組織作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_department_create', kwargs={'client_pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_client_department_list_view(self):
        """組織一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_department_list', kwargs={'client_pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '営業部')

    def test_client_department_update_view(self):
        """組織更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_department_update', kwargs={'pk': self.department.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_client_department_delete_view(self):
        """組織削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_department_delete', kwargs={'pk': self.department.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_client_department_create_post(self):
        """組織作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '開発部',
            'department_code': 'DEV',
            'display_order': 1,
            'valid_from': '2024-01-01'
        }
        
        response = self.test_client.post(
            reverse('client:client_department_create', kwargs={'client_pk': self.client_obj.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            ClientDepartment.objects.filter(
                client=self.client_obj,
                name='開発部'
            ).exists()
        )