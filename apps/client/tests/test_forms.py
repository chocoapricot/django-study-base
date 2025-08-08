
from django.test import TestCase
from apps.client.forms import ClientForm
from apps.system.settings.models import Dropdowns

class ClientFormTest(TestCase):
    def setUp(self):
        # テストに必要なDropdownsのデータを作成
        Dropdowns.objects.create(
            category='regist_form_client',
            name='テスト登録区分',
            value='1',
            disp_seq=1,
            active=True
        )

    def test_corporate_number_validation(self):
        # 正しい法人番号 (stdnumが有効と判断する番号)
        form_data = {'corporate_number': '5835678256246', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'regist_form_client': '1'}
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

        # 誤ったチェックディジット (stdnumがInvalidChecksumを返す番号)
        form_data = {'corporate_number': '2835678256246', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'regist_form_client': '1'}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 桁数が違う
        form_data = {'corporate_number': '12345', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'regist_form_client': '1'}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 数字以外が含まれる
        form_data = {'corporate_number': 'abcdefg123456', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'regist_form_client': '1'}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 空の場合は許容
        form_data = {'corporate_number': '', 'name': 'テスト株式会社', 'name_furigana': 'テストカブシキガイシャ', 'regist_form_client': '1'}
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
    
    def test_basic_contract_date_field(self):
        """基本契約締結日フィールドのテスト"""
        # 正しい日付形式
        form_data = {
            'corporate_number': '5835678256246',
            'name': 'テスト株式会社',
            'name_furigana': 'テストカブシキガイシャ',
            'regist_form_client': '1',
            'basic_contract_date': '2024-01-15'
        }
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        
        # 空の場合は許容
        form_data = {
            'corporate_number': '5835678256246',
            'name': 'テスト株式会社',
            'name_furigana': 'テストカブシキガイシャ',
            'regist_form_client': '1',
            'basic_contract_date': ''
        }
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        
        # 不正な日付形式
        form_data = {
            'corporate_number': '5835678256246',
            'name': 'テスト株式会社',
            'name_furigana': 'テストカブシキガイシャ',
            'regist_form_client': '1',
            'basic_contract_date': '2024/01/15'  # スラッシュ区切りは不正
        }
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('basic_contract_date', form.errors)
