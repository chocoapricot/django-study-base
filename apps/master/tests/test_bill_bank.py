from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.master.models import BillBank
from apps.master.forms import BillBankForm

User = get_user_model()


class BillBankModelTest(TestCase):
    """振込先銀行モデルのテスト"""
    
    def setUp(self):
        self.bill_bank = BillBank.objects.create(
            name='三菱UFJ銀行',
            bank_code='0005',
            branch_name='新宿支店',
            branch_code='001',
            account_type='ordinary',
            account_number='1234567',
            account_holder='株式会社テスト',
            account_holder_kana='カブシキガイシャテスト',
            is_active=True,
            display_order=1
        )
    
    def test_str_method(self):
        """__str__メソッドのテスト"""
        expected = '三菱UFJ銀行 新宿支店 普通 1234567'
        self.assertEqual(str(self.bill_bank), expected)
    
    def test_account_type_display(self):
        """口座種別表示のテスト"""
        self.assertEqual(self.bill_bank.account_type_display, '普通')
        
        # 当座口座の場合
        bill_bank = BillBank.objects.create(
            name='みずほ銀行',
            bank_code='0001',
            branch_name='渋谷支店',
            branch_code='140',
            account_type='current',
            account_number='9876543',
            account_holder='株式会社サンプル'
        )
        self.assertEqual(bill_bank.account_type_display, '当座')
    
    def test_full_bank_info(self):
        """完全な銀行情報のテスト"""
        expected = '三菱UFJ銀行（0005） 新宿支店（001） 普通 1234567'
        self.assertEqual(self.bill_bank.full_bank_info, expected)
        
        # コードがある場合の別パターン
        bill_bank = BillBank.objects.create(
            name='地方銀行',
            bank_code='0097',
            branch_name='本店',
            branch_code='997',
            account_type='ordinary',
            account_number='1111111',
            account_holder='テスト会社'
        )
        expected_with_code = '地方銀行（0097） 本店（997） 普通 1111111'
        self.assertEqual(bill_bank.full_bank_info, expected_with_code)
    
    def test_account_info(self):
        """口座情報のテスト"""
        expected = '普通 1234567 株式会社テスト'
        self.assertEqual(self.bill_bank.account_info, expected)
    
    def test_validation_bank_code(self):
        """銀行コードバリデーションのテスト"""
        # 銀行コードが未入力の場合（必須）
        bill_bank = BillBank(
            name='テスト銀行',
            branch_name='テスト支店',
            branch_code='001',
            account_type='ordinary',
            account_number='1234567',
            account_holder='テスト'
        )
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        # 無効な銀行コード（文字列）
        bill_bank.bank_code = 'abcd'  # 無効な値
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        # 無効な銀行コード（桁数）
        bill_bank.bank_code = '123'  # 3桁
        with self.assertRaises(ValidationError):
            bill_bank.clean()
    
    def test_validation_branch_code(self):
        """支店コードバリデーションのテスト"""
        # 支店コードが未入力の場合（必須）
        bill_bank = BillBank(
            name='テスト銀行',
            bank_code='0001',
            branch_name='テスト支店',
            account_type='ordinary',
            account_number='1234567',
            account_holder='テスト'
        )
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        # 無効な支店コード（文字列）
        bill_bank.branch_code = 'ab'  # 無効な値
        with self.assertRaises(ValidationError):
            bill_bank.clean()
    
    def test_validation_account_number(self):
        """口座番号バリデーションのテスト"""
        # 無効な口座番号（文字列）
        bill_bank = BillBank(
            name='テスト銀行',
            bank_code='0001',
            branch_name='テスト支店',
            branch_code='001',
            account_type='ordinary',
            account_number='abcdefg',  # 無効な値
            account_holder='テスト'
        )
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        # 無効な口座番号（桁数）
        bill_bank.account_number = '123456789'  # 9桁
        with self.assertRaises(ValidationError):
            bill_bank.clean()
    
    def test_get_active_list(self):
        """有効な振込先銀行一覧取得のテスト"""
        # 無効な振込先銀行を作成
        BillBank.objects.create(
            name='無効銀行',
            bank_code='0098',
            branch_name='無効支店',
            branch_code='998',
            account_type='ordinary',
            account_number='9999999',
            account_holder='無効会社',
            is_active=False
        )
        
        active_list = BillBank.get_active_list()
        self.assertEqual(active_list.count(), 1)
        self.assertEqual(active_list.first().name, '三菱UFJ銀行')


