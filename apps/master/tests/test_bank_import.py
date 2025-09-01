import io
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.master.models import Bank, BankBranch

User = get_user_model()

class BankImportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            email='test@example.com'
        )
        self.user.user_permissions.add(*self.get_permissions())
        self.client.login(username='testuser', password='testpassword')

    def get_permissions(self):
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='master',
            codename__in=['view_bank', 'add_bank', 'change_bank', 'delete_bank', 
                          'view_bankbranch', 'add_bankbranch', 'change_bankbranch', 'delete_bankbranch']
        )
        return permissions

    def test_get_import_page(self):
        """CSV取込ページにアクセスできるか"""
        response = self.client.get(reverse('master:bank_import'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'master/bank_import.html')

    def test_successful_import(self):
        """正常なCSVファイルでインポートが成功するか"""
        csv_data = (
            "0001,000,ﾐｽﾞﾎ           ,みずほ,1\n"
            "0001,001,ﾄｳｷﾖｳ          ,東京営業部,2\n"
        )
        csv_file = SimpleUploadedFile(
            "test_import.csv",
            csv_data.encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(reverse('master:bank_import'), {'csv_file': csv_file})
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('master:bank_import'))
        
        # Check that the bank and branch were created
        self.assertTrue(Bank.objects.filter(bank_code='0001').exists())
        self.assertTrue(BankBranch.objects.filter(bank__bank_code='0001', branch_code='001').exists())

    def test_import_with_invalid_data(self):
        """不正なデータを含むCSVファイルでエラーが表示されるか"""
        csv_data = (
            "0001,000,ﾐｽﾞﾎ           ,みずほ,1\n"
            "9999,001,無効な支店     ,むこうなしてん,2\n"  # Bank does not exist
        )
        csv_file = SimpleUploadedFile(
            "test_import_invalid.csv",
            csv_data.encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(reverse('master:bank_import'), {'csv_file': csv_file}, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '銀行コード 9999 が見つかりません。')
        
        # Check that the valid bank was created, but the invalid branch was not
        self.assertTrue(Bank.objects.filter(bank_code='0001').exists())
        self.assertFalse(BankBranch.objects.filter(branch_code='001').exists())
