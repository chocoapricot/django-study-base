from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q
from apps.staff.models import Staff
from apps.staff.models_inquiry import StaffInquiry, StaffInquiryMessage
from apps.master.models import StaffRegistStatus, EmploymentType, StaffTag
from apps.company.models import Company, CompanyUser
from apps.common.constants import Constants
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class StaffInquiryListBadgesTest(TestCase):
    def setUp(self):
        # Setup company and tenant
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        self.company.tenant_id = self.company.id
        self.company.save()
        set_current_tenant_id(self.company.id)

        # Create master data
        self.regist_status = StaffRegistStatus.objects.create(name='正社員', display_order=1)
        self.employment_type = EmploymentType.objects.create(name='月給', display_order=1)
        self.tag = StaffTag.objects.create(name='重要', display_order=1)

        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password',
            first_name='Taro',
            last_name='Tanaka',
            tenant_id=self.company.id
        )

        # Create staff record
        self.staff = Staff.objects.create(
            email=self.staff_user.email,
            name_last='Tanaka',
            name_first='Taro',
            regist_status=self.regist_status,
            employment_type=self.employment_type,
            tenant_id=self.company.id
        )
        self.staff.tags.add(self.tag)

        # Create company user
        self.company_user = User.objects.create_user(
            username='companyuser',
            email='company@example.com',
            password='password',
            tenant_id=self.company.id
        )
        CompanyUser.objects.create(
            email=self.company_user.email,
            corporate_number=self.company.corporate_number,
            tenant_id=self.company.id
        )

        # Grant permissions
        permissions = Permission.objects.filter(
            Q(codename='view_staffinquiry') |
            Q(codename='add_staffinquiry')
        )
        self.company_user.user_permissions.set(permissions)

        # Create inquiry
        self.inquiry = StaffInquiry.objects.create(
            user=self.staff_user,
            corporate_number=self.company.corporate_number,
            subject='Badge Test Inquiry',
            tenant_id=self.company.id
        )
        StaffInquiryMessage.objects.create(
            inquiry=self.inquiry,
            user=self.staff_user,
            content='Message Content',
            tenant_id=self.company.id
        )

        self.client = Client()

    def test_inquiry_list_badges_for_company_user(self):
        self.client.login(email='company@example.com', password='password')
        url = reverse('staff:staff_inquiry_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check if badges are present
        self.assertContains(response, '正社員')
        self.assertContains(response, 'bg-primary') # Based on display_order=1
        self.assertContains(response, '月給')
        self.assertContains(response, '重要')
        self.assertContains(response, 'rounded-pill') # Tags are rounded-pill

        # Check if the staff name is present
        self.assertContains(response, 'Tanaka Taro')

    def test_inquiry_list_no_badges_for_staff_user(self):
        # Staff user should not see these columns/badges based on the template logic
        self.client.login(email='staff@example.com', password='password')

        # Grant permissions to staff user too
        permissions = Permission.objects.filter(
            Q(codename='view_staffinquiry')
        )
        self.staff_user.user_permissions.set(permissions)

        url = reverse('staff:staff_inquiry_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Staff user sees "あて先企業" but not "登録区分" or "雇用形態" columns
        self.assertNotContains(response, '<th>登録区分</th>')
        self.assertNotContains(response, '<th>雇用形態</th>')

        # Staff user might see their own name if it was in the "あて先企業" column but it's not.
        # They see company name.
        self.assertContains(response, 'Test Company')
