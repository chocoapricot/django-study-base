from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.accounts.forms import UserProfileForm
from apps.accounts.validators import MyPasswordValidator

User = get_user_model()


class PasswordValidationTest(TestCase):
    """パスワードバリデーションのテスト"""
    
    def setUp(self):
        """テスト用ユーザーを作成"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='ValidPass123!',
            first_name='テスト',
            last_name='ユーザー'
        )
    
    def test_custom_password_validator_valid_password(self):
        """有効なパスワードのテスト"""
        validator = MyPasswordValidator()
        
        # 有効なパスワード（8文字以上、記号含む）
        valid_passwords = [
            'ValidPass123!',
            'MySecure@Pass1',
            'Test#Password2024',
            'Strong$Pass99'
        ]
        
        for password in valid_passwords:
            with self.subTest(password=password):
                try:
                    validator.validate(password, self.user)
                except ValidationError:
                    self.fail(f"有効なパスワード '{password}' でValidationErrorが発生しました")
    
    def test_custom_password_validator_invalid_password(self):
        """無効なパスワードのテスト"""
        validator = MyPasswordValidator()
        
        # 無効なパスワードのテストケース
        invalid_cases = [
            ('short', '短すぎるパスワード'),
            ('12345678', '記号なしの数字のみ'),
            ('password', '記号なしの文字のみ'),
            ('Password123', '記号なしの英数字'),
            ('Pass!', '短すぎる（記号あり）'),
        ]
        
        for password, description in invalid_cases:
            with self.subTest(password=password, description=description):
                with self.assertRaises(ValidationError, msg=f"無効なパスワード '{password}' ({description}) でValidationErrorが発生しませんでした"):
                    validator.validate(password, self.user)
    
    def test_profile_form_valid_password_change(self):
        """プロファイルフォームでの有効なパスワード変更テスト"""
        form_data = {
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'password': 'NewValidPass123!',
            'password_confirm': 'NewValidPass123!'
        }
        
        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")
    
    def test_profile_form_invalid_password_change(self):
        """プロファイルフォームでの無効なパスワード変更テスト"""
        # 短すぎるパスワード
        form_data = {
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'password': 'short',
            'password_confirm': 'short'
        }
        
        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
    
    def test_profile_form_password_mismatch(self):
        """プロファイルフォームでのパスワード不一致テスト"""
        form_data = {
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'password': 'ValidPass123!',
            'password_confirm': 'DifferentPass123!'
        }
        
        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('password_confirm', form.errors)
        self.assertIn('パスワードが一致しません', str(form.errors['password_confirm']))
    
    def test_profile_form_no_password_change(self):
        """プロファイルフォームでパスワード変更なしのテスト"""
        form_data = {
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'password': '',
            'password_confirm': ''
        }
        
        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")
    
    def test_profile_form_symbol_required_password(self):
        """記号必須パスワードのテスト"""
        # 記号なしパスワード
        form_data = {
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'password': 'Password123',
            'password_confirm': 'Password123'
        }
        
        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
        # 記号が必要というエラーメッセージが含まれているかチェック
        error_message = str(form.errors['password'])
        self.assertIn('記号', error_message)
    
    def test_profile_form_minimum_length_password(self):
        """最小文字数パスワードのテスト"""
        # 7文字のパスワード（最小8文字未満）
        form_data = {
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'password': 'Pass1!',
            'password_confirm': 'Pass1!'
        }
        
        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
        # 最小文字数のエラーメッセージが含まれているかチェック
        error_message = str(form.errors['password'])
        self.assertIn('8文字以上', error_message)


class PasswordValidatorHelpTextTest(TestCase):
    """パスワードバリデーターのヘルプテキストテスト"""
    
    def test_help_text_generation(self):
        """ヘルプテキストの生成テスト"""
        validator = MyPasswordValidator()
        help_text = validator.get_help_text()
        
        # ヘルプテキストに必要な情報が含まれているかチェック
        self.assertIn('8文字以上', help_text)
        self.assertIn('記号', help_text)
        self.assertIsInstance(help_text, str)
        self.assertTrue(len(help_text) > 0)