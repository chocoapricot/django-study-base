from django.urls import reverse
from django.test import Client
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.profile.models import StaffProfile

User = get_user_model()


class StaffProfileModelTests(TestCase):

    def test_profile_form_initial_name(self):
        """新規作成画面でUserの姓・名が初期値になること"""
        user = User.objects.create_user(
            username='u3', email='u3@example.com', first_name='Hanako', last_name='Suzuki', password='pass'
        )
        # 権限付与
        perms = Permission.objects.filter(codename__in=['add_staffprofile', 'change_staffprofile'])
        user.user_permissions.add(*perms)
        client = Client()
        client.force_login(user)
        # プロフィール未作成状態で新規作成画面へ
        url = reverse('profile:edit')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial.get('name_first'), 'Hanako')
        self.assertEqual(form.initial.get('name_last'), 'Suzuki')

    def test_user_save_updates_profile(self):
        """User保存時にStaffProfileの姓・名も同期されること"""
        user = User.objects.create_user(
            username='u4', email='u4@example.com', first_name='OldFirst', last_name='OldLast', password='pass'
        )
        profile = StaffProfile.objects.create(user=user, name_first='OldFirst', name_last='OldLast')
        # Userの姓・名を変更して保存
        user.first_name = 'NewFirst'
        user.last_name = 'NewLast'
        user.save()
        profile.refresh_from_db()
        self.assertEqual(profile.name_first, 'NewFirst')
        self.assertEqual(profile.name_last, 'NewLast')
    def test_init_from_user(self):
        """新規インスタンス作成時にUserの姓・名で初期化されること"""
        user = User.objects.create_user(
            username='u1', email='u1@example.com', first_name='Taro', last_name='Yamada', password='pass'
        )

        profile = StaffProfile(user=user)

        self.assertEqual(profile.name_first, 'Taro')
        self.assertEqual(profile.name_last, 'Yamada')

    def test_save_updates_user(self):
        """プロフィール保存時にUserの姓・名が上書きされること"""
        user = User.objects.create_user(
            username='u2', email='u2@example.com', first_name='OldFirst', last_name='OldLast', password='pass'
        )

        profile = StaffProfile(user=user)
        profile.name_first = 'NewFirst'
        profile.name_last = 'NewLast'
        profile.save()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'NewFirst')
        self.assertEqual(user.last_name, 'NewLast')

        # プロフィールの email は常に user.email と同期されている
        self.assertEqual(profile.email, user.email)
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.profile.models import StaffProfile, StaffMynumber

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
        from django.contrib.auth.models import Permission
        profile_perms = Permission.objects.filter(content_type__app_label='profile')
        for perm in profile_perms:
            self.user.user_permissions.add(perm)
    
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


class StaffMynumberModelTest(TestCase):
    """スタッフマイナンバーモデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_staff_mynumber(self):
        """スタッフマイナンバー作成テスト"""
        # 有効なマイナンバーの例（チェックデジット付き）
        valid_mynumber = '621498320257'  # これは有効なマイナンバーの例
        mynumber = StaffMynumber.objects.create(
            user=self.user,
            email=self.user.email,
            mynumber=valid_mynumber
        )
        
        self.assertEqual(mynumber.user, self.user)
        self.assertEqual(mynumber.mynumber, valid_mynumber)
        self.assertEqual(str(mynumber), 'testuser - マイナンバー')


class StaffMynumberViewTest(TestCase):
    """スタッフマイナンバービューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        from django.contrib.auth.models import Permission
        profile_perms = Permission.objects.filter(content_type__app_label='profile')
        for perm in profile_perms:
            self.user.user_permissions.add(perm)
    
    def test_mynumber_detail_view_no_mynumber(self):
        """マイナンバー詳細ビュー（マイナンバー未登録）のテスト"""
        response = self.client.get(reverse('profile:mynumber_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'マイナンバーが登録されていません')
    
    def test_mynumber_detail_view_with_mynumber(self):
        """マイナンバー詳細ビュー（マイナンバー登録済み）のテスト"""
        valid_mynumber = '621498320257'
        mynumber = StaffMynumber.objects.create(
            user=self.user,
            email=self.user.email,
            mynumber=valid_mynumber
        )
        
        response = self.client.get(reverse('profile:mynumber_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, valid_mynumber)
    
    def test_mynumber_edit_view_post_create(self):
        """マイナンバー編集ビュー（POST・作成）のテスト"""
        # 有効なマイナンバーを使用
        valid_mynumber = '621498320257'
        data = {
            'mynumber': valid_mynumber,
        }
        
        response = self.client.post(reverse('profile:mynumber_edit'), data)
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # マイナンバーが作成されたことを確認
        mynumber = StaffMynumber.objects.get(user=self.user)
        self.assertEqual(mynumber.mynumber, valid_mynumber)
        self.assertEqual(mynumber.email, self.user.email)
    
    def test_mynumber_delete_view_post(self):
        """マイナンバー削除ビュー（POST）のテスト"""
        valid_mynumber = '621498320257'
        mynumber = StaffMynumber.objects.create(
            user=self.user,
            email=self.user.email,
            mynumber=valid_mynumber
        )
        
        response = self.client.post(reverse('profile:mynumber_delete'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # マイナンバーが削除されたことを確認
        self.assertFalse(StaffMynumber.objects.filter(user=self.user).exists())
    
    def test_mynumber_validation(self):
        """マイナンバーバリデーションのテスト"""
        from apps.profile.forms import StaffMynumberForm
        
        try:
            from stdnum.jp import in_
            
            # 有効なマイナンバー（例として提供されたもの）
            valid_mynumber = '621498320257'
            
            # 無効なマイナンバー（チェックデジットが間違っている）
            invalid_mynumber = '123456789012'
            
            # 有効なマイナンバーのテスト
            form = StaffMynumberForm(data={'mynumber': valid_mynumber})
            self.assertTrue(form.is_valid())
            
            # 無効なマイナンバーのテスト
            form = StaffMynumberForm(data={'mynumber': invalid_mynumber})
            self.assertFalse(form.is_valid())
            self.assertIn('mynumber', form.errors)
            
        except ImportError:
            # python-stdnumがない場合は基本的なテストのみ
            # 有効な12桁の数字
            form = StaffMynumberForm(data={'mynumber': '123456789012'})
            self.assertTrue(form.is_valid())
        
        # 桁数が間違っている
        form = StaffMynumberForm(data={'mynumber': '12345678901'})
        self.assertFalse(form.is_valid())
        self.assertIn('mynumber', form.errors)
        
        # 数字以外が含まれている
        form = StaffMynumberForm(data={'mynumber': '12345678901a'})
        self.assertFalse(form.is_valid())
        self.assertIn('mynumber', form.errors)