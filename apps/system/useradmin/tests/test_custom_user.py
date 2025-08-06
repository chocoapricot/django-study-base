from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.system.useradmin.models import CustomUser
from apps.system.useradmin.forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()


class CustomUserModelTest(TestCase):
    def test_custom_user_creation(self):
        """CustomUserモデルの作成テスト"""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='太郎',
            last_name='田中'
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, '太郎')
        self.assertEqual(user.last_name, '田中')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_custom_user_str_representation(self):
        """CustomUserの文字列表現テスト"""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='太郎',
            last_name='田中'
        )
        
        # フルネームがある場合
        expected_str = '田中 太郎 (testuser)'
        self.assertEqual(str(user), expected_str)
        
        # フルネームがない場合
        user_no_name = CustomUser.objects.create_user(
            username='noname',
            email='noname@example.com'
        )
        self.assertEqual(str(user_no_name), 'noname')

    def test_custom_user_superuser_creation(self):
        """スーパーユーザーの作成テスト"""
        superuser = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertEqual(superuser.username, 'admin')
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_custom_user_email_unique(self):
        """メールアドレスの一意性テスト"""
        CustomUser.objects.create_user(
            username='user1',
            email='unique@example.com',
            password='testpass123'
        )
        
        # 同じメールアドレスのユーザーは作成できない
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                username='user2',
                email='unique@example.com',
                password='testpass123'
            )

    def test_custom_user_get_full_name(self):
        """フルネーム取得のテスト"""
        user = CustomUser.objects.create_user(
            username='testuser',
            first_name='太郎',
            last_name='田中'
        )
        
        self.assertEqual(user.get_full_name(), '田中 太郎')
        
        # 名前が設定されていない場合
        user_no_name = CustomUser.objects.create_user(username='noname')
        self.assertEqual(user_no_name.get_full_name(), '')

    def test_custom_user_get_short_name(self):
        """ショートネーム取得のテスト"""
        user = CustomUser.objects.create_user(
            username='testuser',
            first_name='太郎'
        )
        
        self.assertEqual(user.get_short_name(), '太郎')


class CustomUserFormTest(TestCase):
    def test_custom_user_creation_form_valid(self):
        """CustomUserCreationFormの有効なデータテスト"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': '太郎',
            'last_name': '田中',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_custom_user_creation_form_password_mismatch(self):
        """CustomUserCreationFormのパスワード不一致テスト"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123!',
            'password2': 'differentpass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_custom_user_creation_form_required_fields(self):
        """CustomUserCreationFormの必須フィールドテスト"""
        form = CustomUserCreationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)

    def test_custom_user_change_form_valid(self):
        """CustomUserChangeFormの有効なデータテスト"""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        form_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': '次郎',
            'last_name': '佐藤',
            'is_active': True
        }
        form = CustomUserChangeForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())


class CustomUserViewTest(TestCase):
    def setUp(self):
        self.superuser = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='太郎',
            last_name='田中'
        )
        self.test_client = TestClient()

    def test_user_list_view(self):
        """ユーザー一覧ビューのテスト"""
        self.test_client.login(username='admin', password='adminpass123')
        
        response = self.test_client.get(reverse('useradmin:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_user_detail_view(self):
        """ユーザー詳細ビューのテスト"""
        self.test_client.login(username='admin', password='adminpass123')
        
        response = self.test_client.get(
            reverse('useradmin:user_detail', kwargs={'pk': self.user.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
        self.assertContains(response, '田中 太郎')

    def test_user_create_view(self):
        """ユーザー作成ビューのテスト"""
        self.test_client.login(username='admin', password='adminpass123')
        
        response = self.test_client.get(reverse('useradmin:user_create'))
        self.assertEqual(response.status_code, 200)

    def test_user_update_view(self):
        """ユーザー更新ビューのテスト"""
        self.test_client.login(username='admin', password='adminpass123')
        
        response = self.test_client.get(
            reverse('useradmin:user_update', kwargs={'pk': self.user.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_user_delete_view(self):
        """ユーザー削除ビューのテスト"""
        self.test_client.login(username='admin', password='adminpass123')
        
        response = self.test_client.get(
            reverse('useradmin:user_delete', kwargs={'pk': self.user.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_user_create_post(self):
        """ユーザー作成POSTのテスト"""
        self.test_client.login(username='admin', password='adminpass123')
        
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': '花子',
            'last_name': '山田',
            'password1': 'newpass123!',
            'password2': 'newpass123!'
        }
        
        response = self.test_client.post(
            reverse('useradmin:user_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            CustomUser.objects.filter(username='newuser').exists()
        )

    def test_user_update_post(self):
        """ユーザー更新POSTのテスト"""
        self.test_client.login(username='admin', password='adminpass123')
        
        form_data = {
            'username': 'testuser',
            'email': 'updated@example.com',
            'first_name': '次郎',
            'last_name': '佐藤',
            'is_active': True
        }
        
        response = self.test_client.post(
            reverse('useradmin:user_update', kwargs={'pk': self.user.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.first_name, '次郎')
        self.assertEqual(self.user.last_name, '佐藤')

    def test_user_profile_view(self):
        """ユーザープロフィールビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('useradmin:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_user_password_change_view(self):
        """パスワード変更ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('useradmin:password_change'))
        self.assertEqual(response.status_code, 200)

    def test_user_access_control(self):
        """ユーザーアクセス制御のテスト"""
        # 一般ユーザーは他のユーザーの詳細を見れない
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('useradmin:user_detail', kwargs={'pk': self.superuser.pk})
        )
        self.assertEqual(response.status_code, 403)  # Forbidden