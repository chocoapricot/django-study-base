
import datetime
from django.test import TestCase
from unittest.mock import patch
from apps.accounts.models import MyUser
from apps.client.forms import ClientForm, ClientDepartmentForm, ClientContactedForm
from apps.client.forms_mail import ClientUserMailForm
from apps.client.models import Client, ClientDepartment, ClientUser, ClientContacted
from apps.system.settings.models import Dropdowns
from django.utils import timezone

class ClientContactedFormTest(TestCase):
    def setUp(self):
        """テストに必要なデータを作成"""
        self.client = Client.objects.create(
            name='テストクライアント',
            name_furigana='テストクライアント',
            corporate_number='1112223334445'
        )
        self.department1 = ClientDepartment.objects.create(
            client=self.client,
            name='営業部'
        )
        self.department2 = ClientDepartment.objects.create(
            client=self.client,
            name='開発部'
        )
        self.user_in_dept1 = ClientUser.objects.create(
            client=self.client,
            department=self.department1,
            name_last='山田',
            name_first='太郎'
        )
        self.base_data = {
            'contacted_at': timezone.now(),
            'content': 'テスト連絡',
            'client': self.client.pk,
        }

    def test_user_department_validation(self):
        """担当者が選択された所属に属しているかのバリデーションをテスト"""
        # --- 異常系 ---
        # 担当者(営業部)と異なる所属(開発部)を紐付けて登録
        invalid_data = self.base_data.copy()
        invalid_data.update({
            'department': self.department2.pk, # 開発部
            'user': self.user_in_dept1.pk,      # 営業部の山田さん
        })
        form = ClientContactedForm(data=invalid_data, client=self.client)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
        self.assertEqual(form.errors['user'][0], '指定された担当者はこの所属にはいません。')

        # --- 正常系 ---
        # 担当者(営業部)と同じ所属(営業部)を紐付けて登録
        valid_data = self.base_data.copy()
        valid_data.update({
            'department': self.department1.pk, # 営業部
            'user': self.user_in_dept1.pk,      # 営業部の山田さん
        })
        form = ClientContactedForm(data=valid_data, client=self.client)
        self.assertTrue(form.is_valid(), form.errors)


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


class ClientDepartmentFormTest(TestCase):
    def setUp(self):
        self.client = Client.objects.create(
            name='テストクライアント',
            name_furigana='テストクライアント',
            corporate_number='9876543210123'
        )
        self.base_data = {
            'client': self.client.pk,
            'name': 'テスト部署',
            'display_order': 0,
        }

    def test_haken_validation_valid_cases(self):
        """派遣関連のバリデーション: 正常系ケース"""
        # ケース1: どちらもFalseで、関連フィールドは空
        data = self.base_data.copy()
        data.update({
            'is_haken_office': False,
            'haken_jigyosho_teishokubi': '',
            'is_haken_unit': False,
            'haken_unit_manager_title': '',
        })
        form = ClientDepartmentForm(data=data)
        self.assertTrue(form.is_valid(), f"Case 1 failed: {form.errors.as_json()}")

        # ケース2: is_haken_officeがTrueで、抵触日が入力されている
        data = self.base_data.copy()
        data.update({
            'is_haken_office': True,
            'haken_jigyosho_teishokubi': datetime.date.today(),
            'is_haken_unit': False,
            'haken_unit_manager_title': '',
        })
        form = ClientDepartmentForm(data=data)
        self.assertTrue(form.is_valid(), f"Case 2 failed: {form.errors.as_json()}")

        # ケース2.1: is_haken_officeがTrueで、抵触日が空でもOK
        data = self.base_data.copy()
        data.update({
            'is_haken_office': True,
            'haken_jigyosho_teishokubi': '',
            'is_haken_unit': False,
            'haken_unit_manager_title': '',
        })
        form = ClientDepartmentForm(data=data)
        self.assertTrue(form.is_valid(), f"Case 2.1 failed: {form.errors.as_json()}")

        # ケース3: is_haken_unitがTrueで、役職が入力されている
        data = self.base_data.copy()
        data.update({
            'is_haken_office': False,
            'haken_jigyosho_teishokubi': '',
            'is_haken_unit': True,
            'haken_unit_manager_title': '組織単位長',
        })
        form = ClientDepartmentForm(data=data)
        self.assertTrue(form.is_valid(), f"Case 3 failed: {form.errors.as_json()}")

        # ケース4: どちらもTrueで、関連フィールドがすべて入力されている
        data = self.base_data.copy()
        data.update({
            'is_haken_office': True,
            'haken_jigyosho_teishokubi': datetime.date.today(),
            'is_haken_unit': True,
            'haken_unit_manager_title': '組織単位長',
        })
        form = ClientDepartmentForm(data=data)
        self.assertTrue(form.is_valid(), f"Case 4 failed: {form.errors.as_json()}")

    def test_haken_validation_invalid_cases(self):
        """派遣関連のバリデーション: 異常系ケース"""
        # ケース1: is_haken_officeがFalseなのに、抵触日が入力されている
        data = self.base_data.copy()
        data.update({
            'is_haken_office': False,
            'haken_jigyosho_teishokubi': datetime.date.today(),
        })
        form = ClientDepartmentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('haken_jigyosho_teishokubi', form.errors)


        # ケース3: is_haken_unitがFalseなのに、役職が入力されている
        data = self.base_data.copy()
        data.update({
            'is_haken_unit': False,
            'haken_unit_manager_title': '組織単位長',
        })
        form = ClientDepartmentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('haken_unit_manager_title', form.errors)

        # ケース4: is_haken_unitがTrueなのに、役職が空
        data = self.base_data.copy()
        data.update({
            'is_haken_unit': True,
            'haken_unit_manager_title': '',
        })
        form = ClientDepartmentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('haken_unit_manager_title', form.errors)
