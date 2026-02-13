from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q
from apps.kintai.models import StaffTimerecordApproval, StaffTimerecord
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.master.models import TimePunch, ContractPattern
from apps.common.constants import Constants
from apps.common.middleware import set_current_tenant_id
from datetime import date

User = get_user_model()

class TimerecordApprovalViewTest(TestCase):
    def setUp(self):
        self.tenant_id = 1
        set_current_tenant_id(self.tenant_id)

        self.user = User.objects.create_superuser(
            username='admin',
            password='password',
            email='admin@example.com',
            tenant_id=self.tenant_id
        )
        self.client.login(username='admin', password='password')

        # Add permissions
        permissions = Permission.objects.filter(
            Q(codename='view_stafftimerecordapproval') |
            Q(codename='change_stafftimerecordapproval')
        )
        self.user.user_permissions.add(*permissions)

        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            employee_no='S001',
            email='taro@example.com',
            tenant_id=self.tenant_id
        )

        self.time_punch = TimePunch.objects.create(
            name='テスト打刻',
            punch_method=Constants.PUNCH_METHOD.PUNCH,
            tenant_id=self.tenant_id
        )

        self.contract_pattern = ContractPattern.objects.create(
            name='テストパターン',
            domain=Constants.DOMAIN.STAFF,
            tenant_id=self.tenant_id
        )

        self.contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            start_date=date(2025, 1, 1),
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED,
            time_punch=self.time_punch,
            contract_pattern=self.contract_pattern,
            tenant_id=self.tenant_id
        )

        self.approval = StaffTimerecordApproval.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            closing_date=date(2025, 1, 31),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            status='20', # 提出済み
            tenant_id=self.tenant_id
        )

    def test_approval_list_view(self):
        # We need to set tenant_id in session for the middleware to pick it up
        session = self.client.session
        session['tenant_id'] = self.tenant_id
        session.save()

        response = self.client.get(reverse('kintai:timerecord_approval_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/timerecord_approval_list.html')
        self.assertContains(response, 'テスト 太郎')

    def test_approval_detail_view(self):
        session = self.client.session
        session['tenant_id'] = self.tenant_id
        session.save()

        response = self.client.get(reverse('kintai:timerecord_approval_detail', args=[self.approval.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/timerecord_approval_detail.html')
        self.assertContains(response, 'テスト 太郎')

    def test_approve_action(self):
        session = self.client.session
        session['tenant_id'] = self.tenant_id
        session.save()

        response = self.client.post(reverse('kintai:timerecord_approval_approve', args=[self.approval.pk]))
        self.assertEqual(response.status_code, 302)
        self.approval.refresh_from_db()
        self.assertEqual(self.approval.status, '30')

    def test_reject_action(self):
        session = self.client.session
        session['tenant_id'] = self.tenant_id
        session.save()

        response = self.client.post(reverse('kintai:timerecord_approval_reject', args=[self.approval.pk]))
        self.assertEqual(response.status_code, 302)
        self.approval.refresh_from_db()
        self.assertEqual(self.approval.status, '40')

    def test_cancel_action(self):
        session = self.client.session
        session['tenant_id'] = self.tenant_id
        session.save()

        # First, approve it
        self.approval.status = '30'
        self.approval.save()

        response = self.client.post(reverse('kintai:timerecord_approval_cancel', args=[self.approval.pk]))
        self.assertEqual(response.status_code, 302)
        self.approval.refresh_from_db()
        self.assertEqual(self.approval.status, '20')
