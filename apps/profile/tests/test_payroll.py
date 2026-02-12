from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.profile.models import StaffProfilePayroll
from apps.staff.models import Staff, StaffPayroll
from apps.connect.models import ConnectStaff, PayrollRequest
from apps.company.models import Company

User = get_user_model()

class StaffProfilePayrollTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='テスト会社', corporate_number='1234567890123')
        self.tenant_id = self.company.tenant_id
        self.user = User.objects.create_user(username='teststaff', email='test@example.com', password='password')
        self.staff = Staff.objects.create(name_last='テスト', name_first='太郎', email='test@example.com', tenant_id=self.tenant_id)

        # 権限の付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(codename__in=[
            'view_staffprofilepayroll', 'add_staffprofilepayroll', 'change_staffprofilepayroll', 'delete_staffprofilepayroll',
            'view_staffprofile', # profile_index uses this
        ])
        self.user.user_permissions.add(*permissions)

    def test_payroll_create_view(self):
        self.client.login(username='teststaff', password='password')
        response = self.client.get(reverse('profile:payroll_edit'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('profile:payroll_edit'), {
            'basic_pension_number': '123-456-7890'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffProfilePayroll.objects.filter(user=self.user).exists())
        payroll = StaffProfilePayroll.objects.get(user=self.user)
        self.assertEqual(payroll.basic_pension_number, '123-456-7890')

    def test_payroll_request_creation(self):
        # 接続承認済みの状態を作る
        connect_staff = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.user.email,
            status='approved'
        )

        self.client.login(username='teststaff', password='password')
        self.client.post(reverse('profile:payroll_edit'), {
            'basic_pension_number': '123-456-7890'
        })

        # PayrollRequestが作成されているか確認
        self.assertTrue(PayrollRequest.objects.filter(connect_staff=connect_staff).exists())
        request = PayrollRequest.objects.get(connect_staff=connect_staff)
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.staff_payroll_profile.basic_pension_number, '123-456-7890')

    def test_payroll_request_approval(self):
        # 管理者ユーザー
        admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')

        # プロフィール側で登録
        payroll_profile = StaffProfilePayroll.objects.create(user=self.user, basic_pension_number='123-456-7890')

        connect_staff = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.user.email,
            status='approved'
        )

        payroll_request = PayrollRequest.objects.create(
            connect_staff=connect_staff,
            staff_payroll_profile=payroll_profile,
            status='pending'
        )

        self.client.login(username='admin', password='password')
        url = reverse('staff:staff_payroll_request_detail', kwargs={'staff_pk': self.staff.pk, 'pk': payroll_request.pk})

        # 承認
        response = self.client.post(url, {'action': 'approve'})
        self.assertEqual(response.status_code, 302)

        # スタッフ側の給与情報が更新されているか確認
        self.assertTrue(StaffPayroll.objects.filter(staff=self.staff).exists())
        staff_payroll = StaffPayroll.objects.get(staff=self.staff)
        self.assertEqual(staff_payroll.basic_pension_number, '123-456-7890')

        # 申請ステータスが更新されているか確認
        payroll_request.refresh_from_db()
        self.assertEqual(payroll_request.status, 'approved')
