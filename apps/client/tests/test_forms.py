
from django.test import TestCase
from unittest.mock import patch
from apps.accounts.models import MyUser
from apps.client.forms import ClientForm
from apps.client.forms_mail import ClientUserMailForm
from apps.client.models import Client, ClientDepartment, ClientUser, ClientContacted
from apps.system.settings.models import Dropdowns

class ClientFormTest(TestCase):
    def setUp(self):
        # テストに必要なDropdownsのデータを作成
        Dropdowns.objects.create(
            category='client_regist_status',
            name='テスト登録区分',
            value='1',
            disp_seq=1,
            active=True
        )

    def test_corporate_number_validation(self):
        # 正しい法人番号 (stdnumが有効と判断する番号)
        form_data = {'corporate_number': '5835678256246', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'client_regist_status': '1'}
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

        # 誤ったチェックディジット (stdnumがInvalidChecksumを返す番号)
        form_data = {'corporate_number': '2835678256246', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'client_regist_status': '1'}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 桁数が違う
        form_data = {'corporate_number': '12345', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'client_regist_status': '1'}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 数字以外が含まれる
        form_data = {'corporate_number': 'abcdefg123456', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'client_regist_status': '1'}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 空の場合は許容
        form_data = {'corporate_number': '', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'client_regist_status': '1'}
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
    
    def test_basic_contract_date_field(self):
        """基本契約締結日フィールドのテスト"""
        # 正しい日付形式
        form_data = {
            'corporate_number': '5835678256246',
            'name': 'テスト株式会社',
            'name_furigana': 'テストカブシキガイシャ',
            'client_regist_status': '1',
            'basic_contract_date': '2024-01-15'
        }
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        
        # 空の場合は許容
        form_data = {
            'corporate_number': '5835678256246',
            'name': 'テスト株式会社',
            'name_furigana': 'テストカブシキガイシャ',
            'client_regist_status': '1',
            'basic_contract_date': ''
        }
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        
        # 不正な日付形式
        form_data = {
            'corporate_number': '5835678256246',
            'name': 'テスト株式会社',
            'name_furigana': 'テストカブシキガイシャ',
            'client_regist_status': '1',
            'basic_contract_date': '2024/01/15'  # スラッシュ区切りは不正
        }
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('basic_contract_date', form.errors)


class ClientUserMailFormTest(TestCase):
    def setUp(self):
        """テストに必要なデータを作成"""
        self.sender_user = MyUser.objects.create_user(
            username='testsender',
            email='sender@example.com',
            password='password'
        )
        self.client = Client.objects.create(
            name='テストクライアント',
            name_furigana='テストクライアント',
            corporate_number='1234567890123'
        )
        self.department = ClientDepartment.objects.create(
            client=self.client,
            name='テスト部署'
        )
        self.client_user = ClientUser.objects.create(
            client=self.client,
            department=self.department,
            name_last='山田',
            name_first='太郎',
            email='receiver@example.com'
        )
        # 連絡種別 'メール' のためのDropdownを作成
        Dropdowns.objects.create(
            category='contact_type',
            name='メール',
            value='1',
            disp_seq=1,
            active=True
        )

    @patch('apps.client.forms_mail.send_mail')
    def test_send_mail_creates_contacted_history_with_user_and_department(self, mock_send_mail):
        """メール送信時に担当者と組織が設定された連絡履歴が作成されることをテスト"""
        mock_send_mail.return_value = 1 # Simulate successful email sending

        form_data = {
            'to_email': self.client_user.email,
            'subject': 'Test Subject',
            'body': 'Test Body',
        }

        form = ClientUserMailForm(
            client_user=self.client_user,
            user=self.sender_user,
            data=form_data
        )

        self.assertTrue(form.is_valid(), form.errors)

        success, message = form.send_mail()

        self.assertTrue(success)
        self.assertEqual(ClientContacted.objects.count(), 1)

        contacted = ClientContacted.objects.first()

        # These assertions will fail before the fix
        self.assertEqual(contacted.user, self.client_user)
        self.assertEqual(contacted.department, self.department)
