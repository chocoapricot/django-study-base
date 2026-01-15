from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from apps.staff.models_inquiry import StaffInquiry
from apps.connect.models import ConnectStaff
from apps.company.models import Company as CompanyModel
from apps.common.constants import Constants

User = get_user_model()

class StaffInquiryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teststaff', email='staff@example.com', password='password')
        self.admin_user = User.objects.create_superuser(username='adminuser', email='admin@test.com', password='password')
        self.client_user = Client()
        self.client_user.login(username='teststaff', password='password')
        
        # スタッフ作成
        self.staff = Staff.objects.create(email=self.user.email, name_last='Staff', name_first='Test')

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
        self.assertEqual(inquiry.inquiry_from, 'staff')

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

    def test_inquiry_message_delete(self):
        from apps.staff.models_inquiry import StaffInquiryMessage
        from django.utils import timezone
        from datetime import timedelta
        
        inquiry = StaffInquiry.objects.create(
            user=self.user,
            corporate_number='1234567890123',
            subject='Delete Test',
            content='Original Content'
        )
        
        # 1. 5分以内のメッセージ作成
        msg = StaffInquiryMessage.objects.create(
            inquiry=inquiry,
            user=self.user,
            content='Deletable message'
        )
        
        delete_url = reverse('staff:staff_inquiry_message_delete', kwargs={'pk': msg.pk})
        
        # 削除実行
        response = self.client_user.post(delete_url) # urls.py matches this, even if using GET link in UI
        self.assertEqual(StaffInquiryMessage.objects.count(), 0)
        
        # 2. 5分経過後のメッセージ作成
        msg_old = StaffInquiryMessage.objects.create(
            inquiry=inquiry,
            user=self.user,
            content='Expired message'
        )
        # created_atを手動で過去にずらす
        msg_old.created_at = timezone.now() - timedelta(minutes=6)
        msg_old.save()
        
        delete_url_old = reverse('staff:staff_inquiry_message_delete', kwargs={'pk': msg_old.pk})
        response = self.client_user.post(delete_url_old)
        
        # 削除されていないことを確認
        self.assertEqual(StaffInquiryMessage.objects.count(), 1)
        self.assertTrue(StaffInquiryMessage.objects.filter(pk=msg_old.pk).exists())

    def test_staff_inquiry_create_for_staff_view(self):
        self.client.login(email='admin@test.com', password='password')
        url = reverse('staff:staff_inquiry_create_for_staff', kwargs={'staff_pk': self.staff.pk})
        data = {
            'subject': 'Test Subject from Company',
            'content': 'Test Content from Company',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        inquiry = StaffInquiry.objects.get(subject='Test Subject from Company')
        self.assertEqual(inquiry.inquiry_from, 'company')
        self.assertEqual(inquiry.user, self.user)
