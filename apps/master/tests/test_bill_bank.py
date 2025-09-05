from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.master.models import BillBank, Bank, BankBranch
from apps.master.forms import BillBankForm

User = get_user_model()


from apps.system.settings.models import Dropdowns


class BillBankModelTest(TestCase):
    """会社銀行モデルのテスト"""
    
    def setUp(self):
        self.bank = Bank.objects.create(name='三菱UFJ銀行', bank_code='0005')
        self.branch = BankBranch.objects.create(bank=self.bank, name='新宿支店', branch_code='001')
        Dropdowns.objects.create(category='bank_account_type', value='ordinary', name='普通', disp_seq=1)
        Dropdowns.objects.create(category='bank_account_type', value='current', name='当座', disp_seq=2)
        self.bill_bank = BillBank.objects.create(
            bank_code='0005',
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
    
    def test_get_account_type_display(self):
        """口座種別表示のテスト"""
        self.assertEqual(self.bill_bank.get_account_type_display, '普通')
        
        bank2 = Bank.objects.create(name='みずほ銀行', bank_code='0001')
        BankBranch.objects.create(bank=bank2, name='渋谷支店', branch_code='140')
        bill_bank = BillBank.objects.create(
            bank_code='0001',
            branch_code='140',
            account_type='current',
            account_number='9876543',
            account_holder='株式会社サンプル'
        )
        self.assertEqual(bill_bank.get_account_type_display, '当座')
    
    def test_full_bank_info(self):
        """完全な銀行情報のテスト"""
        expected = '三菱UFJ銀行（0005） 新宿支店（001） 普通 1234567'
        self.assertEqual(self.bill_bank.full_bank_info, expected)
        
        bank2 = Bank.objects.create(name='地方銀行', bank_code='0097')
        BankBranch.objects.create(bank=bank2, name='本店', branch_code='997')
        bill_bank = BillBank.objects.create(
            bank_code='0097',
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
        bill_bank = BillBank(
            branch_code='001',
            account_type='ordinary',
            account_number='1234567',
            account_holder='テスト'
        )
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        bill_bank.bank_code = 'abcd'
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        bill_bank.bank_code = '123'
        with self.assertRaises(ValidationError):
            bill_bank.clean()
    
    def test_validation_branch_code(self):
        """支店コードバリデーションのテスト"""
        bill_bank = BillBank(
            bank_code='0001',
            account_type='ordinary',
            account_number='1234567',
            account_holder='テスト'
        )
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        bill_bank.branch_code = 'ab'
        with self.assertRaises(ValidationError):
            bill_bank.clean()
    
    def test_validation_account_number(self):
        """口座番号バリデーションのテスト"""
        bill_bank = BillBank(
            bank_code='0001',
            branch_code='001',
            account_type='ordinary',
            account_number='abcdefg',
            account_holder='テスト'
        )
        with self.assertRaises(ValidationError):
            bill_bank.clean()
        
        bill_bank.account_number = '123456789'
        with self.assertRaises(ValidationError):
            bill_bank.clean()
    
    def test_get_active_list(self):
        """有効な会社銀行一覧取得のテスト"""
        BillBank.objects.create(
            bank_code='0005',
            branch_code='001',
            account_type='ordinary',
            account_number='9999999',
            account_holder='無効会社',
            is_active=False
        )
        
        active_list = BillBank.get_active_list()
        self.assertEqual(active_list.count(), 1)
        self.assertEqual(active_list.first().bank_name, '三菱UFJ銀行')


class BillBankFormTest(TestCase):
    """会社銀行フォームのテスト"""

    def setUp(self):
        from apps.system.settings.models import Dropdowns
        self.bank = Bank.objects.create(bank_code='0010', name='テスト銀行')
        self.branch = BankBranch.objects.create(bank=self.bank, branch_code='100', name='テスト支店')
        Dropdowns.objects.create(category='bank_account_type', value='ordinary', name='普通', disp_seq=1)

    def test_valid_form(self):
        """有効なフォームのテスト"""
        form_data = {
            'bank_code': '0010',
            'branch_code': '100',
            'account_type': 'ordinary',
            'account_number': '7777777',
            'account_holder': '株式会社フォームテスト',
            'account_holder_kana': 'カブシキガイシャフォームテスト',
            'is_active': True,
            'display_order': 1
        }
        form = BillBankForm(data=form_data)
        if not form.is_valid():
            print(form.errors)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_account_holder(self):
        """口座名義が未入力の場合のテスト"""
        form_data = {
            'bank_code': '0010',
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
            'bank_code': '0010',
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
    """会社銀行ビューのテスト"""
    
    def setUp(self):
        from apps.system.settings.models import Dropdowns
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_superuser=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.bank = Bank.objects.create(name='テスト銀行', bank_code='0099')
        self.branch = BankBranch.objects.create(bank=self.bank, name='テスト支店', branch_code='999')
        self.bill_bank = BillBank.objects.create(
            bank_code='0099',
            branch_code='999',
            account_type='ordinary',
            account_number='1111111',
            account_holder='テスト会社',
            account_holder_kana='テストガイシャ'
        )
        Dropdowns.objects.create(category='bank_account_type', value='ordinary', name='普通')
        Dropdowns.objects.create(category='bank_account_type', value='current', name='当座')
    
    def test_bill_bank_list_view(self):
        """会社銀行一覧ビューのテスト"""
        response = self.client.get(reverse('master:bill_bank_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト銀行')
    
    def test_bill_bank_create_view_get(self):
        """会社銀行作成ビュー（GET）のテスト"""
        response = self.client.get(reverse('master:bill_bank_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '会社銀行作成')
    
    def test_bill_bank_create_view_post(self):
        """会社銀行作成ビュー（POST）のテスト"""
        Bank.objects.create(name='新しい銀行', bank_code='0020')
        BankBranch.objects.create(bank=Bank.objects.get(bank_code='0020'), name='新しい支店', branch_code='200')
        form_data = {
            'bank_code': '0020',
            'branch_code': '200',
            'account_type': 'current',
            'account_number': '2222222',
            'account_holder': '新しい会社',
            'account_holder_kana': 'アタラシイカイシャ',
            'is_active': True,
            'display_order': 1
        }
        response = self.client.post(reverse('master:bill_bank_create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BillBank.objects.filter(bank_code='0020').exists())
    
    def test_bill_bank_update_view(self):
        """会社銀行更新ビューのテスト"""
        response = self.client.get(
            reverse('master:bill_bank_update', kwargs={'pk': self.bill_bank.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト銀行')
    
    def test_bill_bank_delete_view(self):
        """会社銀行削除ビューのテスト"""
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