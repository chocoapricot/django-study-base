from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.master.models import Bank, BankBranch
from apps.master.forms import BankBranchForm

User = get_user_model()


class BankBranchModelTest(TestCase):
    """銀行支店モデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.bank = Bank.objects.create(
            name='テスト銀行',
            bank_code='1234',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_str_method(self):
        """__str__メソッドのテスト"""
        # 支店コードありの場合
        branch_with_code = BankBranch.objects.create(
            bank=self.bank,
            name='本店',
            branch_code='001',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(branch_with_code), 'テスト銀行 本店（001）')
        
        # 支店コードなしの場合
        branch_without_code = BankBranch.objects.create(
            bank=self.bank,
            name='支店',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(branch_without_code), 'テスト銀行 支店')
    
    def test_full_name(self):
        """完全な支店名のテスト"""
        # 支店コードありの場合
        branch_with_code = BankBranch.objects.create(
            bank=self.bank,
            name='本店',
            branch_code='001',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(branch_with_code.full_name, 'テスト銀行 本店（001）')
        
        # 支店コードなしの場合
        branch_without_code = BankBranch.objects.create(
            bank=self.bank,
            name='支店',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(branch_without_code.full_name, 'テスト銀行 支店')
    
    def test_validation_branch_code(self):
        """支店コードバリデーションのテスト"""
        branch = BankBranch(
            bank=self.bank,
            name='本店',
            branch_code='abc',  # 数字以外を含む
            created_by=self.user,
            updated_by=self.user
        )
        with self.assertRaises(ValidationError):
            branch.clean()
        
        branch.branch_code = '1234'  # 4桁
        with self.assertRaises(ValidationError):
            branch.clean()
        
        branch.branch_code = '12'  # 2桁
        with self.assertRaises(ValidationError):
            branch.clean()
        
        branch.branch_code = '123'  # 正常な3桁
        branch.clean()  # エラーが発生しないことを確認
    
    def test_get_active_list(self):
        """有効な銀行支店一覧取得のテスト"""
        # 有効な支店
        active_branch = BankBranch.objects.create(
            bank=self.bank,
            name='有効支店',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 無効な支店
        inactive_branch = BankBranch.objects.create(
            bank=self.bank,
            name='無効支店',
            branch_code='002',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        active_list = BankBranch.get_active_list()
        self.assertIn(active_branch, active_list)
        self.assertNotIn(inactive_branch, active_list)
    
    def test_usage_count(self):
        """利用件数のテスト"""
        branch = BankBranch.objects.create(
            bank=self.bank,
            name='テスト支店',
            created_by=self.user,
            updated_by=self.user
        )
        # 現在は他のモデルで参照されていないため0
        self.assertEqual(branch.usage_count, 0)


class BankBranchFormTest(TestCase):
    """銀行支店フォームのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.bank = Bank.objects.create(
            name='テスト銀行',
            bank_code='1234',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_valid_form(self):
        """有効なフォームのテスト"""
        form_data = {
            'bank': self.bank.pk,
            'name': 'テスト支店',
            'branch_code': '001',
            'is_active': True
        }
        form = BankBranchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_bank(self):
        """銀行が未選択の場合のテスト"""
        form_data = {
            'name': 'テスト支店',
            'branch_code': '001',
            'is_active': True
        }
        form = BankBranchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('bank', form.errors)
    
    def test_invalid_form_missing_name(self):
        """支店名が未入力の場合のテスト"""
        form_data = {
            'bank': self.bank.pk,
            'branch_code': '001',
            'is_active': True
        }
        form = BankBranchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class BankBranchViewTest(TestCase):
    """銀行支店ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            codename__in=['view_bank', 'view_bankbranch', 'add_bankbranch', 'change_bankbranch', 'delete_bankbranch']
        )
        self.user.user_permissions.set(permissions)
        
        self.client.login(username='testuser', password='testpass123')
        
        self.bank = Bank.objects.create(
            name='テスト銀行',
            bank_code='1234',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.bank_branch = BankBranch.objects.create(
            bank=self.bank,
            name='テスト支店',
            branch_code='001',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_bank_management_view_with_branch(self):
        """銀行統合管理ビューで支店表示のテスト"""
        response = self.client.get(reverse('master:bank_management') + f'?bank_id={self.bank.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト支店')
    

    
    def test_bank_branch_create_view_get(self):
        """銀行支店作成ビュー（GET）のテスト"""
        response = self.client.get(reverse('master:bank_branch_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行支店作成')
    
    def test_bank_branch_create_view_post(self):
        """銀行支店作成ビュー（POST）のテスト"""
        form_data = {
            'bank': self.bank.pk,
            'name': '新規支店',
            'branch_code': '002',
            'is_active': True
        }
        response = self.client.post(reverse('master:bank_branch_create'), data=form_data)
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(BankBranch.objects.filter(name='新規支店').exists())
    
    def test_bank_branch_update_view(self):
        """銀行支店更新ビューのテスト"""
        form_data = {
            'bank': self.bank.pk,
            'name': '更新された支店',
            'branch_code': '001',
            'is_active': True
        }
        response = self.client.post(
            reverse('master:bank_branch_update', kwargs={'pk': self.bank_branch.pk}),
            data=form_data
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # データベースから再取得して確認
        updated_branch = BankBranch.objects.get(pk=self.bank_branch.pk)
        self.assertEqual(updated_branch.name, '更新された支店')
    
    def test_bank_branch_delete_view(self):
        """銀行支店削除ビューのテスト"""
        response = self.client.post(reverse('master:bank_branch_delete', kwargs={'pk': self.bank_branch.pk}))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertFalse(BankBranch.objects.filter(pk=self.bank_branch.pk).exists())