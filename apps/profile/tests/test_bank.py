"""
銀行情報機能のテスト
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission

from apps.profile.models import StaffProfile, StaffProfileBank
from apps.profile.forms import StaffProfileBankForm
from apps.master.models import Bank, BankBranch
from apps.system.settings.models import Dropdowns

User = get_user_model()


class StaffProfileBankModelTest(TestCase):
    """StaffProfileBankモデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.bank_master = Bank.objects.create(bank_code='0001', name='テスト銀行', is_active=True)
        self.branch_master = BankBranch.objects.create(bank=self.bank_master, branch_code='001', name='テスト支店', is_active=True)
        Dropdowns.objects.create(category='bank_account_type', value='1', name='普通', disp_seq=1)

    def test_create_bank_profile(self):
        """銀行プロフィールの作成テスト"""
        bank = StaffProfileBank.objects.create(
            user=self.user,
            bank_code='0001',
            branch_code='001',
            account_type='1',
            account_number='1234567',
            account_holder='テスト太郎'
        )
        
        self.assertEqual(bank.user, self.user)
        self.assertEqual(bank.bank_code, '0001')
        self.assertEqual(bank.branch_code, '001')
        self.assertEqual(bank.account_type, '1')
        self.assertEqual(bank.account_number, '1234567')
        self.assertEqual(bank.account_holder, 'テスト太郎')
        self.assertEqual(str(bank), f"{self.user.username} - 銀行情報")
    
    def test_bank_profile_properties(self):
        """銀行プロフィールのプロパティテスト"""
        bank = StaffProfileBank.objects.create(
            user=self.user,
            bank_code='0001',
            branch_code='001',
            account_type='1',
            account_number='1234567',
            account_holder='テスト太郎'
        )
        
        self.assertEqual(bank.bank_name, 'テスト銀行')
        self.assertEqual(bank.branch_name, 'テスト支店')
        self.assertEqual(bank.get_account_type_display, '普通')


class StaffProfileBankFormTest(TestCase):
    """StaffProfileBankFormのテスト"""
    
    def setUp(self):
        Dropdowns.objects.create(category='bank_account_type', value='1', name='普通', disp_seq=1)
        self.bank_master = Bank.objects.create(bank_code='0001', name='テスト銀行', is_active=True)
        self.branch_master = BankBranch.objects.create(bank=self.bank_master, branch_code='001', name='テスト支店', is_active=True)

    def test_valid_form(self):
        """正常なフォームデータのテスト"""
        form_data = {
            'bank_code': '0001',
            'branch_code': '001',
            'account_type': '1',
            'account_number': '1234567',
            'account_holder': 'テスト太郎'
        }
        
        form = StaffProfileBankForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = StaffProfileBankForm(data={})
        self.assertFalse(form.is_valid())
        
        # 必須フィールドのチェック
        required_fields = ['account_type', 'account_number', 'account_holder']
        for field in required_fields:
            self.assertIn(field, form.errors)


