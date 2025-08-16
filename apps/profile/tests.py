from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import StaffProfile

User = get_user_model()


class StaffProfileModelTest(TestCase):
    """スタッフプロフィールモデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_staff_profile(self):
        """スタッフプロフィール作成テスト"""
        profile = StaffProfile.objects.create(
            user=self.user,
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            email=self.user.email
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.full_name, '田中 太郎')
        self.assertEqual(profile.full_name_kana, 'タナカ タロウ')
        self.assertEqual(str(profile), '田中 太郎')
    
    def test_full_address_property(self):
        """完全住所プロパティのテスト"""
        profile = StaffProfile.objects.create(
            user=self.user,
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            address1='東京都',
            address2='渋谷区',
            address3='1-1-1',
            email=self.user.email
        )
        
        self.assertEqual(profile.full_address, '東京都渋谷区1-1-1')


class StaffProfileViewTest(TestCase):
    """スタッフプロフィールビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_profile_detail_view_no_profile(self):
        """プロフィール詳細ビュー（プロフィール未作成）のテスト"""
        response = self.client.get(reverse('profile:detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'プロフィールが登録されていません')
    
    def test_profile_detail_view_with_profile(self):
        """プロフィール詳細ビュー（プロフィール作成済み）のテスト"""
        profile = StaffProfile.objects.create(
            user=self.user,
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            email=self.user.email
        )
        
        response = self.client.get(reverse('profile:detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '田中 太郎')
        self.assertContains(response, 'タナカ タロウ')
    
    def test_profile_edit_view_get(self):
        """プロフィール編集ビュー（GET）のテスト"""
        response = self.client.get(reverse('profile:edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'プロフィール作成')
    
    def test_profile_edit_view_post_create(self):
        """プロフィール編集ビュー（POST・作成）のテスト"""
        data = {
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
        }
        
        response = self.client.post(reverse('profile:edit'), data)
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # プロフィールが作成されたことを確認
        profile = StaffProfile.objects.get(user=self.user)
        self.assertEqual(profile.name_last, '田中')
        self.assertEqual(profile.name_first, '太郎')
        self.assertEqual(profile.email, self.user.email)
    
    def test_profile_edit_view_post_update(self):
        """プロフィール編集ビュー（POST・更新）のテスト"""
        # 既存のプロフィールを作成
        profile = StaffProfile.objects.create(
            user=self.user,
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            email=self.user.email
        )
        
        data = {
            'name_last': '佐藤',
            'name_first': '花子',
            'name_kana_last': 'サトウ',
            'name_kana_first': 'ハナコ',
        }
        
        response = self.client.post(reverse('profile:edit'), data)
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # プロフィールが更新されたことを確認
        profile.refresh_from_db()
        self.assertEqual(profile.name_last, '佐藤')
        self.assertEqual(profile.name_first, '花子')
    
    def test_profile_delete_view_get(self):
        """プロフィール削除ビュー（GET）のテスト"""
        profile = StaffProfile.objects.create(
            user=self.user,
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            email=self.user.email
        )
        
        response = self.client.get(reverse('profile:delete'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '田中 太郎')
        self.assertContains(response, 'この操作は取り消せません')
    
    def test_profile_delete_view_post(self):
        """プロフィール削除ビュー（POST）のテスト"""
        profile = StaffProfile.objects.create(
            user=self.user,
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            email=self.user.email
        )
        
        response = self.client.post(reverse('profile:delete'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # プロフィールが削除されたことを確認
        self.assertFalse(StaffProfile.objects.filter(user=self.user).exists())
    
    def test_login_required(self):
        """ログイン必須のテスト"""
        self.client.logout()
        
        # 各ビューにアクセスしてログインページにリダイレクトされることを確認
        urls = [
            reverse('profile:detail'),
            reverse('profile:edit'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)