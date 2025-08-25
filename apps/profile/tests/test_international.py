"""
外国籍情報機能のテスト
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission
from datetime import date, timedelta

from apps.profile.models import StaffProfile, StaffProfileInternational
from apps.profile.forms import StaffProfileInternationalForm
from apps.connect.models import ConnectStaff, ConnectInternationalRequest
from apps.staff.models import Staff

User = get_user_model()


class StaffProfileInternationalModelTest(TestCase):
    """StaffProfileInternationalモデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            email='test@example.com'
        )
    
    def test_create_international_profile(self):
        """外国籍情報の作成テスト"""
        international = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='TEST1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
        
        self.assertEqual(international.staff_profile, self.staff_profile)
        self.assertEqual(international.residence_card_number, 'TEST1234567890')
        self.assertEqual(international.residence_status, '技術・人文知識・国際業務')
        self.assertEqual(str(international), f"{self.staff_profile} - 外国籍情報")
    
    def test_international_profile_str(self):
        """__str__メソッドのテスト"""
        international = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='TEST1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
        
        expected = f"{self.staff_profile} - 外国籍情報"
        self.assertEqual(str(international), expected)


class StaffProfileInternationalFormTest(TestCase):
    """StaffProfileInternationalFormのテスト"""
    
    def test_valid_form(self):
        """正常なフォームデータのテスト"""
        form_data = {
            'residence_card_number': 'FORM1234567890',
            'residence_status': '技能実習',
            'residence_period_from': date.today(),
            'residence_period_to': date.today() + timedelta(days=365)
        }
        
        form = StaffProfileInternationalForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_date_range(self):
        """不正な日付範囲のテスト"""
        form_data = {
            'residence_card_number': 'FORM1234567890',
            'residence_status': '技能実習',
            'residence_period_from': date.today() + timedelta(days=365),
            'residence_period_to': date.today()
        }
        
        form = StaffProfileInternationalForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('在留許可開始日は在留期限より前の日付を入力してください。', str(form.errors))
    
    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = StaffProfileInternationalForm(data={})
        self.assertFalse(form.is_valid())
        
        required_fields = ['residence_card_number', 'residence_status', 'residence_period_from', 'residence_period_to']
        for field in required_fields:
            self.assertIn(field, form.errors)


