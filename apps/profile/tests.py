from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from datetime import date, timedelta
from apps.profile.models import StaffProfile, StaffProfileInternational
from apps.profile.forms import StaffProfileInternationalForm
from apps.connect.models import ConnectStaff, ConnectInternationalRequest
from apps.staff.models import Staff

User = get_user_model()


class StaffProfileInternationalModelTest(TestCase):
    """外国籍プロフィールモデルのテスト"""
    
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
        """外国籍プロフィールの作成テスト"""
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
        """外国籍プロフィールの文字列表現テスト"""
        international = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='TEST1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
        
        expected_str = f"{self.staff_profile} - 外国籍情報"
        self.assertEqual(str(international), expected_str)


class StaffProfileInternationalFormTest(TestCase):
    """外国籍プロフィールフォームのテスト"""
    
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


class ConnectInternationalRequestTest(TestCase):
    """外国籍情報申請のテスト"""
    
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
        """外国籍情報申請の文字列表現テスト"""
        request = ConnectInternationalRequest.objects.create(
            connect_staff=self.connect_staff,
            profile_international=self.international_profile,
            status='pending'
        )
        
        expected_str = f"{self.connect_staff} - {self.international_profile} (未承認)"
        self.assertEqual(str(request), expected_str)


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
        url = reverse('profile:international_detail')
        response = self.client.get(url)
        
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
        
        url = reverse('profile:international_detail')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST1234567890')
        self.assertContains(response, '技術・人文知識・国際業務')
    
    def test_international_edit_view_get(self):
        """外国籍情報編集ビュー（GET）のテスト"""
        url = reverse('profile:international_edit')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '外国籍情報登録')
        self.assertContains(response, '在留カード番号')
    
    def test_international_edit_view_post_valid(self):
        """外国籍情報編集ビュー（POST・正常データ）のテスト"""
        url = reverse('profile:international_edit')
        form_data = {
            'residence_card_number': 'POST1234567890',
            'residence_status': '留学',
            'residence_period_from': date.today().strftime('%Y-%m-%d'),
            'residence_period_to': (date.today() + timedelta(days=730)).strftime('%Y-%m-%d')
        }
        
        response = self.client.post(url, data=form_data)
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 外国籍情報が作成されたことを確認
        international = StaffProfileInternational.objects.get(staff_profile=self.staff_profile)
        self.assertEqual(international.residence_card_number, 'POST1234567890')
        self.assertEqual(international.residence_status, '留学')
        
        # 申請が作成されたことを確認
        request = ConnectInternationalRequest.objects.get(connect_staff=self.connect_staff)
        self.assertEqual(request.profile_international, international)
        self.assertEqual(request.status, 'pending')
    
    def test_international_edit_view_post_invalid(self):
        """外国籍情報編集ビュー（POST・不正データ）のテスト"""
        url = reverse('profile:international_edit')
        form_data = {
            'residence_card_number': 'POST1234567890',
            'residence_status': '留学',
            'residence_period_from': (date.today() + timedelta(days=365)).strftime('%Y-%m-%d'),
            'residence_period_to': date.today().strftime('%Y-%m-%d')
        }
        
        response = self.client.post(url, data=form_data)
        
        # フォームエラーでページが再表示されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '在留許可開始日は在留期限より前の日付を入力してください')
    
    def test_international_delete_view(self):
        """外国籍情報削除ビューのテスト"""
        international = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='DELETE1234567890',
            residence_status='技能実習',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )
        
        # GET リクエスト（削除確認画面）
        url = reverse('profile:international_delete')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DELETE1234567890')
        self.assertContains(response, '外国籍情報を削除しますか？')
        
        # POST リクエスト（削除実行）
        response = self.client.post(url)
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 外国籍情報が削除されたことを確認
        self.assertFalse(
            StaffProfileInternational.objects.filter(staff_profile=self.staff_profile).exists()
        )
    
    def test_view_without_connect_staff(self):
        """ConnectStaffが存在しない場合のテスト"""
        # ConnectStaffを削除
        self.connect_staff.delete()
        
        url = reverse('profile:international_detail')
        response = self.client.get(url)
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)


class StaffInternationalRequestViewTest(TestCase):
    """スタッフ側の外国籍情報申請ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        # 管理者権限を付与
        permissions = Permission.objects.filter(
            codename__in=['change_staff', 'view_staff']
        )
        self.admin_user.user_permissions.set(permissions)
        
        self.staff = Staff.objects.create(
            name_last='申請',
            name_first='花子',
            name_kana_last='シンセイ',
            name_kana_first='ハナコ',
            email='staff@example.com',
            regist_form_code=1,
            sex=2
        )
        
        self.user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpass123'
        )
        
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            name_last='申請',
            name_first='花子',
            name_kana_last='シンセイ',
            name_kana_first='ハナコ',
            email='staff@example.com'
        )
        
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            status='approved'
        )
        
        self.international_profile = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='REQ1234567890',
            residence_status='留学',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=730)
        )
        
        self.international_request = ConnectInternationalRequest.objects.create(
            connect_staff=self.connect_staff,
            profile_international=self.international_profile,
            status='pending'
        )
        
        self.client.login(username='admin', password='adminpass123')
    
    def test_staff_international_request_detail_view(self):
        """スタッフ外国籍情報申請詳細ビューのテスト"""
        url = reverse('staff:staff_international_request_detail', 
                     kwargs={'staff_pk': self.staff.pk, 'pk': self.international_request.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'REQ1234567890')
        self.assertContains(response, '留学')
        self.assertContains(response, '承認')
        self.assertContains(response, '却下')
    
    def test_staff_international_request_approve(self):
        """外国籍情報申請承認のテスト"""
        url = reverse('staff:staff_international_request_detail', 
                     kwargs={'staff_pk': self.staff.pk, 'pk': self.international_request.pk})
        
        response = self.client.post(url, data={'action': 'approve'})
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 申請が承認されたことを確認
        self.international_request.refresh_from_db()
        self.assertEqual(self.international_request.status, 'approved')
    
    def test_staff_international_request_reject(self):
        """外国籍情報申請却下のテスト"""
        url = reverse('staff:staff_international_request_detail', 
                     kwargs={'staff_pk': self.staff.pk, 'pk': self.international_request.pk})
        
        response = self.client.post(url, data={'action': 'reject'})
        
        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 申請が却下されたことを確認
        self.international_request.refresh_from_db()
        self.assertEqual(self.international_request.status, 'rejected')
        
        # 関連する外国籍情報が削除されたことを確認
        self.assertFalse(
            StaffProfileInternational.objects.filter(pk=self.international_profile.pk).exists()
        )


if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.settings')
    django.setup()
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["apps.profile.tests"])