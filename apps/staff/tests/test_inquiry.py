from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models_inquiry import StaffInquiry
from apps.connect.models import ConnectStaff
from apps.company.models import Company as CompanyModel
from apps.common.constants import Constants

User = get_user_model()

class StaffInquiryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teststaff', email='staff@example.com', password='password')
        self.client_user = Client()
        self.client_user.login(username='teststaff', password='password')
        
        # 会社作成
        self.company_model = CompanyModel.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        
        # 接続承認作成
        ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            status=Constants.CONNECT_STATUS.APPROVED
        )

    def test_inquiry_create(self):
        url = reverse('staff:staff_inquiry_create')
        # GET
        response = self.client_user.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Company')
        
        # POST
        data = {
            'corporate_number': '1234567890123',
            'subject': 'Test Subject',
            'content': 'Test Content'
        }
        response = self.client_user.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StaffInquiry.objects.count(), 1)
        inquiry = StaffInquiry.objects.first()
        self.assertEqual(inquiry.subject, 'Test Subject')
        self.assertEqual(inquiry.user, self.user)

    def test_inquiry_list(self):
        StaffInquiry.objects.create(
            user=self.user,
            corporate_number='1234567890123',
            subject='Initial Subject',
            content='Initial Content'
        )
        url = reverse('staff:staff_inquiry_list')
        response = self.client_user.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Initial Subject')
        self.assertContains(response, 'Test Company')

    def test_inquiry_list_empty_redirect(self):
        # 問い合わせがない場合、新規作成画面へリダイレクトされることを確認
        StaffInquiry.objects.all().delete()
        url = reverse('staff:staff_inquiry_list')
        response = self.client_user.get(url)
        self.assertRedirects(response, reverse('staff:staff_inquiry_create'))

    def test_inquiry_message(self):
        inquiry = StaffInquiry.objects.create(
            user=self.user,
            corporate_number='1234567890123',
            subject='Message Test',
            content='Original Content'
        )
        url = reverse('staff:staff_inquiry_detail', kwargs={'pk': inquiry.pk})
        
        # メッセージ投稿
        data = {
            'content': 'Reply from Staff'
        }
        response = self.client_user.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        from apps.staff.models_inquiry import StaffInquiryMessage
        self.assertEqual(StaffInquiryMessage.objects.count(), 1)
        msg = StaffInquiryMessage.objects.first()
        self.assertEqual(msg.content, 'Reply from Staff')
        self.assertEqual(msg.user, self.user)
