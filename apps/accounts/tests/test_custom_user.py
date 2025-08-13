from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.accounts.models import MyUser

User = get_user_model()

class MyUserModelTest(TestCase):
    """MyUserモデルのテスト"""
    
    def test_create_user(self):
        """ユーザー作成のテスト"""
        user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone_number='090-1234-5678'
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.phone_number, '090-1234-5678')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """スーパーユーザー作成のテスト"""
        admin_user = MyUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertEqual(admin_user.username, 'admin')
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.check_password('adminpass123'))
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_user_str_method(self):
        """ユーザーの文字列表現のテスト"""
        user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(str(user), 'testuser')

    def test_phone_number_field(self):
        """電話番号フィールドのテスト"""
        user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone_number='090-1234-5678'
        )
        
        self.assertEqual(user.phone_number, '090-1234-5678')

    def test_phone_number_optional(self):
        """電話番号フィールドが任意であることのテスト"""
        user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertIsNone(user.phone_number)

    def test_email_optional(self):
        """メールアドレスが任意であることのテスト"""
        user = MyUser.objects.create_user(
            username='testuser',
            email='',
            password='testpass123'
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, '')
        self.assertTrue(user.check_password('testpass123'))

    def test_username_required(self):
        """ユーザー名が必須であることのテスト"""
        with self.assertRaises(ValueError):
            MyUser.objects.create_user(
                username='',
                email='test@example.com',
                password='testpass123'
            )


class MyUserViewTest(TestCase):
    """MyUserビューのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.superuser = MyUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='太郎',
            last_name='田中'
        )
        self.test_client = TestClient()

    def test_user_profile_view(self):
        """ユーザープロフィールビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_profile_requires_login(self):
        """プロフィールページがログインを要求することのテスト"""
        response = self.test_client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertIn('/accounts/login/', response.url)