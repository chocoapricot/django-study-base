from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffPayroll
from datetime import date

User = get_user_model()

class StaffPayrollViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        content_type = ContentType.objects.get_for_model(StaffPayroll)
        self.view_perm = Permission.objects.get(codename='view_staffpayroll', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_staffpayroll', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_staffpayroll', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_staffpayroll', content_type=content_type)

        staff_content_type = ContentType.objects.get_for_model(Staff)
        self.view_staff_perm = Permission.objects.get(codename='view_staff', content_type=staff_content_type)

        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm, self.view_staff_perm)

        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
        )

    def test_staff_payroll_create_view_get(self):
        response = self.client.get(reverse('staff:staff_payroll_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_form.html')

    def test_staff_payroll_create_view_post(self):
        data = {
            'health_insurance_join_date': '2022-01-01',
            'welfare_pension_join_date': '2022-01-01',
            'employment_insurance_join_date': '2022-01-01',
        }
        response = self.client.post(reverse('staff:staff_payroll_create', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffPayroll.objects.filter(staff=self.staff).exists())

    def test_staff_payroll_detail_view(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.get(reverse('staff:staff_payroll_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_detail.html')
        self.assertContains(response, reverse('staff:staff_payroll_edit', args=[self.staff.pk]))

    def test_staff_payroll_edit_view_get(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.get(reverse('staff:staff_payroll_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_form.html')

    def test_staff_payroll_edit_view_post(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        data = {
            'health_insurance_join_date': '2023-01-01',
        }
        response = self.client.post(reverse('staff:staff_payroll_edit', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 302)
        payroll.refresh_from_db()
        self.assertEqual(payroll.health_insurance_join_date, date(2023, 1, 1))

    def test_staff_payroll_delete_view_get(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.get(reverse('staff:staff_payroll_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_confirm_delete.html')

    def test_staff_payroll_delete_view_post(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.post(reverse('staff:staff_payroll_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffPayroll.objects.filter(staff=self.staff).exists())
