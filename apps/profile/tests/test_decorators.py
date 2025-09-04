from django.test import TestCase, Client, override_settings
from django.urls import reverse, path, include
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from apps.profile.decorators import check_staff_agreement
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.master.models import StaffAgreement
from apps.company.models import Company

User = get_user_model()

@check_staff_agreement
def dummy_view(request):
    return HttpResponse("OK")

# このテスト用のURLConf
urlpatterns = [
    path('dummy_test_view/', dummy_view, name='dummy_view'),
    path('connect/', include('apps.connect.urls')),
]

@override_settings(ROOT_URLCONF=__name__)
class StaffAgreementDecoratorTest(TestCase):
    """check_staff_agreement デコレータのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='TestPass123!',
            is_staff=False,
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
            status='approved',
        )

    def test_redirect_if_not_agreed(self):
        """未同意の場合に同意画面にリダイレクトされ、nextパラメータが付与されることをテスト"""
        self.client.login(email='testuser@example.com', password='TestPass123!')
        
        dummy_url = reverse('dummy_view')
        response = self.client.get(dummy_url)
        
        self.assertEqual(response.status_code, 302, "未同意のユーザーはリダイレクトされるべき")
        
        expected_redirect_url = reverse('connect:staff_agree', kwargs={'pk': self.connection.pk})
        self.assertTrue(response.url.startswith(expected_redirect_url))
        self.assertIn(f'next={dummy_url}', response.url)

    def test_no_redirect_if_agreed(self):
        """同意済みの場合にリダイレクトされないことをテスト"""
        ConnectStaffAgree.objects.create(
            email=self.user.email,
            corporate_number=self.company.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True,
        )
        
        self.client.login(email='testuser@example.com', password='TestPass123!')
        
        response = self.client.get(reverse('dummy_view'))
        
        self.assertEqual(response.status_code, 200, "同意済みのユーザーはリダイレクトされないべき")
        self.assertEqual(response.content, b"OK")

    def test_no_redirect_for_staff_user(self):
        """is_staff=Trueのユーザーはチェック対象外であることをテスト"""
        staff_user = User.objects.create_user(
            username='staffuser',
            email='staffuser@example.com',
            password='TestPass123!',
            is_staff=True,
        )
        self.client.login(email='staffuser@example.com', password='TestPass123!')
        
        response = self.client.get(reverse('dummy_view'))
        
        self.assertEqual(response.status_code, 200, "is_staffユーザーはチェック対象外")
        self.assertEqual(response.content, b"OK")
