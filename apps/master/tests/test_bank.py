from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.master.models import Bank
from apps.master.forms import BankForm

User = get_user_model()


class BankModelTest(TestCase):
    """銀行モデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_str_method(self):
        """__str__メソッドのテスト"""
        # 銀行コードありの場合
        bank_with_code = Bank.objects.create(
            name='テスト銀行',
            bank_code='1234',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(bank_with_code), 'テスト銀行（1234）')
        
        # 銀行コードありの場合（別パターン）
        bank_without_code = Bank.objects.create(
            name='サンプル銀行',
            bank_code='5678',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(bank_without_code), 'サンプル銀行（5678）')
    
    def test_full_name(self):
        """完全な銀行名のテスト"""
        # 銀行コードありの場合
        bank_with_code = Bank.objects.create(
            name='テスト銀行',
            bank_code='1234',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(bank_with_code.full_name, 'テスト銀行（1234）')
        
        # 銀行コードありの場合（別パターン）
        bank_without_code = Bank.objects.create(
            name='サンプル銀行',
            bank_code='9999',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(bank_without_code.full_name, 'サンプル銀行（9999）')
    
    def test_validation_bank_code(self):
        """銀行コードバリデーションのテスト"""
        bank = Bank(
            name='テスト銀行',
            bank_code='abc1',  # 数字以外を含む
            created_by=self.user,
            updated_by=self.user
        )
        with self.assertRaises(ValidationError):
            bank.clean()
        
        bank.bank_code = '12345'  # 5桁
        with self.assertRaises(ValidationError):
            bank.clean()
        
        bank.bank_code = '123'  # 3桁
        with self.assertRaises(ValidationError):
            bank.clean()
        
        bank.bank_code = '1234'  # 正常な4桁
        bank.clean()  # エラーが発生しないことを確認
    
    def test_get_active_list(self):
        """有効な銀行一覧取得のテスト"""
        # 有効な銀行
        active_bank = Bank.objects.create(
            name='有効銀行',
            bank_code='0098',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 無効な銀行
        inactive_bank = Bank.objects.create(
            name='無効銀行',
            bank_code='0097',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        active_list = Bank.get_active_list()
        self.assertIn(active_bank, active_list)
        self.assertNotIn(inactive_bank, active_list)
    
    def test_usage_count(self):
        """利用件数のテスト"""
        bank = Bank.objects.create(
            name='テスト銀行',
            bank_code='0096',
            created_by=self.user,
            updated_by=self.user
        )
        # 現在は他のモデルで参照されていないため0
        self.assertEqual(bank.usage_count, 0)
    
class BankFormTest(TestCase):
    """銀行フォームのテスト"""
    
    def test_valid_form(self):
        """有効なフォームのテスト"""
        form_data = {
            'name': 'テスト銀行',
            'bank_code': '1234',
            'is_active': True
        }
        form = BankForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_name(self):
        """銀行名が未入力の場合のテスト"""
        form_data = {
            'bank_code': '1234',
            'is_active': True
        }
        form = BankForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class BankViewTest(TestCase):
    """銀行ビューのテスト"""
    
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
            codename__in=['view_bank', 'add_bank', 'change_bank', 'delete_bank', 'view_bankbranch']
        )
        self.user.user_permissions.set(permissions)
        
        self.client.login(username='testuser', password='testpass123')
        
        self.bank = Bank.objects.create(
            name='テスト銀行',
            bank_code='1234',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_bank_management_view(self):
        """銀行統合管理ビューのテスト"""
        response = self.client.get(reverse('master:bank_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト銀行')
    

    
    def test_bank_create_view_get(self):
        """銀行作成ビュー（GET）のテスト"""
        response = self.client.get(reverse('master:bank_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行作成')
    
    def test_bank_create_view_post(self):
        """銀行作成ビュー（POST）のテスト"""
        form_data = {
            'name': '新規銀行',
            'bank_code': '5678',
            'is_active': True
        }
        response = self.client.post(reverse('master:bank_create'), data=form_data)
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(Bank.objects.filter(name='新規銀行').exists())
    
    def test_bank_update_view(self):
        """銀行更新ビューのテスト"""
        form_data = {
            'name': '更新された銀行',
            'bank_code': '1234',
            'is_active': True
        }
        response = self.client.post(
            reverse('master:bank_update', kwargs={'pk': self.bank.pk}),
            data=form_data
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # データベースから再取得して確認
        updated_bank = Bank.objects.get(pk=self.bank.pk)
        self.assertEqual(updated_bank.name, '更新された銀行')
    
    def test_bank_delete_view(self):
        """銀行削除ビューのテスト"""
        response = self.client.post(reverse('master:bank_delete', kwargs={'pk': self.bank.pk}))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertFalse(Bank.objects.filter(pk=self.bank.pk).exists())