class BillBankFormTest(TestCase):
    """振込先銀行フォームのテスト"""
    
    def test_valid_form(self):
        """有効なフォームのテスト"""
        form_data = {
            'name': 'りそな銀行',
            'bank_code': '0010',
            'branch_name': '大阪支店',
            'branch_code': '100',
            'account_type': 'ordinary',
            'account_number': '7777777',
            'account_holder': '株式会社フォームテスト',
            'account_holder_kana': 'カブシキガイシャフォームテスト',
            'is_active': True,
            'display_order': 1
        }
        form = BillBankForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_name(self):
        """銀行名が未入力の場合のテスト"""
        form_data = {
            'branch_name': '大阪支店',
            'account_type': 'ordinary',
            'account_number': '7777777',
            'account_holder': '株式会社フォームテスト',
            'is_active': True,
            'display_order': 1
        }
        form = BillBankForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_invalid_form_missing_account_holder(self):
        """口座名義が未入力の場合のテスト"""
        form_data = {
            'name': 'りそな銀行',
            'bank_code': '0010',
            'branch_name': '大阪支店',
            'branch_code': '100',
            'account_type': 'ordinary',
            'account_number': '7777777',
            'is_active': True,
            'display_order': 1
        }
        form = BillBankForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('account_holder', form.errors)
    
    def test_invalid_form_missing_bank_code(self):
        """銀行コードが未入力の場合のテスト"""
        form_data = {
            'name': 'りそな銀行',
            'branch_name': '大阪支店',
            'branch_code': '100',
            'account_type': 'ordinary',
            'account_number': '7777777',
            'account_holder': '株式会社フォームテスト',
            'is_active': True,
            'display_order': 1
        }
        form = BillBankForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('bank_code', form.errors)
    
    def test_invalid_form_missing_branch_code(self):
        """支店コードが未入力の場合のテスト"""
        form_data = {
            'name': 'りそな銀行',
            'bank_code': '0010',
            'branch_name': '大阪支店',
            'account_type': 'ordinary',
            'account_number': '7777777',
            'account_holder': '株式会社フォームテスト',
            'is_active': True,
            'display_order': 1
        }
        form = BillBankForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('branch_code', form.errors)


class BillBankViewTest(TestCase):
    """振込先銀行ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_superuser=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.bill_bank = BillBank.objects.create(
            name='テスト銀行',
            bank_code='0099',
            branch_name='テスト支店',
            branch_code='999',
            account_type='ordinary',
            account_number='1111111',
            account_holder='テスト会社'
        )
    
    def test_bill_bank_list_view(self):
        """振込先銀行一覧ビューのテスト"""
        response = self.client.get(reverse('master:bill_bank_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト銀行')
    
    def test_bill_bank_create_view_get(self):
        """振込先銀行作成ビュー（GET）のテスト"""
        response = self.client.get(reverse('master:bill_bank_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '振込先銀行作成')
    
    def test_bill_bank_create_view_post(self):
        """振込先銀行作成ビュー（POST）のテスト"""
        form_data = {
            'name': '新しい銀行',
            'bank_code': '0020',
            'branch_name': '新しい支店',
            'branch_code': '200',
            'account_type': 'current',
            'account_number': '2222222',
            'account_holder': '新しい会社',
            'is_active': True,
            'display_order': 1
        }
        response = self.client.post(reverse('master:bill_bank_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BillBank.objects.filter(name='新しい銀行').exists())
    
    def test_bill_bank_update_view(self):
        """振込先銀行更新ビューのテスト"""
        response = self.client.get(
            reverse('master:bill_bank_update', kwargs={'pk': self.bill_bank.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト銀行')
    
    def test_bill_bank_delete_view(self):
        """振込先銀行削除ビューのテスト"""
        response = self.client.get(
            reverse('master:bill_bank_delete', kwargs={'pk': self.bill_bank.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト銀行')
        
        # 削除実行
        response = self.client.post(
            reverse('master:bill_bank_delete', kwargs={'pk': self.bill_bank.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BillBank.objects.filter(pk=self.bill_bank.pk).exists())