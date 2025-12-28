from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.company.models import Company
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.master.models import StaffAgreement

User = get_user_model()

class StaffAgreeViewTest(TestCase):
    """staff_agree ビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='TestPass123!',
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='TestPass123!',
        )
        self.company = Company.objects.create(
            corporate_number='1234567890123',
            name='Test Company',
        )
        self.agreement = StaffAgreement.objects.create(
            name='Test Agreement',
            agreement_text='This is a test agreement.',
            corporation_number=self.company.corporate_number,
            is_active=True,
        )
        self.connection = ConnectStaff.objects.create(
            email=self.user.email,
            corporate_number=self.company.corporate_number,
            status='pending', # 承認待ちの状態
        )

    def test_redirect_to_next_url_after_agreement(self):
        """同意後、next パラメータにリダイレクトされることをテスト"""
        self.client.login(email='approver@example.com', password='TestPass123!')
        
        target_redirect_url = '/profile/some_page/'
        agree_url = reverse('connect:staff_agree', kwargs={'pk': self.connection.pk})
        
        # next パラメータを付けて同意画面にPOST
        response = self.client.post(
            f'{agree_url}?next={target_redirect_url}',
            {'agreements': [self.agreement.pk]}
        )
        
        # next パラメータのURLにリダイレクトされることを確認
        self.assertRedirects(response, target_redirect_url, fetch_redirect_response=False)
        
        # 同意が記録されていることを確認
        self.assertTrue(
            ConnectStaffAgree.objects.filter(
                email=self.user.email,
                staff_agreement=self.agreement,
                is_agreed=True,
            ).exists()
        )
        
        # 接続ステータスは変わらないことを確認 (承認フローは通らないため)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, 'pending')

    def test_redirect_to_connect_list_if_no_next_param(self):
        """next パラメータがない場合、承認フローに進むことをテスト"""
        self.client.login(email='approver@example.com', password='TestPass123!')
        
        agree_url = reverse('connect:staff_agree', kwargs={'pk': self.connection.pk})
        
        response = self.client.post(agree_url, {'agreements': [self.agreement.pk]})
        
        # 承認されて接続一覧にリダイレクトされることを確認
        self.assertRedirects(response, reverse('connect:staff_list'))
        
        # 接続ステータスが 'approved' になっていることを確認
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, 'approved')

    def test_staff_agree_view_contains_company_name(self):
        """同意画面に会社名が含まれていることをテスト"""
        self.client.login(email='approver@example.com', password='TestPass123!')
        
        agree_url = reverse('connect:staff_agree', kwargs={'pk': self.connection.pk})
        response = self.client.get(agree_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'{self.company.name} - 同意確認')
