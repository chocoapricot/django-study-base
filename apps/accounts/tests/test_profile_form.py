from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.forms import UserProfileForm

User = get_user_model()

class UserProfileFormTest(TestCase):
    """ユーザープロファイルフォームのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            first_name='太郎',
            last_name='田中'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            first_name='花子',
            last_name='佐藤'
        )
    
    def test_email_change_to_unique_address(self):
        """未使用のメールアドレスへの変更は成功する"""
        form_data = {
            'email': 'newemail@test.com',
            'first_name': '太郎',
            'last_name': '田中',
            'phone_number': '090-1234-5678'
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertTrue(form.is_valid())
    
    def test_email_change_to_existing_address(self):
        """他のユーザーが使用中のメールアドレスへの変更は失敗する"""
        form_data = {
            'email': 'user2@test.com',  # user2が既に使用中
            'first_name': '太郎',
            'last_name': '田中',
            'phone_number': '090-1234-5678'
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('既に他のユーザーによって使用されています', str(form.errors['email']))
    
    def test_email_keep_same_address(self):
        """同じメールアドレスのまま変更は成功する"""
        form_data = {
            'email': 'user1@test.com',  # 自分のメールアドレス
            'first_name': '太郎',
            'last_name': '田中',
            'phone_number': '090-1234-5678'
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertTrue(form.is_valid())
    
    def test_password_validation(self):
        """パスワード確認のバリデーション"""
        form_data = {
            'email': 'user1@test.com',
            'first_name': '太郎',
            'last_name': '田中',
            'phone_number': '090-1234-5678',
            'password': 'ValidPass123!',  # 有効なパスワード
            'password_confirm': 'DifferentPass123!'  # 異なるパスワード
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertFalse(form.is_valid())
        self.assertIn('password_confirm', form.errors)
        self.assertIn('パスワードが一致しません', str(form.errors['password_confirm']))
    
    def test_password_validation_success(self):
        """パスワード確認が一致する場合は成功"""
        form_data = {
            'email': 'user1@test.com',
            'first_name': '太郎',
            'last_name': '田中',
            'phone_number': '090-1234-5678',
            'password': 'NewPassword123!',  # 記号を含む有効なパスワード
            'password_confirm': 'NewPassword123!'
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")
    
    def test_required_fields_validation(self):
        """必須フィールドのバリデーション"""
        # メールアドレスが空の場合
        form_data = {
            'email': '',
            'first_name': '太郎',
            'last_name': '田中',
            'phone_number': '090-1234-5678'
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
        # 姓が空の場合
        form_data = {
            'email': 'user1@test.com',
            'first_name': '太郎',
            'last_name': '',
            'phone_number': '090-1234-5678'
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)
        
        # 名が空の場合
        form_data = {
            'email': 'user1@test.com',
            'first_name': '',
            'last_name': '田中',
            'phone_number': '090-1234-5678'
        }
        form = UserProfileForm(data=form_data, instance=self.user1)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)