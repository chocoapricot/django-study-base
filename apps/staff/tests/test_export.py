from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.staff.models import Staff

class StaffExportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser',
            password='password'
        )
        # Give permission to view staff
        permission = Permission.objects.get(codename='view_staff')
        self.user.user_permissions.add(permission)
        self.client.login(username='testuser', password='password')

        # Create some staff data
        self.staff1 = Staff.objects.create(
            employee_no='001',
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            email='taro@example.com'
        )
        self.staff2 = Staff.objects.create(
            employee_no='002',
            name_last='鈴木',
            name_first='花子',
            name_kana_last='スズキ',
            name_kana_first='ハナコ',
            email='hanako@example.com',
            regist_form_code=1 # Example filter value
        )

    def test_staff_export_csv(self):
        """Test exporting staff data as CSV."""
        url = reverse('staff:staff_export') + '?format=csv'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

        content = response.content.decode('utf-8')
        self.assertIn('山田', content)
        self.assertIn('鈴木', content)
        self.assertIn('employee_no', content) # Check for header

    def test_staff_export_excel(self):
        """Test exporting staff data as Excel."""
        url = reverse('staff:staff_export') + '?format=excel'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_staff_export_with_filter(self):
        """Test exporting filtered staff data."""
        url = reverse('staff:staff_export') + '?format=csv&q=山田'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertIn('山田', content)
        self.assertNotIn('鈴木', content)

    def test_staff_export_with_regist_form_filter(self):
        """Test exporting with regist_form filter."""
        url = reverse('staff:staff_export') + '?format=csv&regist_form=1'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertNotIn('山田', content)
        self.assertIn('鈴木', content)
