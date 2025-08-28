from django.test import TestCase
from ..forms import CompanyForm, CompanyUserForm
from ..models import Company
from django.contrib.auth import get_user_model

User = get_user_model()

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
        form_data = {'name': 'テスト会社', 'corporate_number': '2000012010019'}
        form = CompanyForm(data=form_data)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())

        # 法人番号が空の場合は有効とする
        form_data = {'name': 'テスト会社', 'corporate_number': ''}
        form = CompanyForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_corporate_number_edge_cases(self):
        """法人番号のエッジケーステスト"""
        # 13桁未満
        form_data = {'name': 'テスト会社', 'corporate_number': '12345'}
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())

        # 13桁超過
        form_data = {'name': 'テスト会社', 'corporate_number': '12345678901234'}
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())

        # 数字以外の文字を含む
        form_data = {'name': 'テスト会社', 'corporate_number': '200001201001a'}
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
        }
        form = CompanyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
        self.assertIn('電話番号は数字とハイフンのみ入力してください。', form.errors['phone_number'])


class CompanyUserFormTest(TestCase):
    """会社担当者フォームのテスト"""

    def setUp(self):
        self.company = Company.objects.create(name="テスト株式会社")
        self.user = User.objects.create_user(username='testuser', password='testpassword')

    def test_valid_form(self):
        """有効なフォームのテスト"""
        form_data = {'user': self.user.pk}
        form = CompanyUserForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_no_user(self):
        """ユーザーがいない場合の無効なフォームのテスト"""
        form_data = {'user': 999} # 存在しないユーザー
        form = CompanyUserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
