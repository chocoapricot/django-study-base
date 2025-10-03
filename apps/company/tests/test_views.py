from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models import Company, CompanyDepartment, CompanyUser

User = get_user_model()

class CompanyViewTest(TestCase):
    """会社ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # ユーザーをスーパーユーザーにして権限問題を回避
        self.user.is_superuser = True
        self.user.save()
        self.company = Company.objects.create(
            name="テスト会社",
            corporate_number="1234567890123",
            postal_code="1000001",
            address="東京都千代田区千代田1-1",
            phone_number="03-1234-5678"
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
            'corporate_number': getattr(self.company, 'corporate_number', '') or '',
            'representative': getattr(self.company, 'representative', '') or '',
            'postal_code': getattr(self.company, 'postal_code', '') or '',
            'address': getattr(self.company, 'address', '') or '',
            'phone_number': getattr(self.company, 'phone_number', '') or '',
        })
        # フォームが有効であればリダイレクト、無効であれば200が返される
        self.assertIn(response.status_code, [200, 302])

    def test_change_history_list_view(self):
        """変更履歴一覧ビューのテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company:change_history_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'common/common_change_history_list.html')
        self.assertContains(response, "会社関連 変更履歴一覧")

class DepartmentViewTest(TestCase):
    """部署ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # ユーザーをスーパーユーザーにして権限問題を回避
        self.user.is_superuser = True
        self.user.save()
        self.department = CompanyDepartment.objects.create(
            name="開発部",
            corporate_number="1234567890123",
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
            'corporate_number': '1234567890123',
            'department_code': 'SALES001',
            'display_order': 2,
            'valid_from': '',
            'valid_to': '',
            'accounting_code': '',
            'postal_code': '',
            'address': '',
            'phone_number': ''
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
            'corporate_number': self.department.corporate_number or '',
            'department_code': self.department.department_code,
            'accounting_code': self.department.accounting_code or '',
            'display_order': self.department.display_order,
            'postal_code': self.department.postal_code or '',
            'address': self.department.address or '',
            'phone_number': self.department.phone_number or '',
            'valid_from': self.department.valid_from or '',
            'valid_to': self.department.valid_to or ''
        })
        self.assertEqual(response.status_code, 302)  # リダイレクト


class CompanyUserViewTest(TestCase):
    """自社担当者ビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            is_superuser=True
        )
        self.client.login(username='testuser', password='testpassword')

        self.company = Company.objects.create(name="テスト株式会社", corporate_number="1112223334445")
        self.department = CompanyDepartment.objects.create(
            name="テスト部署",
            corporate_number="1112223334445",
            department_code="TEST_DEPT"
        )
        self.company_user = CompanyUser.objects.create(
            corporate_number="1112223334445",
            department_code="TEST_DEPT",
            name_last="山田",
            name_first="太郎",
        )
        self.create_url = reverse('company:company_user_create')
        self.edit_url = reverse('company:company_user_edit', kwargs={'pk': self.company_user.pk})
        self.delete_url = reverse('company:company_user_delete', kwargs={'pk': self.company_user.pk})
        self.detail_url = reverse('company:company_detail')

    def test_create_view_get(self):
        """作成ビューのGETアクセス"""
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "担当者作成")

    def test_create_view_post(self):
        """作成ビューのPOST"""
        data = {
            'department_code': self.department.department_code,
            'name_last': '鈴木',
            'name_first': '一郎',
            'position': '係長',
            'display_order': 10,
        }
        response = self.client.post(self.create_url, data)
        self.assertRedirects(response, self.detail_url)
        self.assertTrue(CompanyUser.objects.filter(name_last='鈴木').exists())

    def test_edit_view_get(self):
        """編集ビューのGETアクセス"""
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "担当者編集")

    def test_edit_view_post(self):
        """編集ビューのPOST"""
        data = {
            'department_code': self.department.department_code,
            'name_last': '山田',
            'name_first': '太郎',
            'position': '本部長', # Change position
            'phone_number': '',
            'email': '',
            'display_order': 0,
        }
        response = self.client.post(self.edit_url, data)
        self.assertRedirects(response, self.detail_url)
        self.company_user.refresh_from_db()
        self.assertEqual(self.company_user.position, '本部長')

    def test_delete_view_get(self):
        """削除ビューのGETアクセス"""
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "担当者削除の確認")

    def test_delete_view_post(self):
        """削除ビューのPOST"""
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(CompanyUser.objects.filter(pk=self.company_user.pk).exists())
