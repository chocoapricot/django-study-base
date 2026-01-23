from django.test import TestCase
from ..forms import CompanyForm, CompanyUserForm
from ..models import Company, CompanyDepartment

class CompanyFormTest(TestCase):
    """会社情報フォームのテスト"""

    def test_corporate_number_validation(self):
        """法人番号のバリデーションテスト"""
        # 無効な法人番号（桁数不足）
        form_data = {'name': 'テスト会社', 'corporate_number': '123456789012'}
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 無効な法人番号（チェックディジット不正）
        form_data = {'name': 'テスト会社', 'corporate_number': '1234567890123'}
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('corporate_number', form.errors)

        # 有効な法人番号（実際の法人番号例）
        form_data = {'name': 'テスト会社', 'corporate_number': '2000012010019', 'dispatch_treatment_method': 'agreement'}
        form = CompanyForm(data=form_data)
        self.assertTrue(form.is_valid())

        # 法人番号が空の場合は有効とする
        form_data = {'name': 'テスト会社', 'corporate_number': '', 'dispatch_treatment_method': 'agreement'}
        form = CompanyForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_corporate_number_edge_cases(self):
        """法人番号のエッジケーステスト"""
        # 13桁未満
        form_data = {'name': 'テスト会社', 'corporate_number': '12345', 'dispatch_treatment_method': 'agreement'}
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())

        # 13桁超過
        form_data = {'name': 'テスト会社', 'corporate_number': '12345678901234', 'dispatch_treatment_method': 'agreement'}
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())

        # 数字以外の文字を含む
        form_data = {'name': 'テスト会社', 'corporate_number': '200001201001a', 'dispatch_treatment_method': 'agreement'}
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_phone_number_invalid(self):
        """
        電話番号に英字が含まれる場合はバリデーションエラー
        """
        form_data = {
            'name': 'テスト会社',
            'corporate_number': '2000012010019',
            'representative': '代表者',
            'postal_code': '1000001',
            'address': '東京都千代田区千代田1-1',
            'phone_number': '03-1234-ABCD',
            'dispatch_treatment_method': 'agreement',
        }
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
        self.assertIn('電話番号は数字とハイフンのみ入力してください。', form.errors['phone_number'])


class CompanyUserFormTest(TestCase):
    """自社担当者フォームのテスト"""

    def setUp(self):
        self.company = Company.objects.create(name="テスト株式会社", dispatch_treatment_method='agreement')
        self.department = CompanyDepartment.objects.create(name="テスト部署")
        self.valid_data = {
            'department': self.department.pk,
            'name_last': '田中',
            'name_first': '角栄',
            'position': '課長',
            'phone_number': '090-1234-5678',
            'email': 'tanaka@example.com',
            'display_order': 1,
        }

    def test_valid_form(self):
        """有効なフォームのテスト"""
        form = CompanyUserForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_invalid_phone_number(self):
        """無効な電話番号のテスト"""
        invalid_data = self.valid_data.copy()
        invalid_data['phone_number'] = '090-1234-ABCD' # Invalid characters
        form = CompanyUserForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)

    def test_name_required(self):
        """氏名が必須であることのテスト"""
        invalid_data = self.valid_data.copy()
        del invalid_data['name_last']
        del invalid_data['name_first']
        form = CompanyUserForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name_last', form.errors)
        self.assertIn('name_first', form.errors)
