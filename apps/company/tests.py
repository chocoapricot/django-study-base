from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Company, CompanyDepartment

User = get_user_model()

class CompanyModelTest(TestCase):
    """会社モデルのテスト"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="テスト会社",
            corporate_number="1234567890123",
            postal_code="1000001",
            address="東京都千代田区千代田1-1",
            phone_number="03-1234-5678",
            url="https://example.com"
        )
    
    def test_company_creation(self):
        """会社の作成テスト"""
        self.assertEqual(self.company.name, "テスト会社")
        self.assertEqual(self.company.corporate_number, "1234567890123")
        self.assertEqual(str(self.company), "テスト会社")
    
    def test_company_unique_name(self):
        """会社名の一意性テスト"""
        with self.assertRaises(Exception):
            Company.objects.create(name="テスト会社")

class CompanyDepartmentModelTest(TestCase):
    """部署モデルのテスト"""
    
    def setUp(self):
        self.department = CompanyDepartment.objects.create(
            name="開発部",
            department_code="DEV001",
            accounting_code="ACC001",
            display_order=1
        )
    
    def test_department_creation(self):
        """部署の作成テスト"""
        self.assertEqual(self.department.name, "開発部")
        self.assertEqual(self.department.department_code, "DEV001")
        self.assertEqual(self.department.accounting_code, "ACC001")
        self.assertEqual(self.department.display_order, 1)
        self.assertEqual(str(self.department), "開発部")
    
    def test_department_unique_name(self):
        """部署名の一意性テスト"""
        with self.assertRaises(Exception):
            CompanyDepartment.objects.create(name="開発部", department_code="DEV002")
    
    def test_department_unique_code(self):
        """部署コードの一意性テスト"""
        with self.assertRaises(Exception):
            CompanyDepartment.objects.create(name="営業部", department_code="DEV001")

class CompanyViewTest(TestCase):
    """会社ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name="テスト会社",
            corporate_number="1234567890123"
        )
    
    def test_company_detail_view_requires_login(self):
        """会社詳細ビューのログイン必須テスト"""
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
    
    def test_company_detail_view_with_login(self):
        """ログイン後の会社詳細ビューテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "テスト会社")
    
    def test_company_edit_view_with_login(self):
        """ログイン後の会社編集ビューテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company:company_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "会社情報編集")
    
    def test_company_edit_no_changes(self):
        """会社編集で変更がない場合のテスト"""
        self.client.login(username='testuser', password='testpass123')
        # 既存のデータと同じ内容でPOST
        response = self.client.post(reverse('company:company_edit'), {
            'name': self.company.name,
            'corporate_number': self.company.corporate_number or '',
            'postal_code': '',
            'address': '',
            'phone_number': '',
            'url': ''
        })
        self.assertEqual(response.status_code, 302)  # リダイレクト

class DepartmentViewTest(TestCase):
    """部署ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.department = CompanyDepartment.objects.create(
            name="開発部",
            department_code="DEV001",
            display_order=1
        )
    

    
    def test_department_detail_view_with_login(self):
        """ログイン後の部署詳細ビューテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company:department_detail', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "開発部")
    
    def test_department_create_view_with_login(self):
        """ログイン後の部署作成ビューテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company:department_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "部署作成")
    
    def test_department_create_post(self):
        """部署作成のPOSTテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('company:department_create'), {
            'name': '営業部',
            'department_code': 'SALES001',
            'display_order': 2
        })
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(CompanyDepartment.objects.filter(name='営業部').exists())
    
    def test_department_edit_view_with_login(self):
        """ログイン後の部署編集ビューテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company:department_edit', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "部署編集")
    
    def test_department_delete_view_with_login(self):
        """ログイン後の部署削除確認ビューテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company:department_delete', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "部署削除確認")
    
    def test_department_delete_post(self):
        """部署削除のPOSTテスト"""
        self.client.login(username='testuser', password='testpass123')
        department_id = self.department.pk
        response = self.client.post(reverse('company:department_delete', kwargs={'pk': department_id}))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertFalse(CompanyDepartment.objects.filter(pk=department_id).exists())
    

    
    def test_department_edit_no_changes(self):
        """部署編集で変更がない場合のテスト"""
        self.client.login(username='testuser', password='testpass123')
        # 既存のデータと同じ内容でPOST
        response = self.client.post(reverse('company:department_edit', kwargs={'pk': self.department.pk}), {
            'name': self.department.name,
            'department_code': self.department.department_code,
            'accounting_code': self.department.accounting_code or '',
            'display_order': self.department.display_order,
            'postal_code': self.department.postal_code or '',
            'address': self.department.address or '',
            'phone_number': self.department.phone_number or ''
        })
        self.assertEqual(response.status_code, 302)  # リダイレクト