class ConnectInternationalRequestModelTest(TestCase):
    """ConnectInternationalRequestモデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            email='test@example.com'
        )
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='test@example.com',
            status='approved'
        )
        self.international_profile = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='TEST1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
    
    def test_create_international_request(self):
        """外国籍情報申請の作成テスト"""
        request = ConnectInternationalRequest.objects.create(
            connect_staff=self.connect_staff,
            profile_international=self.international_profile,
            status='pending'
        )
        
        self.assertEqual(request.connect_staff, self.connect_staff)
        self.assertEqual(request.profile_international, self.international_profile)
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.get_status_display(), '未承認')
    
    def test_international_request_str(self):
        """__str__メソッドのテスト"""
        request = ConnectInternationalRequest.objects.create(
            connect_staff=self.connect_staff,
            profile_international=self.international_profile,
            status='pending'
        )
        
        expected = f"{self.connect_staff} - {self.international_profile} (未承認)"
        self.assertEqual(str(request), expected)


class InternationalViewTest(TestCase):
    """外国籍情報ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を付与
        permissions = Permission.objects.filter(
            codename__in=[
                'view_staffprofileinternational',
                'add_staffprofileinternational',
                'change_staffprofileinternational',
                'delete_staffprofileinternational'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            email='test@example.com'
        )
        
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='test@example.com',
            status='approved'
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_international_detail_view_no_data(self):
        """外国籍情報詳細ビュー（データなし）のテスト"""
        response = self.client.get(reverse('profile:international_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '外国籍情報が登録されていません')
    
    def test_international_detail_view_with_data(self):
        """外国籍情報詳細ビュー（データあり）のテスト"""
        international = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='TEST1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
        
        response = self.client.get(reverse('profile:international_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST1234567890')
        self.assertContains(response, '技術・人文知識・国際業務')
    
    def test_international_edit_view_get(self):
        """外国籍情報編集ビュー（GET）のテスト"""
        response = self.client.get(reverse('profile:international_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '外国籍情報登録')
    
    def test_international_edit_view_post_valid(self):
        """外国籍情報編集ビュー（POST・正常データ）のテスト"""
        form_data = {
            'residence_card_number': 'POST1234567890',
            'residence_status': '留学',
            'residence_period_from': date.today().strftime('%Y-%m-%d'),
            'residence_period_to': (date.today() + timedelta(days=730)).strftime('%Y-%m-%d')
        }
        
        response = self.client.post(reverse('profile:international_edit'), data=form_data)
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # データが作成されているか確認
        international = StaffProfileInternational.objects.get(staff_profile=self.staff_profile)
        self.assertEqual(international.residence_card_number, 'POST1234567890')
        self.assertEqual(international.residence_status, '留学')
        
        # 申請が作成されているか確認
        request = ConnectInternationalRequest.objects.get(connect_staff=self.connect_staff)
        self.assertEqual(request.profile_international, international)
        self.assertEqual(request.status, 'pending')
    
    def test_international_edit_view_post_invalid(self):
        """外国籍情報編集ビュー（POST・不正データ）のテスト"""
        form_data = {
            'residence_card_number': 'POST1234567890',
            'residence_status': '留学',
            'residence_period_from': (date.today() + timedelta(days=730)).strftime('%Y-%m-%d'),
            'residence_period_to': date.today().strftime('%Y-%m-%d')
        }
        
        response = self.client.post(reverse('profile:international_edit'), data=form_data)
        self.assertEqual(response.status_code, 200)  # フォームエラーで再表示
        self.assertContains(response, '在留許可開始日は在留期限より前の日付を入力してください')
    
    def test_international_delete_view_get(self):
        """外国籍情報削除ビュー（GET）のテスト"""
        international = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='DELETE1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
        
        response = self.client.get(reverse('profile:international_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DELETE1234567890')
        self.assertContains(response, '外国籍情報を削除しますか？')
    
    def test_international_delete_view_post(self):
        """外国籍情報削除ビュー（POST）のテスト"""
        international = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='DELETE1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
        
        response = self.client.post(reverse('profile:international_delete'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # データが削除されているか確認
        self.assertFalse(
            StaffProfileInternational.objects.filter(staff_profile=self.staff_profile).exists()
        )
    
    def test_international_view_without_connect_staff(self):
        """ConnectStaffなしでのアクセステスト"""
        # ConnectStaffを削除
        self.connect_staff.delete()
        
        response = self.client.get(reverse('profile:international_detail'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
    
    def test_international_view_without_permissions(self):
        """権限なしでのアクセステスト"""
        # 権限を削除
        self.user.user_permissions.clear()
        
        response = self.client.get(reverse('profile:international_detail'))
        self.assertEqual(response.status_code, 403)  # 権限エラー


class InternationalIntegrationTest(TestCase):
    """外国籍情報機能の統合テスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を付与
        permissions = Permission.objects.filter(
            codename__in=[
                'view_staffprofileinternational',
                'add_staffprofileinternational',
                'change_staffprofileinternational',
                'delete_staffprofileinternational'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            email='test@example.com'
        )
        
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='test@example.com',
            status='approved'
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_full_international_workflow(self):
        """外国籍情報の完全なワークフローテスト"""
        # 1. 詳細画面でデータなし確認
        response = self.client.get(reverse('profile:international_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '外国籍情報が登録されていません')
        
        # 2. 登録画面でデータ入力
        form_data = {
            'residence_card_number': 'WORKFLOW1234567890',
            'residence_status': '特定技能',
            'residence_period_from': date.today().strftime('%Y-%m-%d'),
            'residence_period_to': (date.today() + timedelta(days=1095)).strftime('%Y-%m-%d')
        }
        
        response = self.client.post(reverse('profile:international_edit'), data=form_data)
        self.assertEqual(response.status_code, 302)
        
        # 3. データが作成されているか確認
        international = StaffProfileInternational.objects.get(staff_profile=self.staff_profile)
        self.assertEqual(international.residence_card_number, 'WORKFLOW1234567890')
        self.assertEqual(international.residence_status, '特定技能')
        
        # 4. 申請が作成されているか確認
        request = ConnectInternationalRequest.objects.get(connect_staff=self.connect_staff)
        self.assertEqual(request.profile_international, international)
        self.assertEqual(request.status, 'pending')
        
        # 5. 詳細画面でデータあり確認
        response = self.client.get(reverse('profile:international_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WORKFLOW1234567890')
        self.assertContains(response, '特定技能')
        
        # 6. 削除処理
        response = self.client.post(reverse('profile:international_delete'))
        self.assertEqual(response.status_code, 302)
        
        # 7. データが削除されているか確認
        self.assertFalse(
            StaffProfileInternational.objects.filter(staff_profile=self.staff_profile).exists()
        )