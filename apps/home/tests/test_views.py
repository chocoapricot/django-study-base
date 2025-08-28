from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import MyUser
from apps.staff.models import Staff
from apps.connect.models import ConnectStaff, MynumberRequest
from apps.profile.models import StaffProfile, StaffProfileMynumber


class HomeViewTest(TestCase):
    def setUp(self):
        """
        テストデータのセットアップ
        """
        self.client = Client()
        self.user = MyUser.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password',
            first_name='Test',
            last_name='User',
        )
        self.home_url = reverse('home:home')

    def test_home_view_redirects_for_anonymous_user(self):
        """
        未ログインユーザーはログインページにリダイレクトされることをテスト
        """
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/accounts/login/?next={self.home_url}')

    def test_home_view_loads_for_logged_in_user(self):
        """
        ログイン済みユーザーでホーム画面が正常に表示されることをテスト
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/home.html')

    def test_home_view_context_data(self):
        """
        ホーム画面のコンテキストデータが正しく渡されていることをテスト
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)

        # コンテキストのキーが存在するかチェック
        self.assertIn('staff_count', response.context)
        self.assertIn('approved_staff_count', response.context)
        self.assertIn('client_count', response.context)
        self.assertIn('approved_client_count', response.context)

    def test_home_view_staff_request_count(self):
        """
        Test that staff_request_count is calculated correctly.
        """
        self.client.login(email='testuser@example.com', password='password')

        # Create staff user
        staff_user = MyUser.objects.create_user(
            username='staffuser@example.com',
            email='staff@example.com',
            password='password',
        )
        # Create mynumber profile
        staff_mynumber = StaffProfileMynumber.objects.create(
            user=staff_user,
            mynumber='123456789012'
        )

        # Create Staff data
        Staff.objects.create(email='staff@example.com')

        # Create ConnectStaff data
        connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            status='approved'
        )

        # Create a pending request
        MynumberRequest.objects.create(
            connect_staff=connect_staff,
            profile_mynumber=staff_mynumber,
            status='pending'
        )

        # Create another staff without request
        Staff.objects.create(email='norequest@example.com')

        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('staff_request_count', response.context)
        self.assertEqual(response.context['staff_request_count'], 1)
