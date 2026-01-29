from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q
from apps.staff.models import Staff
from apps.staff.models_inquiry import StaffInquiry, StaffInquiryMessage
from apps.connect.models import ConnectStaff
from apps.company.models import Company as CompanyModel
from apps.common.constants import Constants

User = get_user_model()

class StaffInquiryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teststaff', email='staff@example.com', password='password')

        # Grant permissions for inquiry tests
        permissions = Permission.objects.filter(
            Q(codename='view_staffinquiry') |
            Q(codename='add_staffinquiry') |
            Q(codename='change_staffinquiry') |
            Q(codename='delete_staffinquirymessage')
        )
        self.user.user_permissions.set(permissions)

        self.admin_user = User.objects.create_superuser(username='adminuser', email='admin@example.com', password='password')
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
        self.assertEqual(StaffInquiryMessage.objects.count(), 1)
        inquiry = StaffInquiry.objects.first()
        message = StaffInquiryMessage.objects.first()
        self.assertEqual(inquiry.subject, 'Test Subject')
        self.assertEqual(inquiry.user, self.user)
        self.assertEqual(inquiry.inquiry_from, 'staff')
        self.assertEqual(message.content, 'Test Content')
        self.assertEqual(message.inquiry, inquiry)

    def test_inquiry_list(self):
        inquiry = StaffInquiry.objects.create(
            user=self.user,
            corporate_number='1234567890123',
            subject='Initial Subject',
        )
        StaffInquiryMessage.objects.create(
            inquiry=inquiry,
            user=self.user,
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
        from django.utils import timezone
        from datetime import timedelta
        
        inquiry = StaffInquiry.objects.create(
            user=self.user,
            corporate_number='1234567890123',
            subject='Delete Test',
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
        self.client.login(email='admin@example.com', password='password')
        url = reverse('staff:staff_inquiry_create_for_staff', kwargs={'staff_pk': self.staff.pk})
        data = {
            'subject': 'Test Subject from Company',
            'content': 'Test Content from Company',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffInquiry.objects.filter(subject='Test Subject from Company').exists())
        inquiry = StaffInquiry.objects.get(subject='Test Subject from Company')
        self.assertEqual(inquiry.inquiry_from, 'company')
        self.assertEqual(inquiry.user, self.user)
        # Check that a message was created
        self.assertEqual(inquiry.messages.count(), 1)
        self.assertEqual(inquiry.messages.first().content, 'Test Content from Company')


class StaffInquiryStatusTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username='teststaff', email='staff@example.com', password='password')
        self.company_user = User.objects.create_user(username='companyuser', email='company@example.com', password='password')
        self.company_user.is_staff = True
        self.company_user.save()

        permissions = Permission.objects.filter(
            Q(codename='view_staffinquiry') |
            Q(codename='add_staffinquiry') |
            Q(codename='change_staffinquiry') |
            Q(codename='delete_staffinquirymessage')
        )
        self.staff_user.user_permissions.set(permissions)
        self.company_user.user_permissions.set(permissions)

        self.company = CompanyModel.objects.create(name='Test Company', corporate_number='1234567890123')
        ConnectStaff.objects.create(corporate_number=self.company.corporate_number, email=self.staff_user.email, status='approved')

        self.inquiry = StaffInquiry.objects.create(
            user=self.staff_user,
            corporate_number=self.company.corporate_number,
            subject='Status Test',
        )
        StaffInquiryMessage.objects.create(
            inquiry=self.inquiry,
            user=self.staff_user,
            content='Test Content'
        )

        self.client_staff = Client()
        self.client_staff.login(username='teststaff', password='password')
        self.client_company = Client()
        self.client_company.login(username='companyuser', password='password')

    def test_toggle_status_reopen_failure(self):
        self.assertEqual(self.inquiry.status, 'open')

        # Toggle to completed
        url = reverse('staff:staff_inquiry_toggle_status', kwargs={'pk': self.inquiry.pk})
        response = self.client_staff.post(url)
        self.assertRedirects(response, reverse('staff:staff_inquiry_detail', kwargs={'pk': self.inquiry.pk}))
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, 'completed')

        # Try to toggle back to open (should fail now)
        response = self.client_staff.post(url)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, 'completed') # Should still be completed
        # Expect error message
        # self.assertContains(response, '完了済みの問い合わせを再開することはできません。') 
        # Note: Response is redirect, message is in Django messages. checking redirect.
        self.assertRedirects(response, reverse('staff:staff_inquiry_detail', kwargs={'pk': self.inquiry.pk}))

    def test_company_can_post_on_completed_inquiry(self):
        from apps.company.models import CompanyUser
        CompanyUser.objects.create(email=self.company_user.email, corporate_number=self.company.corporate_number)

        self.inquiry.status = 'completed'
        self.inquiry.save()

        initial_message_count = self.inquiry.messages.count()
        self.assertEqual(initial_message_count, 1)

        url = reverse('staff:staff_inquiry_detail', kwargs={'pk': self.inquiry.pk})
        data = {'content': 'Company CAN post'}
        response = self.client_company.post(url, data, follow=True)

        self.inquiry.refresh_from_db()
        # Should increase
        self.assertEqual(self.inquiry.messages.count(), initial_message_count + 1)
        self.assertNotContains(response, 'この問い合わせは完了済みのため、メッセージを投稿できません。')
        self.assertEqual(self.inquiry.messages.last().content, 'Company CAN post')


    def test_flags_on_reply(self):
        from apps.company.models import CompanyUser
        CompanyUser.objects.create(email=self.company_user.email, corporate_number=self.company.corporate_number)

        # Create inquiry by staff
        inquiry = StaffInquiry.objects.create(
            user=self.staff_user,
            corporate_number=self.company.corporate_number,
            subject='Initial',
            inquiry_from='staff',
            last_message_by='staff'
        )
        StaffInquiryMessage.objects.create(
            inquiry=inquiry,
            user=self.staff_user,
            content='Initial'
        )
        url = reverse('staff:staff_inquiry_detail', kwargs={'pk': inquiry.pk})

        # Company replies
        self.client_company.post(url, {'content': 'Company Reply'})
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.last_message_by, 'company')
        # msg = inquiry.messages.last()
        # self.assertEqual(msg.sender_type, 'company') # Field removed

        # Staff replies
        self.client_staff.post(url, {'content': 'Staff Reply'})
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.last_message_by, 'staff')
        # msg_staff = inquiry.messages.last()
        # self.assertEqual(msg_staff.sender_type, 'staff') # Field removed