class BankViewTest(TestCase):
    """銀行情報ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を付与
        permissions = Permission.objects.filter(
            codename__in=[
                'view_staffprofilebank',
                'add_staffprofilebank',
                'change_staffprofilebank',
                'delete_staffprofilebank'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.client.login(username='testuser', password='testpass123')

        self.bank_master = Bank.objects.create(bank_code='0001', name='テスト銀行', is_active=True)
        self.branch_master = BankBranch.objects.create(bank=self.bank_master, branch_code='001', name='テスト支店', is_active=True)
        Dropdowns.objects.create(category='bank_account_type', value='1', name='普通', disp_seq=1)

    def test_bank_detail_view_no_data(self):
        """銀行詳細ビュー（データなし）のテスト"""
        response = self.client.get(reverse('profile:bank_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行口座が登録されていません')
    
    def test_bank_detail_view_with_data(self):
        """銀行詳細ビュー（データあり）のテスト"""
        bank = StaffProfileBank.objects.create(
            user=self.user,
            bank_code='0001',
            branch_code='001',
            account_type='1',
            account_number='1234567',
            account_holder='テスト太郎'
        )
        
        response = self.client.get(reverse('profile:bank_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0001')
        self.assertContains(response, 'テスト銀行')
        self.assertContains(response, '001')
        self.assertContains(response, 'テスト支店')
        self.assertContains(response, '普通')
        self.assertContains(response, '1234567')
        self.assertContains(response, 'テスト太郎')
    
    def test_bank_edit_view_get(self):
        """銀行編集ビュー（GET）のテスト"""
        response = self.client.get(reverse('profile:bank_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行口座登録')
    
    def test_bank_delete_view_get(self):
        """銀行削除ビュー（GET）のテスト"""
        bank = StaffProfileBank.objects.create(
            user=self.user,
            bank_code='0001',
            branch_code='001',
            account_type='1',
            account_number='1234567',
            account_holder='テスト太郎'
        )
        
        response = self.client.get(reverse('profile:bank_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行口座情報を削除しますか？この操作は取り消せません。')
    
    def test_bank_delete_view_post(self):
        """銀行削除ビュー（POST）のテスト"""
        bank = StaffProfileBank.objects.create(
            user=self.user,
            bank_code='0001',
            branch_code='001',
            account_type='1',
            account_number='1234567',
            account_holder='テスト太郎'
        )
        
        response = self.client.post(reverse('profile:bank_delete'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # データが削除されているか確認
        self.assertFalse(
            StaffProfileBank.objects.filter(user=self.user).exists()
        )
    
    def test_bank_view_without_permissions(self):
        """権限なしでのアクセステスト"""
        # 権限を削除
        self.user.user_permissions.clear()
        
        response = self.client.get(reverse('profile:bank_detail'))
        self.assertEqual(response.status_code, 403)  # 権限エラー


class BankIntegrationTest(TestCase):
    """銀行情報機能の統合テスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を付与
        permissions = Permission.objects.filter(
            codename__in=[
                'view_staffprofilebank',
                'add_staffprofilebank',
                'change_staffprofilebank',
                'delete_staffprofilebank'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.client.login(username='testuser', password='testpass123')

        self.bank_master = Bank.objects.create(bank_code='0001', name='テスト銀行', is_active=True)
        self.branch_master = BankBranch.objects.create(bank=self.bank_master, branch_code='001', name='テスト支店', is_active=True)
        Dropdowns.objects.create(category='bank_account_type', value='1', name='普通', disp_seq=1)

    def test_full_bank_workflow(self):
        """銀行情報の完全なワークフローテスト"""
        # 1. 詳細画面でデータなし確認
        response = self.client.get(reverse('profile:bank_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行口座が登録されていません')
        
        # 2. 編集画面アクセス(GET)
        response = self.client.get(reverse('profile:bank_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行口座登録')

        # 3. データ登録(POST)
        form_data = {
            'bank_code': '0001',
            'branch_code': '001',
            'account_type': '1',
            'account_number': '1234567',
            'account_holder': 'テストタロウ'
        }
        response = self.client.post(reverse('profile:bank_edit'), form_data)
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertTrue(StaffProfileBank.objects.filter(user=self.user).exists())

        # 4. 詳細画面でデータあり確認
        response = self.client.get(reverse('profile:bank_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト銀行')
        self.assertContains(response, 'テスト支店')
        self.assertContains(response, '普通')
        
        # 5. 編集画面でデータ表示確認
        response = self.client.get(reverse('profile:bank_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="テスト銀行"')
        self.assertContains(response, 'value="テスト支店"')

        # 6. 削除処理
        response = self.client.post(reverse('profile:bank_delete'))
        self.assertEqual(response.status_code, 302)
        
        # 7. データが削除されているか確認
        self.assertFalse(
            StaffProfileBank.objects.filter(user=self.user).exists()
        )